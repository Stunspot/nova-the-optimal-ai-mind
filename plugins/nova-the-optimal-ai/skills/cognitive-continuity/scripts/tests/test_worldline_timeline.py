from __future__ import annotations
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import worldline_timeline as timeline
import workspace_runtime as runtime
import continuity_store_v2 as store

NOW = datetime(2026, 9, 13, 20, tzinfo=timezone.utc)
OWNER = {'user':'owner','agent':'nova','project':'*','thread':None}
MANIFEST = {'format':runtime.FORMAT,'scope':OWNER}
LINK = r'E:\Notes\conversation-0123456789abcdef0123456789.md'

def row(key='EP-one', project='*', **changes):
    event = {'format':'cd-worldline-event/v2','title':'Explored how memory works','kind':'exploration',
      'disposition':'recorded','occurred_at':'2026-09-01T12:00:00Z','ended_at':None,
      'time_basis':'observed','time_precision':'instant',
      'sources':[{'kind':'artifact','locator':LINK,'label':'Source','owner':'owner'}],
      'topics':['memory'],'related_ids':[],'supersedes':[]}
    result = {'id':key,'type':'message','recorded_at':'2026-09-02T12:00:00Z',
      'valid_from':'2026-09-01T12:00:00Z','valid_to':None,'expires_at':None,
      'scope':{**OWNER,'project':project},'source':{'kind':'agent','authority':'user-request','locator':LINK},
      'content':event['title'],'sensitivity':'ordinary','retention':'until-user-forgets',
      'tags':[],'worldline_event':event}
    result.update(changes)
    return result

def select(rows, **request):
    return timeline.select_worldline_rows(MANIFEST, rows, {'scope':{},'as_of':NOW.isoformat(),**request}, NOW)

class SelectionTests(unittest.TestCase):
    def test_projectless_and_cross_project_recognition_exact_owner(self):
        values=[row(),row('EP-p','a'),row('EP-q','b')]
        foreign=row('EP-foreign'); foreign['scope']['user']='different'
        values.append(foreign)
        result,families,coverage=select(values)
        self.assertEqual(3,len(result)); self.assertEqual(3,coverage['eligible_events'])
        self.assertNotIn('EP-foreign',json.dumps([result,families,coverage]))
        self.assertEqual(1,len(select(values,scope={'project':'a'})[0]))
        self.assertTrue(any(item['scope']['project'] is None for item in result))
        with self.assertRaises(runtime.ContinuityError): select(values,scope={'user':'different'})
        with self.assertRaises(runtime.ContinuityError): select(values,scope={'user':'*'})

    def test_occurrence_time_survives_expired_current_validity(self):
        value=row(valid_to='2026-09-02T12:00:00Z')
        value['worldline_event']['ended_at']='2026-09-01T13:00:00Z'
        value['worldline_event']['time_precision']='range'
        self.assertEqual(1,len(select([value])[0]))
        value['expires_at']='2026-09-10T12:00:00Z'
        self.assertEqual([],select([value],as_of='2026-09-03T12:00:00Z')[0])

    def test_legacy_recorded_anchor_and_safe_pointer(self):
        value=row(); del value['worldline_event']
        value['valid_from']='2020-01-01T00:00:00Z'; value['content']='An old substantive exchange'
        item=select([value])[0][0]
        self.assertEqual('legacy_episode',item['origin'])
        self.assertEqual('recorded',item['time_basis'])
        self.assertEqual(value['recorded_at'],item['occurred_at'])
        self.assertEqual(LINK,item['sources'][0]['locator'])
        self.assertEqual([],select([value],include_legacy=False)[0])
        value['source']['locator']='javascript:invalid()'
        item=select([value])[0][0]
        self.assertEqual([],item['sources'])

    def test_valid_v1_without_optional_thread_projects_to_current_view(self):
        value=row();del value['worldline_event'];del value['scope']['thread'];del value['expires_at']
        timeline._validate(value,'episode.schema.json')
        manifest={'format':runtime.LEGACY_FORMAT,'scope':OWNER}
        items,_,_=timeline.select_worldline_rows(manifest,[value],{},NOW)
        self.assertIsNone(items[0]['scope']['thread'])

    def test_half_open_window_topics_token_search_and_kind(self):
        value=row()
        self.assertEqual(1,len(select([value],from_time='2026-09-01T12:00:00Z',to_time='2026-09-02T00:00:00Z',search='memory works',topics=['MEMORY'],kinds=['exploration'])[0]))
        self.assertEqual([],select([value],to_time='2026-09-01T12:00:00Z')[0])
        self.assertEqual([],select([value],search='memory nonexistent')[0])

    def test_linear_corrections_keep_identity_and_privacy_at_execution(self):
        a=row(); b=row('EP-two',recorded_at='2026-09-04T12:00:00Z',type='correction')
        b['worldline_event']['supersedes']=[a['id']]
        b['worldline_event']['title']=b['content']='Corrected recognition'
        result,families,_=select([a,b])
        self.assertEqual(a['id'],result[0]['id']); self.assertEqual(b['id'],result[0]['revision_id'])
        self.assertEqual(2,len(families[a['id']]))
        self.assertEqual(a['id'],select([a,b],as_of='2026-09-03T00:00:00Z')[0][0]['revision_id'])
        b['sensitivity']='sensitive'
        self.assertEqual([],select([a,b],as_of='2026-09-03T00:00:00Z')[0])
        b['sensitivity']='ordinary'; b['worldline_event']['disposition']='retracted'
        self.assertEqual([],select([a,b],as_of='2026-09-03T00:00:00Z')[0])
        self.assertEqual('retracted',select([a,b],mode='inspect',event_id=a['id'])[0][0]['disposition'])

    def test_explicitly_relaxed_current_description_does_not_reveal_old_private_text(self):
        a=row(sensitivity='sensitive'); b=row('EP-two',type='correction')
        b['worldline_event']['supersedes']=[a['id']]
        b['recorded_at']='2026-09-04T12:00:00Z'
        b['worldline_event']['title']=b['content']='Authorized ordinary recognition'
        self.assertEqual(b['content'],select([a,b])[0][0]['title'])
        self.assertEqual([],select([a,b],as_of='2026-09-03T12:00:00Z')[0])

    def test_references_and_facets_do_not_disclose_foreign_ids(self):
        a=row(); b=row('EP-foreign'); b['scope']['user']='different'
        a['worldline_event']['related_ids']=[b['id']]
        self.assertNotIn('EP-foreign',json.dumps(select([a,b])[0]))

    def test_missing_source_flag_does_not_erase_occurrence(self):
        result=select([row()],unreachable_source_ids=['EP-one'])[0]
        self.assertEqual(1,len(result)); self.assertEqual('unavailable',result[0]['content_availability'])
        self.assertEqual(LINK,result[0]['sources'][0]['locator'])
        self.assertEqual("unavailable",select([row(tags=["source-unreachable"])])[0][0]["content_availability"])

    def test_narrow_manifest_bounds_omitted_facets(self):
        manifest={'format':runtime.FORMAT,'scope':{**OWNER,'project':'a','thread':'t'}}
        a=row('EP-a','a');a['scope']['thread']='t'
        result=timeline.select_worldline_rows(manifest,[a,row('EP-b','b')],{},NOW)[0]
        self.assertEqual(['EP-a'],[v['id'] for v in result])

    def test_timezone_buckets_are_fixed_and_total(self):
        item=select([row()])[0][0]
        item['occurred_at']='2026-09-01T01:00:00Z'
        result=timeline._buckets([item],{'bucket':'day','display_offset_minutes':-360})
        self.assertEqual([{'period':'2026-08-31','events':1}],result['buckets'])

    def test_cursor_tamper_and_safe_link_rules(self):
        with self.assertRaises(runtime.ContinuityError):timeline._decode_cursor('corrupt')
        self.assertTrue(timeline._href(LINK).startswith('file:///E:/Notes/'))
        self.assertIsNone(timeline._href('task:actual-opaque-identifier'))
        with self.assertRaises(runtime.ContinuityError):timeline._href('javascript:alert(1)')

class RuntimeTests(unittest.TestCase):
    def test_real_capture_cli_replay_query_paging_render_and_mutation_boundary(self):
        with tempfile.TemporaryDirectory(dir='E:/' if os.name=='nt' and Path('E:/').exists() else None) as name:
            base=Path(name);root=base/'store'
            runtime.initialize_workspace(str(root),user='owner',agent='nova',project='*',thread=None,
                                         sensitivity='ordinary',retention='until-user-forgets')
            argv=['capture',str(root),'--current','--title','Discussed the shape of memory','--source',LINK,
                  '--event-key','first','--capture-mode','explicit','--authority','user-request']
            request=timeline._write_args(timeline.parser().parse_args(argv))
            receipt=store.capture_worldline(request)
            replay=store.capture_worldline(timeline._write_args(timeline.parser().parse_args(argv)))
            self.assertEqual(receipt['id'],replay['id']);self.assertEqual('duplicate_committed',replay['status'])
            argv2=argv.copy();argv2[argv2.index('--event-key')+1]='second';argv2[argv2.index('--title')+1]='</script><script>alert(1)</script>'
            store.capture_worldline(timeline._write_args(timeline.parser().parse_args(argv2)))
            query={'workspace':{'selection_mode':'generic_explicit','path':str(root),'grant_id':None},'page_size':1,'deadline_ms':30000}
            before=runtime.tree_digest(root)
            first=timeline.query_worldline(query)
            self.assertEqual(2,first['coverage']['eligible_events']);self.assertTrue(first['has_more'])
            second=timeline.query_worldline({**query,'cursor':first['next_cursor']})
            self.assertFalse(second['has_more']);self.assertNotEqual(first['entries'][0]['id'],second['entries'][0]['id'])
            overview=timeline.query_worldline({**query,'mode':'overview'})
            self.assertEqual(2,sum(b['events'] for b in overview['overview']['buckets']))
            event_id=receipt['episode_id']
            inspected=timeline.query_worldline({**query,'mode':'inspect','event_id':event_id})
            self.assertEqual(1,len(inspected['revisions']))
            rendered=timeline.render_worldline(query,base/'timeline.html')
            page=(base/'timeline.html').read_text(encoding='utf-8')
            self.assertEqual(2,rendered['rendered_events']);self.assertNotIn('</script><script>alert',page)
            self.assertIn('\\u003c/script',page);self.assertIn('Filters apply to this saved view.',page)
            self.assertEqual(before,runtime.tree_digest(root))
            output=subprocess.check_output([sys.executable,'-B',str(SCRIPTS/'worldline_timeline.py'),'overview',str(root),'--deadline-ms','30000'],text=True,encoding='utf-8')
            self.assertEqual(2,json.loads(output)['coverage']['eligible_events'])
            with self.assertRaises(runtime.ContinuityError):timeline.query_worldline({**query,'cursor':first['next_cursor'],'search':'changed'})
            argv3=['capture',str(root),'--supersedes',event_id,'--title','Corrected recognition','--event-key','correction','--authority','user-request']
            corrected=store.capture_worldline(timeline._write_args(timeline.parser().parse_args(argv3)))
            self.assertEqual(event_id,corrected['event_id'])
            with self.assertRaisesRegex(runtime.ContinuityError,'cursor_stale'):timeline.query_worldline({**query,'cursor':first['next_cursor']})
            with self.assertRaises(runtime.ContinuityError):timeline.render_worldline(query,base/'timeline.html')
            with self.assertRaises(runtime.ContinuityError):timeline.render_worldline(query,root/'not-a-projection.html')
            with mock.patch.object(timeline,'_unchanged',return_value=False):
                with self.assertRaisesRegex(runtime.ContinuityError,'snapshot_changed'):timeline.query_worldline(query)

if __name__=='__main__':unittest.main()
