from datetime import datetime, timedelta, timezone
import io
import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.error import URLError
from experiments.oanda_demo.close_first_probe import check_grant, invalidated, put_known_close, close_if_invalidated, CLOSE_GRANT
from experiments.oanda_demo.first_probe_reconcile import sanitize_trade
from experiments.oanda_demo.lab import LabError
from tests.test_oanda_guarded_continuation import trade


def grant():
    return {'OANDA_PRACTICE_CLOSE_APPROVAL':CLOSE_GRANT,
        'OANDA_PRACTICE_CLOSE_UNTIL':(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()}


def market():
    return SimpleNamespace(signal_time=datetime.now(timezone.utc)-timedelta(hours=1,minutes=5),score_6=-.35,score_24=.76,candle_direction=-1)


class CloseFirstProbeTests(TestCase):
    def test_invalidation_requires_fresh_negative_signal(self):
        m=market();now=datetime.now(timezone.utc)
        self.assertTrue(invalidated(m,now))
        m.score_6=.1;self.assertFalse(invalidated(m,now))
        m.score_6=-.1;m.signal_time=now-timedelta(hours=4)
        self.assertFalse(invalidated(m,now))

    def test_missing_and_expired_grants_fail(self):
        with patch.dict('os.environ',{},clear=True),self.assertRaises(LabError):check_grant()
        p=grant();p['OANDA_PRACTICE_CLOSE_UNTIL']='2020-01-01T00:00:00Z'
        with patch.dict('os.environ',p),self.assertRaises(LabError):check_grant()

    def test_already_closed_does_not_issue_a_close(self):
        before=sanitize_trade(trade());before.update(state='CLOSED',current_units=0)
        c=Mock()
        with patch.dict('os.environ',grant()),patch('experiments.oanda_demo.close_first_probe.reconcile',return_value=before):
            r=close_if_invalidated(c)
        self.assertEqual(r['status'],'already_closed_no_action');c.candles.assert_not_called()

    def test_close_uses_only_fixed_practice_trade_route(self):
        c=Mock();c._account='101-001-1234567-001';c._token='private-fixture-token'
        c._opener.open.return_value=io.BytesIO(json.dumps({'orderFillTransaction':{
            'instrument':'GBP_USD','tradesClosed':[{'tradeID':'5'}], 'price':'1.35350','time':'2026-09-08T03:00:00Z'}}).encode())
        with patch.dict('os.environ',grant()):r=put_known_close(c)
        request=c._opener.open.call_args.args[0]
        self.assertEqual(request.get_method(),'PUT')
        self.assertEqual(request.full_url,'https://api-fxpractice.oanda.com/v3/accounts/101-001-1234567-001/trades/5/close')
        self.assertEqual(json.loads(request.data),{'units':'ALL'})
        self.assertNotIn('private-fixture-token',str(r))

    def test_transport_failure_never_retries_or_leaks(self):
        c=Mock();c._account='101-001-1234567-001';c._token='private-fixture-token'
        c._opener.open.side_effect=URLError('private diagnostic')
        with patch.dict('os.environ',grant()),self.assertRaises(LabError) as caught:put_known_close(c)
        self.assertEqual(c._opener.open.call_count,1)
        self.assertNotIn('private diagnostic',str(caught.exception))

    def scenario(self,unrelated=False):
        c=Mock();c.summary.return_value={'open_trade_count':1,'pending_order_count':2}
        c.pending_orders.return_value=[{'type':'STOP_LOSS','tradeID':'5'},{'type':'TAKE_PROFIT','tradeID':'6' if unrelated else '5'}]
        before=sanitize_trade(trade());after={**before,'state':'CLOSED','current_units':0}
        with patch.dict('os.environ',grant()),patch('experiments.oanda_demo.close_first_probe.reconcile',side_effect=[before,after]),patch('experiments.oanda_demo.close_first_probe._market_features',return_value=market()),patch('experiments.oanda_demo.close_first_probe.current_prices_without_units_available',return_value={'GBP_USD':{'tradeable':True,'time':datetime.now(timezone.utc)}}),patch('experiments.oanda_demo.close_first_probe.put_known_close',return_value={'close_fill_price':'1.35350'}) as put:
            if unrelated:
                with self.assertRaises(LabError):close_if_invalidated(c)
                put.assert_not_called()
                return None
            r=close_if_invalidated(c);self.assertEqual(put.call_count,1);return r

    def test_verified_invalidation_closes_and_reconciles_once(self):
        r=self.scenario()
        self.assertEqual(r['status'],'known_practice_trade_closed')
        self.assertFalse(r['stop_widened']);self.assertEqual(r['new_entries'],0)

    def test_unrelated_pending_order_blocks_close(self):
        self.scenario(unrelated=True)
