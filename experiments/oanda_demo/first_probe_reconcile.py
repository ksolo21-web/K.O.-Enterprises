"""Read-only reconciliation of the first known Practice probe, including closure.

The expected trade is pinned to its verified fill. No account identifier,
credential, absolute balance, or unrelated account activity is published.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import Request
from urllib.error import HTTPError, URLError

from .forward_lab import ForwardPracticeClient
from .lab import LabError, MAX_RESPONSE, PRACTICE_ORIGIN

EXPECTED_TRADE_ID = '5'
EXPECTED_INSTRUMENT = 'GBP_USD'
EXPECTED_UNITS = Decimal('888')
EXPECTED_ENTRY = Decimal('1.35433')
EXPECTED_STOP = Decimal('1.35320')
EXPECTED_TARGET = Decimal('1.35574')


def number(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise LabError('Invalid Practice trade numeric field.') from None
    if not result.is_finite():
        raise LabError('Non-finite Practice trade field.')
    return result


def sanitize_trade(trade):
    if not isinstance(trade, dict):
        raise LabError('Practice trade response is missing.')
    if (str(trade.get('id')) != EXPECTED_TRADE_ID
            or trade.get('instrument') != EXPECTED_INSTRUMENT
            or number(trade.get('initialUnits')) != EXPECTED_UNITS
            or number(trade.get('price')) != EXPECTED_ENTRY
            or not str(trade.get('openTime', '')).startswith('2026-09-07T22:36:24.')):
        raise LabError('Practice trade does not match the known first fill.')
    state = trade.get('state')
    if state not in ('OPEN', 'CLOSED', 'CLOSE_WHEN_TRADEABLE'):
        raise LabError('Unrecognized Practice trade state.')
    current = number(trade.get('currentUnits'))
    if (state == 'CLOSED' and current != 0) or (state == 'OPEN' and current <= 0):
        raise LabError('Inconsistent Practice trade state and units.')
    stop, target = trade.get('stopLossOrder'), trade.get('takeProfitOrder')
    def pending_protection(order, kind, price):
        return (isinstance(order, dict) and order.get('state') == 'PENDING'
            and order.get('type') == kind and str(order.get('tradeID')) == EXPECTED_TRADE_ID
            and number(order.get('price')) == price)
    protected = (pending_protection(stop, 'STOP_LOSS', EXPECTED_STOP)
        and pending_protection(target, 'TAKE_PROFIT', EXPECTED_TARGET)) if state == 'OPEN' else None
    return {
        'status': 'first_practice_probe_reconciled',
        'environment': 'practice', 'real_money': False,
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'trade_reference': hashlib.sha256(EXPECTED_TRADE_ID.encode()).hexdigest()[:12],
        'instrument': EXPECTED_INSTRUMENT, 'direction': 'long',
        'initial_units': int(EXPECTED_UNITS), 'current_units': float(current),
        'entry_price': str(EXPECTED_ENTRY), 'open_time': trade['openTime'],
        'state': state, 'close_time': trade.get('closeTime'),
        'average_close_price': trade.get('averageClosePrice'),
        'realized_price_pl_virtual_usd': float(number(trade.get('realizedPL', '0'))),
        'unrealized_pl_virtual_usd': float(number(trade.get('unrealizedPL', '0'))),
        'financing_virtual_usd': float(number(trade.get('financing', '0'))),
        'original_stop_loss': str(EXPECTED_STOP),
        'original_take_profit': str(EXPECTED_TARGET),
        'both_original_protective_orders_pending': protected,
        'entry_to_original_stop_risk_before_slippage_usd': float(EXPECTED_UNITS*(EXPECTED_ENTRY-EXPECTED_STOP)),
        'target_price_profit_before_costs_usd': float(EXPECTED_UNITS*(EXPECTED_TARGET-EXPECTED_ENTRY)),
        'warning': 'Practice amounts are virtual. Price P/L and financing are reported separately; no revenue claim.',
    }


def reconcile(client):
    # The existing client validates the account ID and blocks redirects.
    client.summary()  # Verify the same Practice account is USD-denominated.
    url = f'{PRACTICE_ORIGIN}/v3/accounts/{client._account}/trades/{EXPECTED_TRADE_ID}'
    request = Request(url, headers={'Authorization': 'Bearer '+client._token, 'Accept':'application/json'}, method='GET')
    try:
        with client._opener.open(request, timeout=25) as response:
            raw = response.read(MAX_RESPONSE+1)
        if len(raw) > MAX_RESPONSE:
            raise LabError('Practice trade response exceeds size limit.')
        payload = json.loads(raw)
    except HTTPError as error:
        raise LabError(f'Practice trade reconciliation returned HTTP {error.code}; no retry.') from None
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        raise LabError('Practice trade reconciliation failed; no order sent.') from None
    if not isinstance(payload, dict):
        raise LabError('Malformed Practice trade response.')
    return sanitize_trade(payload.get('trade'))


def main(argv=None):
    parser=argparse.ArgumentParser(description='Read-only first Practice trade reconciliation.')
    parser.add_argument('--output', required=True)
    args=parser.parse_args(argv)
    try:
        report=reconcile(ForwardPracticeClient.from_environment())
        path=Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
        print(f"First Practice probe: state={report['state']}, realized_price_pl={report['realized_price_pl_virtual_usd']:.5f}, unrealized_pl={report['unrealized_pl_virtual_usd']:.5f}, protection={report['both_original_protective_orders_pending']}.")
        return 0
    except (LabError, OSError) as error:
        print(str(error) if isinstance(error,LabError) else 'Practice reconciliation output failed.', file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
