"""Selected-module SpiderFoot pilot, using the native scanner and graph/correlation engine."""
import argparse, csv, datetime, hashlib, json, logging, os, ssl, sys, threading, time, urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'sources/spiderfoot'
sys.path.insert(0,str(SOURCE))
PROVIDERS={'crt.sh','whois.arin.net'}
COLUMNS=['generated','data','source_data','module','type','confidence','visibility','risk','hash','source_event_hash','event_description','event_class','scan_id','false_positive','parent_false_positive']
def parse():
    p=argparse.ArgumentParser(description='SpiderFoot selected-module pilot: provider queries, native event chaining and graph exports.')
    p.add_argument('target',nargs='?')
    p.add_argument('--output',type=Path,default=Path.cwd())
    p.add_argument('--max-requests',type=int,default=20)
    p.add_argument('--deadline',type=int,default=120)
    p.add_argument('--fixture',action='store_true',help='Use built-in synthetic provider fixtures; target must be example.test.')
    p.add_argument('--catalog',action='store_true',help='Show the reviewed module profiles without querying providers.')
    a=p.parse_args()
    if a.catalog: print(json.dumps({'domain':['sfp_crt','sfp_arin','sfp_email'],'storage':'sfp__stor_db','providers':sorted(PROVIDERS)},indent=2)); return a
    if not a.target: p.error('Supply a domain name.')
    if a.fixture and a.target!='example.test': p.error('--fixture accepts only example.test')
    if not 1<=a.max_requests<=100 or not 10<=a.deadline<=600: p.error('Request budget must be 1..100 and deadline 10..600 seconds.')
    return a

def main():
    a=parse()
    if a.catalog: return 0
    output=a.output.resolve()
    if not output.is_relative_to(ROOT): raise ValueError('Output must stay inside the OSINT workbench.')
    output.mkdir(parents=True,exist_ok=True)
    state=output/('spiderfoot-fixture-state-v2' if a.fixture else 'spiderfoot-state')
    for folder in [state,state/'cache',state/'logs']: folder.mkdir(exist_ok=True)
    os.environ.update(SPIDERFOOT_DATA=str(state),SPIDERFOOT_CACHE=str(state/'cache'),SPIDERFOOT_LOGS=str(state/'logs'))
    import requests, publicsuffixlist
    from spiderfoot import SpiderFootHelpers, SpiderFootDb, SpiderFootCorrelator
    from sflib import SpiderFoot
    from sfscan import SpiderFootScanner
    from modules.sfp_arin import sfp_arin
    # ARIN contact records may enrich a domain; do not pivot into person-name searches.
    sfp_arin.watchedEvents=lambda self:['DOMAIN_NAME']
    target=a.target.rstrip('.').encode('idna').decode('ascii').lower()
    target_type=SpiderFootHelpers.targetTypeFromString(target)
    if target_type!='INTERNET_NAME': raise ValueError('Supply a domain without a URL, wildcard or port.')
    selected=['sfp_crt','sfp_arin','sfp_email','sfp__stor_db']
    ignored=[p.name for p in (SOURCE/'modules').glob('sfp_*.py') if p.stem not in selected]
    modules=SpiderFootHelpers.loadModulesAsDict(str(SOURCE/'modules'),ignored)
    if 'sfp_crt' in modules: modules['sfp_crt']['opts'].update(verify=False,fetchcerts=False)
    suffix=Path(publicsuffixlist.__file__).parent/'public_suffix_list.dat'
    if a.fixture:
        fixture_suffix=state/'fixture-suffix-list.dat'
        fixture_suffix.write_bytes(suffix.read_bytes().replace(b'// ===END ICANN DOMAINS===',b'test\n// ===END ICANN DOMAINS==='))
        suffix=fixture_suffix
    config={'_debug':False,'_maxthreads':2,'__logging':True,'__outputfilter':None,'_useragent':'Nova OSINT SpiderFoot pilot','_dnsserver':'','_fetchtimeout':10,'_internettlds':suffix.read_text(encoding='utf-8'),'_internettlds_cache':72,'_genericusers':','.join(sorted(SpiderFootHelpers.usernamesFromWordlists(['generic-usernames']))),'__database':str(state/'spiderfoot.sqlite'),'__modules__':modules,'__correlationrules__':[],'__globaloptdescs__':{},'_socks1type':'','_socks2addr':'','_socks3port':'','_socks4user':'','_socks5pwd':''}
    db=SpiderFootDb(config,init=True)
    rules=SpiderFootHelpers.loadCorrelationRulesRaw(str(SOURCE/'correlations')+os.sep,['template.yaml'])
    config['__correlationrules__']=SpiderFootCorrelator(db,rules).get_ruleset()
    db.close()
    failures=[]
    class Errors(logging.Handler):
        def emit(self,record):
            if record.levelno>=logging.ERROR: failures.append(record.getMessage())
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    logging.getLogger().addHandler(Errors())
    transport={'requests':0,'blocked':[],'responses':[]}
    lock=threading.Lock(); deadline=time.monotonic()+a.deadline
    original_init=SpiderFoot.__init__; original_fetch=SpiderFoot.fetchUrl; original_send=requests.Session.send
    def verified_init(self,*args,**kwargs):
        original_init(self,*args,**kwargs)
        ssl._create_default_https_context=ssl.create_default_context
    SpiderFoot.__init__=verified_init
    def allow(url):
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme!='https' or parsed.hostname not in PROVIDERS or parsed.port not in (None,443) or parsed.username is not None or parsed.password is not None: raise ValueError('Provider/HTTPS boundary rejected '+url)
    def gate_send(self,request,**kwargs):
        allow(request.url)
        if kwargs.get('verify') is False: raise ValueError('TLS verification cannot be disabled in this profile.')
        with lock:
            if time.monotonic()>deadline or transport['requests']>=a.max_requests:
                transport['blocked'].append('request/deadline budget reached'); raise TimeoutError('SpiderFoot request/deadline budget reached')
            transport['requests']+=1
        return original_send(self,request,**kwargs)
    requests.Session.send=gate_send
    def fixture(url):
        parsed=urllib.parse.urlparse(url)
        if parsed.hostname=='crt.sh': payload=[{'id':1,'name_value':'mail.example.test\nwww.example.test'}]
        elif '/pocs;domain=' in url: payload={'pocs':{'pocRef':{'@name':'Person, Fixture','$':'https://whois.arin.net/rest/poc/FIXTURE'}}}
        else: payload={'poc':{'email':'operator@example.test'}}
        body=json.dumps(payload)
        return {'code':'200','content':body,'headers':{},'realurl':url,'status':'OK'}
    def verified_fetch(self,url,*args,**kwargs):
        try:
            allow(url)
            if time.monotonic()>deadline: raise TimeoutError('SpiderFoot deadline reached')
            kwargs['verify']=True
            kwargs['timeout']=min(kwargs.get('timeout',10),10)
            if a.fixture:
                with lock:
                    if transport['requests']>=a.max_requests: raise TimeoutError('SpiderFoot request budget reached')
                    transport['requests']+=1
                result=fixture(url)
            else: result=original_fetch(self,url,*args,**kwargs)
            transport['responses'].append({'provider':urllib.parse.urlparse(url).hostname,'code':result.get('code'),'has_content':result.get('content') is not None})
            return result
        except Exception as exc:
            transport['blocked'].append(str(exc))
            return {'code':None,'content':None,'headers':{},'realurl':url,'status':str(exc)}
    SpiderFoot.fetchUrl=verified_fetch
    scan_id=SpiderFootHelpers.genScanInstanceId()
    scanner=SpiderFootScanner('OSINT '+target,scan_id,target,target_type,selected,config)
    db=SpiderFootDb(config)
    rows=db.scanResultEvent(scan_id)
    correlations=db.scanCorrelationList(scan_id)
    db.close()
    events=[dict(zip(COLUMNS,row)) for row in rows]
    (output/'spiderfoot-events.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
    with (output/'spiderfoot-events.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=COLUMNS);writer.writeheader();writer.writerows(events)
    graph=json.loads(SpiderFootHelpers.buildGraphJson(target,rows)) if rows else {'nodes':[],'edges':[]}
    (output/'spiderfoot-graph.json').write_text(json.dumps(graph,indent=2),encoding='utf-8')
    gexf=SpiderFootHelpers.buildGraphGexf(target,'SpiderFoot '+target,rows) if rows else b''
    (output/'spiderfoot-graph.gexf').write_bytes(gexf)
    template=(ROOT/'data/spiderfoot-report-template.html').read_text(encoding='utf-8')
    payload=json.dumps({'target':target,'fixture':a.fixture,'graph':graph,'events':events},ensure_ascii=False).replace('<',chr(92)+'u003c')
    (output/'spiderfoot-report.html').write_text(template.replace('__SPIDERFOOT_DATA__',payload),encoding='utf-8')
    partial=bool(failures or transport['blocked'] or any(not response['has_content'] or str(response['code']) not in ['200','201'] for response in transport['responses']))
    summary={'target':target,'scan_id':scan_id,'native_status':scanner.status,'evidence_state':'partial' if partial else 'completed-selected-profile','fixture':a.fixture,'modules':selected,'rules_loaded':len(config['__correlationrules__']),'correlations':correlations,'events':len(events),'graph_nodes':len(graph['nodes']),'graph_edges':len(graph['edges']),'transport':transport,'errors':failures,'tls_verified':ssl._create_default_https_context is ssl.create_default_context,'evidence_boundary':'Synthetic fixtures only.' if a.fixture else 'Selected public provider queries; no claim of comprehensive coverage or identity attribution.'}
    (output/'spiderfoot-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return 3 if partial else (0 if scanner.status=='FINISHED' else 1)
if __name__=='__main__': raise SystemExit(main())