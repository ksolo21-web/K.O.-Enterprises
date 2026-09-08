"""One-shot, risk-reducing close of the exact known Practice trade only.

Requires a short-lived explicit runtime grant and a fresh completed candle
contradicting the long entry. This discretionary exit is recorded separately;
it is not a result of the original fixed stop/target strategy. No new entry,
live route, stop modification, retry, or scheduler is implemented.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from urllib.request import Request
from urllib.error import HTTPError, URLError

from .account_audit import PracticeAuditClient
from .first_probe_reconcile import reconcile, EXPECTED_TRADE_ID
from .forward_lab import _market_features
from .forward_probe import current_prices_without_units_available
from .lab import LabError, MAX_RESPONSE, PRACTICE_ORIGIN

CLOSE_GRANT = 'CLOSE_KNOWN_PRACTICE_PROBE_ON_INVALIDATION'


def check_grant():
    if os.environ.get('OANDA_PRACTICE_CLOSE_APPROVAL') != CLOSE_GRANT:
        raise LabError('Missing Practice-only known-trade close grant.')
    try:
        expires=datetime.fromisoformat(os.environ['OANDA_PRACTICE_CLOSE_UNTIL'].replace('Z','+00:00'))
    except (KeyError, ValueError):
        raise LabError('Invalid Practice close-grant expiry.') from None
    now=datetime.now(timezone.utc)
    if expires.tzinfo is None or not now < expires <= now+timedelta(minutes=30):
        raise LabError('Practice close grant expired or exceeds thirty minutes.')


def invalidated(market, now):
    age=(now-market.signal_time-timedelta(hours=1)).total_seconds()
    if not 0 <= age <= 3900:
        return False
    return market.score_6 < 0 and market.candle_direction == -1


def put_known_close(client):
    check_grant()
    url=f'{PRACTICE_ORIGIN}/v3/accounts/{client._account}/trades/{EXPECTED_TRADE_ID}/close'
    request=Request(url, data=b'{"units":"ALL"}', method='PUT', headers={
        'Authorization':'Bearer '+client._token, 'Accept':'application/json',
        'Content-Type':'application/json'})
    try:
        with client._opener.open(request, timeout=25) as response:
            raw=response.read(MAX_RESPONSE+1)
        if len(raw)>MAX_RESPONSE:
            raise LabError('Practice close response exceeds size limit; reconcile, do not retry.')
        payload=json.loads(raw)
    except HTTPError as error:
        raise LabError(f'Practice close returned HTTP {error.code}; reconcile, do not retry.') from None
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        raise LabError('Practice close outcome uncertain; reconcile, do not retry.') from None
    fill=payload.get('orderFillTransaction') if isinstance(payload,dict) else None
    if (not isinstance(fill,dict) or fill.get('instrument')!='GBP_USD'
            or {str(row.get('tradeID')) for row in fill.get('tradesClosed',[]) if isinstance(row,dict)} != {EXPECTED_TRADE_ID}
            or fill.get('tradeOpened') or fill.get('tradeReduced')):
        raise LabError('Known Practice close fill not confirmed; reconcile, do not retry.')
    return {'close_fill_time':fill.get('time'), 'close_fill_price':fill.get('price')}


def close_if_invalidated(client):
    check_grant()
    before=reconcile(client)
    base={'environment':'practice','real_money':False,'before':before}
    if before['state']=='CLOSED':
        return {**base,'status':'already_closed_no_action','after':before}
    if before['state']!='OPEN' or before['current_units']!=888 or not before['both_original_protective_orders_pending']:
        raise LabError('Known Practice trade changed; no close attempted.')
    market=_market_features('GBP_USD',client.candles('GBP_USD'))
    now=datetime.now(timezone.utc)
    diagnostics={'signal_time':market.signal_time.isoformat(),'score_6':market.score_6,
        'score_24':market.score_24,'candle_direction':market.candle_direction}
    if not invalidated(market,now):
        return {**base,'status':'hold_no_fresh_invalidation','signal':diagnostics}
    price=current_prices_without_units_available(client)['GBP_USD']
    if not price['tradeable'] or not -10 <= (datetime.now(timezone.utc)-price['time']).total_seconds() <=120:
        return {**base,'status':'hold_price_not_fresh_or_tradeable','signal':diagnostics}
    summary=client.summary()
    pending=client.pending_orders()
    if summary['open_trade_count']!=1 or summary['pending_order_count']!=2 or len(pending)!=2:
        raise LabError('Practice exposure changed; reconcile without retry.')
    if any(str(row.get('tradeID'))!=EXPECTED_TRADE_ID or row.get('type') not in ('STOP_LOSS','TAKE_PROFIT') for row in pending):
        raise LabError('Unrelated Practice orders found; no close attempted.')
    fill=put_known_close(client)
    after=reconcile(client)
    if after['state']!='CLOSED' or after['current_units']!=0:
        raise LabError('Practice close submitted but not reconciled; do not retry.')
    return {**base,'status':'known_practice_trade_closed','after':after,
        'signal':diagnostics, **fill,
        'exit_classification':'discretionary_signal_invalidation',
        'new_entries':0,'stop_widened':False,
        'warning':'Virtual loss/profit only. This discretionary exit does not validate the original strategy.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Close only the known invalidated Practice probe.')
    parser.add_argument('--output',required=True);args=parser.parse_args(argv)
    try:
        report=close_if_invalidated(PracticeAuditClient.from_environment())
        path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        after=report.get('after',report['before'])
        print(f"Practice close step: {report['status']}; state={after['state']}; realized_price_pl={after['realized_price_pl_virtual_usd']:.5f}.")
        return 0
    except (LabError,OSError) as error:
        print(str(error) if isinstance(error,LabError) else 'Practice close output failed.',file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
