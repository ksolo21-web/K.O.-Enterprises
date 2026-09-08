import unittest
from decimal import Decimal
from experiments.oanda_demo.practice_risk import RiskError, guard_probe_plan

def plan():
    return dict(eligible=True, environment='practice', real_money=False,
        instrument='GBP_USD', direction='long', signed_units=888,
        reference_entry='1.35433', price_bound='1.35453', stop_loss='1.35320',
        take_profit='1.35574', hard_virtual_risk_cap_usd=1.0,
        estimated_max_virtual_risk_usd=0.9995)

class RiskTests(unittest.TestCase):
    def test_real_fill_example_sizes_at_worst_entry_and_allowance(self):
        p = plan(); r = guard_probe_plan(p)
        self.assertEqual(r['signed_units'], 699)
        self.assertEqual(r['estimated_max_virtual_risk_usd'], 0.99957)
        self.assertEqual(r['stop_loss'], p['stop_loss'])
        self.assertEqual(r['take_profit'], p['take_profit'])
        self.assertFalse(r['risk_limit_is_guaranteed'])
        self.assertEqual(p['signed_units'], 888)

    def test_short_sizing_and_idempotence(self):
        p=plan(); p.update(direction='short', signed_units=-888,
            price_bound='1.35413', stop_loss='1.35546', take_profit='1.35292')
        r=guard_probe_plan(p)
        self.assertEqual(r['signed_units'], -699)
        self.assertEqual(guard_probe_plan(r),r)

    def test_bad_values_fail_closed(self):
        for v in ['NaN','Infinity','-1','0',None,True]:
            p=plan(); p['price_bound']=v
            with self.subTest(v=v), self.assertRaises(RiskError): guard_probe_plan(p)

    def test_live_or_non_usd_is_rejected(self):
        for key,v in [('environment','live'),('real_money',True),('instrument','USD_JPY')]:
            p=plan(); p[key]=v
            with self.subTest(key=key),self.assertRaises(RiskError): guard_probe_plan(p)

    def test_invalid_brackets_rejected(self):
        for key,v in [('stop_loss','1.35600'),('price_bound','1.35600'),('take_profit','1.35440'),('direction','short')]:
            p=plan(); p[key]=v
            with self.subTest(key=key), self.assertRaises(RiskError):guard_probe_plan(p)

    def test_units_and_budget_never_increase(self):
        p=plan();p.update(signed_units=50, hard_virtual_risk_cap_usd=.05)
        r=guard_probe_plan(p)
        self.assertLessEqual(r['signed_units'],50)
        self.assertLessEqual(r['estimated_max_virtual_risk_usd'],.05)

    def test_nonintegral_units_rejected(self):
        for v in [0,True,1.2,'888']:
            p=plan();p['signed_units']=v
            with self.subTest(v=v),self.assertRaises(RiskError):guard_probe_plan(p)

    def test_small_risk_and_ineligible_cases(self):
        p=plan();p['hard_virtual_risk_cap_usd']=.00001
        self.assertFalse(guard_probe_plan(p)['eligible'])
        self.assertEqual(guard_probe_plan({'eligible':False}),{'eligible':False})

    def test_all_rounding_regressions_stay_inside_budget(self):
        for i in range(1,301):
            p=plan(); p['stop_loss']=str(Decimal('1.35433')-Decimal(i)/100000)
            r=guard_probe_plan(p)
            if r['eligible']:
                actual=abs(Decimal(p['price_bound'])-Decimal(p['stop_loss']))+Decimal('.00010')
                self.assertLessEqual(abs(r['signed_units'])*actual,Decimal('1'))

if __name__=='__main__':unittest.main()
