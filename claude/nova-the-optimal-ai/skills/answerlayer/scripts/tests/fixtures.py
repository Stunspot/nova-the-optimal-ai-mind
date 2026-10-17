"""Synthetic decision fixture; not research evidence, consent or a live policy."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).absolute().parents[1]))
from ledgerlib import *

def fixture():
 d=load(ROOT/'assets/reality-ledger.template/reality-ledger.json')
 d.update(ledger_id='RL-SYNTHETIC-DELIVERY',title='Synthetic delivery cutoff decision',owner='Fixture owner',scope='Fictional standard orders in Zone A',decision_use='Choose when to accept an order for next-day delivery',created_at='2026-09-01T12:00:00Z',updated_at='2026-09-02T12:00:00Z',example=True)
 d['baseline'].update(as_of='2026-09-01',text='Accept standard orders until 17:00 for next-day delivery. Keep express orders separate.',context={k:d[k] for k in ('scope','decision_use','owner')})
 source={'id':'S1','status':'accepted_delta','title':'Synthetic carrier notice','locator':'fixture://notice/paragraph1','publication_date':'2026-09-02','authority':'Fictional carrier for test only','access_status':'synthetic_fixture','accessed_at':'2026-09-02T10:00:00Z','origin_id':None,'supports':[{'claim':'Standard Zone A cutoff is16:00 starting September2','location':'paragraph1','relation':'supports','scope':d['scope']}]}
 d['sources']=[source]
 candidate={'id':'C1','status':'accepted_delta','claim':'Standard pickup moved one hour earlier','source_ids':['S1'],'answer_change':'17:00 becomes16:00 for standard Zone A orders','mechanism':'Earlier pickup removes the previous final hour of eligibility','event_date':'2026-09-02','publication_date':'2026-09-02','effective_date':'2026-09-02','threshold_date':'not_applicable','classification':'structural_event','confidence_basis':'One fictional direct notice; no independent corroboration claimed','counterfactual':'If the notice is rescinded, restore the prior cutoff after review','recheck':'On the next carrier notice or a missed pickup'}
 d['candidates']=[candidate]
 p={'id':'P1','status':'accepted_delta','before':'until 17:00','after':'until 16:00','mechanism':candidate['mechanism'],'source_ids':['S1'],'counterfactual':candidate['counterfactual'],'authority':'model_generated','approved_by':None,'approved_at':None,'base_version':1,'base_sha256':baseline_hash(d),'scope':d['scope'],'recheck':candidate['recheck'],'candidate_ids':['C1'],'source_hashes':{'S1':identity({k:v for k,v in source.items() if k!='status'})},'result_as_of':'2026-09-02'}
 d['patches']=[p]
 d['approvals']=[{'id':'A1','object_id':'P1','action':'approve','actor':'Fixture owner (synthetic)','at':'2026-09-02T11:00:00Z','scope':'patch-adoption','authorization_basis':'Synthetic recorded instruction to apply this exact fixture patch; no real authorization','base_sha256':p['base_sha256'],'patch_sha256':patch_hash(p),'expires_at':None}]
 return d
