"""Exact-decimal sizing for USD-quoted Practice brackets; no network access.

Budgets the worst permitted entry price plus a one-pip stop-slippage allowance.
This is a modeled loss budget, not a guaranteed maximum loss during a gap.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from typing import Any

INSTRUMENTS = frozenset({'EUR_USD', 'GBP_USD', 'AUD_USD', 'NZD_USD'})
STOP_SLIPPAGE_ALLOWANCE = Decimal('0.00010')
MAX_MODELED_RISK = Decimal('1.00')
MAX_UNITS = 1000

class RiskError(ValueError):
    pass

def positive_decimal(value: object) -> Decimal:
    if isinstance(value, bool):
        raise RiskError('Invalid bracket value.')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise RiskError('Invalid bracket value.') from None
    if not number.is_finite() or number <= 0:
        raise RiskError('Invalid bracket value.')
    return number

def guard_probe_plan(plan: dict[str, Any], minimum_units: int = 1) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise RiskError('Invalid Practice plan.')
    if plan.get('eligible') is not True:
        return dict(plan)
    if (plan.get('environment') != 'practice' or plan.get('real_money') is not False
            or plan.get('instrument') not in INSTRUMENTS):
        raise RiskError('Only whitelisted Practice plans may be sized.')
    units = plan.get('signed_units')
    if type(units) is not int or units == 0 or type(minimum_units) is not int or minimum_units < 1:
        raise RiskError('Invalid Practice unit count.')
    direction = 1 if units > 0 else -1
    if plan.get('direction') != ('long' if direction == 1 else 'short'):
        raise RiskError('Practice direction and units disagree.')
    try:
        reference, bound, stop, target = [positive_decimal(plan[k]) for k in
            ('reference_entry', 'price_bound', 'stop_loss', 'take_profit')]
        budget = min(positive_decimal(plan['hard_virtual_risk_cap_usd']), MAX_MODELED_RISK)
    except KeyError:
        raise RiskError('Incomplete Practice bracket.') from None
    valid = stop < reference <= bound < target if direction == 1 else target < bound <= reference < stop
    if not valid:
        raise RiskError('Invalid protective bracket or entry bound.')
    modeled_unit_risk = abs(bound - stop) + STOP_SLIPPAGE_ALLOWANCE
    allowed = int((budget / modeled_unit_risk).to_integral_value(rounding=ROUND_FLOOR))
    sized = min(abs(units), MAX_UNITS, allowed)
    if sized < minimum_units:
        return {**plan, 'eligible': False, 'reason': 'bounded_risk_below_minimum_units'}
    return {
        **plan,
        'signed_units': direction * sized,
        'hard_unit_cap': MAX_UNITS,
        'hard_virtual_risk_cap_usd': float(budget),
        'estimated_max_virtual_risk_usd': float(sized * modeled_unit_risk),
        'reference_stop_risk_usd': float(sized * abs(reference - stop)),
        'entry_bound_stop_risk_usd': float(sized * abs(bound - stop)),
        'stop_slippage_allowance_pips': 1.0,
        'risk_limit_is_guaranteed': False,
        'risk_sizing_version': 'entry_bound_plus_stop_allowance_v2',
        'risk_warning': 'A gap or stop slippage beyond the allowance can exceed this modeled loss budget.',
    }
