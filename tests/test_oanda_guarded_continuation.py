from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch

from experiments.oanda_demo.guarded_probe import build_guarded_plan, execute_guarded
from experiments.oanda_demo.first_probe_reconcile import sanitize_trade
from experiments.oanda_demo.practice_risk import guard_probe_plan
from experiments.oanda_demo.lab import LabError
from tests.test_oanda_practice_risk import plan


def current_plan():
    result=plan(); now=datetime.now(timezone.utc)
    result.update(signal_time=(now-timedelta(hours=1, minutes=20)).isoformat(),
        generated_at=now.isoformat(), current_price_time=now.isoformat())
    return result


def trade():
    return {'id':'5', 'instrument':'GBP_USD', 'initialUnits':'888',
        'currentUnits':'888', 'price':'1.35433', 'openTime':'2026-09-07T22:36:24.165279973Z',
        'state':'OPEN', 'realizedPL':'0', 'unrealizedPL':'-0.85', 'financing':'0',
        'stopLossOrder':{'state':'PENDING','type':'STOP_LOSS','tradeID':'5','price':'1.35320'},
        'takeProfitOrder':{'state':'PENDING','type':'TAKE_PROFIT','tradeID':'5','price':'1.35574'}}


class GuardedContinuationTests(TestCase):
    def client(self):
        c=Mock();c.instrument_metadata.return_value={'GBP_USD':{'minimum_trade_size':1}}
        return c

    def test_guarded_plan_uses_exact_conservative_sizing(self):
        with patch('experiments.oanda_demo.guarded_probe.build_probe_plan',return_value=current_plan()):
            result=build_guarded_plan(self.client())
        self.assertEqual(result['signed_units'],699)
        self.assertLessEqual(result['estimated_max_virtual_risk_usd'],1)

    def test_existing_exposure_blocks_before_more_reads(self):
        c=self.client()
        with patch('experiments.oanda_demo.guarded_probe.build_probe_plan',return_value={'eligible':False,'reason':'existing_practice_trade_or_order'}):
            result=build_guarded_plan(c)
        self.assertFalse(result['eligible']);c.instrument_metadata.assert_not_called()

    def test_stale_price_or_candle_is_blocked(self):
        for key,hours in [('signal_time',4),('current_price_time',1),('generated_at',1)]:
            p=current_plan();p[key]=(datetime.now(timezone.utc)-timedelta(hours=hours)).isoformat()
            with self.subTest(key=key),patch('experiments.oanda_demo.guarded_probe.build_probe_plan',return_value=p):
                self.assertFalse(build_guarded_plan(self.client())['eligible'])

    def test_future_uncompleted_candle_blocked(self):
        p=current_plan();p['signal_time']=datetime.now(timezone.utc).isoformat()
        with patch('experiments.oanda_demo.guarded_probe.build_probe_plan',return_value=p):
            self.assertFalse(build_guarded_plan(self.client())['eligible'])

    def test_local_permit_is_claimed_once_before_delegating(self):
        p=guard_probe_plan(current_plan())
        with tempfile.TemporaryDirectory() as directory:
            permit=str(Path(directory)/'permit.json')
            with patch('experiments.oanda_demo.guarded_probe._load_permit'),patch('experiments.oanda_demo.guarded_probe.execute_plan',return_value={'status':'mock_fill'}) as execute:
                execute_guarded(self.client(),p,permit)
                with self.assertRaises(LabError):execute_guarded(self.client(),p,permit)
                self.assertEqual(execute.call_count,1)

    def test_reconcile_open_checks_state_not_presence_only(self):
        p=trade(); report=sanitize_trade(p)
        self.assertTrue(report['both_original_protective_orders_pending'])
        self.assertEqual(report['entry_to_original_stop_risk_before_slippage_usd'],1.00344)
        p['stopLossOrder']['state']='CANCELLED'
        self.assertFalse(sanitize_trade(p)['both_original_protective_orders_pending'])

    def test_reconcile_closed_reports_actuals_separately(self):
        p=trade();p.update(state='CLOSED',currentUnits='0',realizedPL='-1.01',unrealizedPL='0',financing='-0.01',closeTime='2026-09-08T03:00:00Z',averageClosePrice='1.35319')
        result=sanitize_trade(p)
        self.assertEqual(result['realized_price_pl_virtual_usd'],-1.01)
        self.assertEqual(result['financing_virtual_usd'],-.01)
        self.assertIsNone(result['both_original_protective_orders_pending'])
        self.assertNotIn('"id"',json.dumps(result))

    def test_reconcile_rejects_unexpected_fill(self):
        for key,value in [('id','6'),('instrument','EUR_USD'),('price','1.3'),('initialUnits','999')]:
            p=trade();p[key]=value
            with self.subTest(key=key),self.assertRaises(LabError):sanitize_trade(p)
