#!/usr/bin/env python3
"""Create a small private case in a new folder; never overwrite existing records."""
import argparse,csv,io,json,os
from pathlib import Path
from check_packet import regular,ARTIFACTS,MATRIX_HEADERS,SOURCE_HEADERS,FORMAT

def create(output,case_id,candidate_id,employer,role,artifacts,purpose='real'):
    target=regular(output)
    if target.exists():raise ValueError('Destination exists; choose a new private case folder')
    if not all(isinstance(x,str)and x.strip()for x in [case_id,candidate_id,employer,role]):raise ValueError('Supply case/candidate reference, employer and role; use explicit unknown wording where needed')
    chosen=list(dict.fromkeys(artifacts or ['resume']))
    if any(x not in ARTIFACTS for x in chosen):raise ValueError('Unsupported artifact')
    case={'format':FORMAT,'case_id':case_id,'candidate_id':candidate_id,'purpose':purpose,'revision':1,'vacancy':{'employer':employer,'title':role,'coverage':'partial','source_ids':[],'deadline':{'status':'unknown','wording':'Not supplied yet','instant':None}},'artifacts':[{'id':a,'path':a+'.md','allowed':None,'required_format':'unknown','max_words':None,'max_characters':None}for a in chosen],'questions':[],'checks':[{'id':kind.upper()+'-001','kind':kind,'requirement':'Review material '+kind+' conditions from actual posting and user evidence','state':'unknown','blocking':True,'basis':'','next_action':'Inspect supplied evidence; ask only the unresolved material question.'}for kind in ['eligibility','instructions','privacy']],'submission':{'state':'not-submitted','authority_reference':None,'receipt_reference':None,'observed_at':None}}
    payload={'case.json':(json.dumps(case,ensure_ascii=False,indent=2)+'\n').encode()}
    for name,fields in [('source-register.csv',SOURCE_HEADERS),('evidence-claim-matrix.csv',MATRIX_HEADERS)]:
        stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerow(fields);payload[name]=stream.getvalue().encode()
    for a in chosen:payload[a+'.md']=('# '+a.replace('-',' ').title()+' draft\n').encode()
    target.parent.mkdir(parents=True,exist_ok=True);target.mkdir() # exclusive reservation; existing user folder never replaced
    try:
        for name,data in payload.items():
            with (target/name).open('xb')as f:f.write(data)
    except Exception:
        # Keep any incomplete case for recovery; never erase or retry over unknown output.
        raise ValueError('Creation incomplete; preserve '+str(target)+' and inspect its files before choosing a new output')
    return {'ok':True,'case':str(target),'state':'draft','selected':chosen,'next':'Retain posting/history under sources; fill accountable source and criterion records, then draft only selected files. Run check_packet.py to see exact remaining work.'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--case-id',required=True);p.add_argument('--candidate-id',default='candidate');p.add_argument('--employer',required=True);p.add_argument('--role',required=True);p.add_argument('--artifact',action='append',choices=sorted(ARTIFACTS));p.add_argument('--purpose',choices=['real','practice'],default='real');a=p.parse_args()
    try:r=create(a.output,a.case_id,a.candidate_id,a.employer,a.role,a.artifact,a.purpose)
    except(OSError,ValueError)as e:print(json.dumps({'ok':False,'error':str(e)},ensure_ascii=True));return 1
    print(json.dumps(r,ensure_ascii=True,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())