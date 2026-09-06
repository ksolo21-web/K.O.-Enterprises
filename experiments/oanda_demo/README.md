# OANDA demo laboratory — key reported, connection unverified

Kaleb offered a demo API with $50 virtual funds and a $500 target, and reported adding a demo API key on 2026-09-06. This is a separate research experiment, not company revenue. The saved credential cannot be inspected through the current GitHub connector and is not present in the local environment. No market dataset was fetched, no broker orders were sent, and no performance result is claimed.

The first stage is deliberately read-only: it checks the USD practice account and obtains up to 5000 completed EUR_USD hourly bid/ask candles. A deterministic historical replay compares fixed 1%, 2% and 5% risk scenarios from separate $50 virtual starting balances. A 70/30 chronological split separates development and holdout periods. Returns, settled balance drawdown, trade count and first attainment of $500 are reported, including non-attainment.

The baseline is a test instrument, not a claimed profitable strategy. It models bid/ask spread and 0.1 pip adverse slippage per side, uses only prior completed bars for signals and stops, and assumes the stop is hit first if both stop and target fall inside an hourly candle. Trades close within their entry hour; entries stop before 19:00 UTC. No financing advantage is invented. Exact commissions, intrabar liquidity, account margin closeout and intrabar drawdown still need validation before any forward demo execution.

## Secure connection

No OANDA plugin was found in the connected plugin directory on 2026-09-06. Keep the token out of chats, source code, issue/PR text and logs. Use GitHub Actions repository secrets named `OANDA_DEMO_TOKEN` and `OANDA_DEMO_ACCOUNT_ID`, restricted to a dedicated practice account. A token can be powerful even when our code is read-only; do not use a live-account token.

The supplied workflow is manual-only and bounded. It becomes runnable from GitHub's Actions interface once merged to the default branch. Adding secrets alone does not launch anything. Review the code before running it. It has no recurring schedule, no artifact upload and no broker-write capability. It uses standard public-repository runners, not larger paid runners. No billing or paid plan is enabled.

The workflow is now on `main`. After both secret names above are configured, open [OANDA practice research (read only)](https://github.com/ksolo21-web/K.O.-Enterprises/actions/workflows/oanda-practice-research.yml), choose **Run workflow**, select `main`, and run once. The connected GitHub tools expose result reads but no dispatch action. The 2026-09-06 repository run listing showed 14 CI runs and no OANDA run. Do not put the token or account ID into chat or public logs; the workflow passes them privately from secrets to the bounded process.

```sh
python -m experiments.oanda_demo.lab fetch
python -m experiments.oanda_demo.lab replay --input state/oanda-demo-candles.json
```

The API host is fixed to `https://api-fxpractice.oanda.com`; there is no environment option or live fallback. Only GET summary and account-specific EUR_USD candle routes are permitted. Redirects are rejected. HTTP errors do not print response bodies or credentials. Network reads require the user's separately supplied practice credentials and an explicit manual invocation. Corporate scheduled/external automation remains paused; this work does not remove `PAUSE_AUTONOMY` or change company control policy.

The next stage, after credentials arrive and data integrity is checked, is a forward **demo-only** executor with idempotent orders, practice-account verification, loss limits, reconciliation and an emergency stop. It has not been implemented or activated in this first stage. $50 → $500 is an experimental target, not a promised result or deadline; simulated outcomes never establish real-money profitability.

## Sources checked 2026-09-06

- Practice/live API environments: https://developer.oanda.com/rest-live-v20/development-guide/
- Token access: https://developer.oanda.com/rest-live-v20/authentication/
- Account-specific candles, price components and 5000-candle bound: https://developer.oanda.com/rest-live-v20/pricing-ep/
- Account summary: https://developer.oanda.com/rest-live-v20/account-ep/

Revalidate endpoint behavior against the actual practice account on first connection. Revalidate the protocol before a forward demo phase; a replay is not broker-execution validation.
