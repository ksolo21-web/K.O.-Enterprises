"""Controlled transport evidence; these tests do not establish real model accuracy."""
import copy
import json
import re
import unittest
from unittest.mock import patch

from inspection_engine.core import DataError, SYSTEM_NAME
from inspection_engine.report_proposals import (loopback_provider,PAGE_SCHEMA,
    RELATION_SCHEMA,IDENT,CELL,IMAGE_ANCHOR)


class ProposalContractTests(unittest.TestCase):
    def setUp(self):
        self.request={'prompt':'synthetic source','images':[{'png':b'PNG'}],'schema':copy.deepcopy(PAGE_SCHEMA)}
        self.tags={'models':[{'name':'model:tag','digest':'a'*64}]}
        self.answer={'sections':[],'tables':[],'figures':[],'findings':[]}
        self.response={'model':'model:tag','done':True,'done_reason':'stop',
            'response':json.dumps(self.answer),'eval_count':12,
            'thinking':'DO NOT RECORD','context':[1,2,3],'unknown_field':'DO NOT RECORD'}

    def invoke(self,events,response=None,callback=None):
        with patch('inspection_engine.report_proposals.request_json',return_value=self.tags), \
             patch('inspection_engine.report_proposals.generate',return_value=response or self.response) as transport:
            result=loopback_provider('model:tag','a'*64,audit_event=callback or events.append)(self.request)
            return result,transport

    def test_audit_retains_exact_request_and_filtered_raw_result(self):
        events=[];answer,transport=self.invoke(events)
        self.assertEqual(answer,self.answer)
        self.assertEqual([e['kind'] for e in events],['generation_request','generation_response'])
        self.assertEqual(events[0]['payload'],transport.call_args.args[0])
        self.assertEqual(events[0]['payload']['images'],['UE5H'])
        self.assertEqual(events[1]['envelope']['response'],self.response['response'])
        self.assertEqual(events[1]['envelope']['eval_count'],12)
        self.assertTrue({'thinking','context','unknown_field'}.isdisjoint(events[1]['envelope']))

    def test_callback_cannot_mutate_live_payload_or_result(self):
        def mutate(event):
            if event['kind']=='generation_request':event['payload']['model']='changed'
            else:event['envelope']['response']='changed'
        answer,transport=self.invoke([],callback=mutate)
        self.assertEqual(answer,self.answer)
        self.assertEqual(transport.call_args.args[0]['model'],'model:tag')
        self.assertEqual(self.response['response'],json.dumps(self.answer))

    def test_request_audit_failure_prevents_generation(self):
        def fail(event):raise OSError('Synthetic evidence write failure')
        with patch('inspection_engine.report_proposals.request_json',return_value=self.tags), \
             patch('inspection_engine.report_proposals.generate') as transport:
            with self.assertRaises(OSError):loopback_provider('model:tag','a'*64,audit_event=fail)(self.request)
            transport.assert_not_called()

    def test_pin_failure_produces_no_generation_event(self):
        events=[]
        with patch('inspection_engine.report_proposals.request_json',return_value={'models':[]}), \
             patch('inspection_engine.report_proposals.generate') as transport:
            with self.assertRaises(DataError):loopback_provider('model:tag','a'*64,audit_event=events.append)(self.request)
            self.assertEqual(events,[]);transport.assert_not_called()

    def test_invalid_json_and_incomplete_results_remain_auditable(self):
        for change in ({'response':'{invalid'}, {'done_reason':'length'}, {'error':'synthetic failure'}):
            response=dict(self.response,**change);events=[]
            with self.subTest(change=change),self.assertRaises(DataError):self.invoke(events,response)
            self.assertEqual(len(events),2)
            self.assertEqual(events[1]['envelope']['response'],response['response'])

    def test_invalid_callback_rejected_before_transport(self):
        with self.assertRaises(DataError):loopback_provider('model:tag','a'*64,audit_event=True)

    def test_source_contract_excludes_known_invalid_proposals(self):
        props=PAGE_SCHEMA['properties']
        self.assertEqual(props['figures']['items']['properties']['region'],IMAGE_ANCHOR)
        self.assertEqual(set(props['findings']['items']['properties']['system']['enum']),set(SYSTEM_NAME))
        for category,field in [('sections','title'),('findings','location')]:
            self.assertEqual(props[category]['items']['properties'][field]['maxLength'],200)
        for category in ('sections','findings'):
            self.assertEqual(props[category]['items']['properties']['anchors']['minItems'],1)
        table=props['tables']['items']['properties']
        self.assertEqual(table['rows']['minItems'],1)
        self.assertEqual(table['rows']['items']['properties']['cells']['minItems'],1)
        blank=next(c['properties'] for c in CELL['anyOf'] if c['properties']['role'].get('const')=='blank')
        self.assertEqual(blank['anchors']['items'],IMAGE_ANCHOR)
        self.assertEqual(blank['anchors']['minItems'],1)
        self.assertEqual(RELATION_SCHEMA['properties']['relations']['items']['properties']['anchors']['minItems'],2)
        for invalid in ('bad id','bad/id','-bad','x'*61):self.assertIsNone(re.fullmatch(IDENT['pattern'],invalid))
        self.assertIsNotNone(re.fullmatch(IDENT['pattern'],'table-row:1'))


if __name__=='__main__':unittest.main()
