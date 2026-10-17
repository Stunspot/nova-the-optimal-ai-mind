import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
P=Path(__file__).resolve().parents[1]/'media_evidence.py'
spec=importlib.util.spec_from_file_location('media',P); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
CAPTION='WEBVTT\n\n00:00.000 --> 00:02.000\nThe sample contains 42 items.\n\n00:01.500 --> 00:03.000\nOverlap stays visible.\n'
class MediaEvidenceTests(unittest.TestCase):
    def test_caption_times_overlap_and_origin_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'a.vtt'; source.write_text(CAPTION)
            out=Path(temp)/'evidence'; m.ingest(source,out,'platform_automatic','https://example.test/v')
            receipt=json.loads((out/'evidence.json').read_text())
            self.assertEqual(receipt['origin'],'platform_automatic')
            self.assertEqual(receipt['segments'][1]['start_seconds'],1.5)
            self.assertEqual(receipt['review_status'],'unreviewed')
            self.assertEqual(receipt['artifact_sha256'],m.digest(source))
            self.assertEqual((out/'raw/a.vtt').read_bytes(),source.read_bytes())
            self.assertIn('42 items',(out/'transcript.md').read_text())
            self.assertEqual(m.ingest(source,out,'platform_automatic','https://example.test/v')['status'],'already_ingested')
    def test_tampered_output_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'a.srt'; p.write_text('1\n00:00:00,000 --> 00:00:01,000\nText\n')
            out=Path(temp)/'e'; m.ingest(p,out,'platform_caption','file-ref')
            (out/'transcript.md').write_text('changed')
            with self.assertRaises(m.MediaError): m.ingest(p,out,'platform_caption','file-ref')
    def test_tampered_receipt_source_or_segments_rejected(self):
        for field in ('source_ref','segments','origin','review_status'):
            with tempfile.TemporaryDirectory() as temp:
                source=Path(temp)/'a.vtt'; source.write_text(CAPTION)
                out=Path(temp)/'e'; m.ingest(source,out,'platform_caption','original')
                receipt=out/'evidence.json'; record=json.loads(receipt.read_text())
                if field=='segments': record[field][0]['text']='invented 999'
                else: record[field]='tampered'
                receipt.write_text(json.dumps(record))
                with self.assertRaises(m.MediaError): m.ingest(source,out,'platform_caption','original')
    def test_model_diagnostics_preserved_without_truth_probability(self):
        value={'segments':[{'start':0,'end':1,'text':'possibly speech','avg_logprob':-2.1,'no_speech_prob':0.8}]}
        s=m.whisper_segments(value)[0]
        self.assertEqual(s['diagnostics']['no_speech_prob'],0.8)
        self.assertEqual(s['review_status'],'unreviewed')
    def test_empty_asr_is_preserved(self): self.assertEqual(m.whisper_segments({'segments':[]}),[])
    def test_bad_times_and_nonfinite_rejected(self):
        for value in ({'start':2,'end':1,'text':'x'},{'start':float('nan'),'end':1,'text':'x'}):
            with self.assertRaises(m.MediaError): m.whisper_segments({'segments':[value]})
        with self.assertRaises(m.MediaError): m.caption_segments('00:70.000 --> 00:71.000\nx')
    def test_missing_or_malformed_cues_are_explicit(self):
        with self.assertRaises(m.MediaError): m.caption_segments('unreadable')
        with self.assertRaises(m.MediaError): m.caption_segments(CAPTION+'\nbroken cue')
    def test_caption_capture_has_no_video_cookie_or_plugin_inheritance(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'capture'
            def run(cmd,**kwargs):
                self.assertIn('--skip-download',cmd); self.assertIn('--ignore-config',cmd); self.assertIn('--no-plugin-dirs',cmd); self.assertIn('--no-playlist',cmd)
                self.assertNotIn('--cookies-from-browser',cmd); self.assertFalse(kwargs['shell'])
                raw=out/'raw'; (raw/'id.info.json').write_text(json.dumps({'id':'id','extractor_key':'Test','webpage_url':'https://example.test/video','subtitles':{'en':[]}})); (raw/'id.en.vtt').write_text(CAPTION)
                return type('Result',(),{'returncode':0,'stdout':'','stderr':''})()
            with patch.object(m.subprocess,'run',side_effect=run),patch.object(m.importlib.metadata,'version',return_value='fixture'):
                result=m.capture('https://example.test/video',out)
            self.assertEqual(result['transcripts'],1)
    def test_failed_capture_retains_failure_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'capture'
            with patch.object(m.subprocess,'run',return_value=type('R',(),{'returncode':1,'stdout':'','stderr':'fixture failure'})()):
                with self.assertRaises(m.MediaError): m.capture('https://example.test/video',out)
            self.assertEqual(json.loads((out/'capture.json').read_text())['status'],'failed')
if __name__=='__main__': unittest.main()
