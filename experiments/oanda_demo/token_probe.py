"""Read-only OANDA Practice token check and account-ID resolution.

The probe only calls ``GET /v3/accounts`` on the fixed practice hostname. It
never places orders and never prints tokens or account identifiers.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from .lab import LabError, MAX_RESPONSE, NoRedirects, PRACTICE_ORIGIN

ACCOUNTS_URL = PRACTICE_ORIGIN + "/v3/accounts"
ACCOUNT_ID_RE = re.compile(r"[0-9]+(?:-[0-9]+){3}", re.ASCII)


def _validated_token(value: object) -> str:
    token = value.strip() if isinstance(value, str) else ""
    if not token or any(character.isspace() for character in token):
        raise LabError("Missing or invalid OANDA_DEMO_TOKEN; use secret storage.")
    return token


def _configured_account_id(value: object) -> str | None:
    account_id = value.strip() if isinstance(value, str) else ""
    if not account_id or len(account_id) > 128:
        return None
    return account_id if ACCOUNT_ID_RE.fullmatch(account_id) else None


def authorized_account_ids(token: object, opener=None) -> tuple[str, ...]:
    """Return validated account IDs authorized by a practice token.

    The fixed endpoint is deliberately independent of the configured account ID,
    allowing token validity and account-ID configuration to be diagnosed
    separately without exposing either secret.
    """
    token = _validated_token(token)
    opener = opener or build_opener(NoRedirects())
    request = Request(
        ACCOUNTS_URL,
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        method="GET",
    )
    try:
        with opener.open(request, timeout=20) as response:
            body = response.read(MAX_RESPONSE + 1)
            if len(body) > MAX_RESPONSE:
                raise LabError("Practice account-list response exceeded the size limit.")
    except HTTPError as error:
        raise LabError(
            f"OANDA Practice token check returned HTTP {error.code}. No automatic retry."
        ) from None
    except (URLError, TimeoutError):
        raise LabError("OANDA Practice token check failed. No order was sent.") from None

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise LabError("OANDA Practice returned invalid account-list JSON.") from None
    accounts = payload.get("accounts") if isinstance(payload, dict) else None
    if not isinstance(accounts, list) or not accounts:
        raise LabError("The OANDA Practice token returned no authorized accounts.")

    identifiers: list[str] = []
    for account in accounts:
        identifier = account.get("id") if isinstance(account, dict) else None
        if (
            not isinstance(identifier, str)
            or len(identifier) > 128
            or not ACCOUNT_ID_RE.fullmatch(identifier)
            or identifier in identifiers
        ):
            raise LabError("OANDA Practice returned an invalid account list.")
        identifiers.append(identifier)
    return tuple(identifiers)


def resolve_account_id(
    token: object, configured_account_id: object, opener=None
) -> tuple[str, bool]:
    """Resolve a matching account ID, recovering only an unambiguous sole account.

    Returns ``(account_id, recovered)``. A syntactically valid but unauthorized
    configured ID never falls back to another account. An absent or malformed ID
    may be recovered only when the token authorizes exactly one practice account.
    """
    authorized = authorized_account_ids(token, opener=opener)
    configured = _configured_account_id(configured_account_id)
    if configured is not None:
        if configured in authorized:
            return configured, False
        raise LabError(
            "OANDA_demo_account_ID is a valid-looking ID but is not authorized by the supplied practice token."
        )
    if len(authorized) == 1:
        return authorized[0], True
    raise LabError(
        "The OANDA Practice token is valid and authorizes multiple accounts, but OANDA_demo_account_ID is not a valid matching v20 account ID."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve a read-only OANDA Practice account without exposing credentials."
    )
    parser.add_argument(
        "--output", default="state/oanda-resolved-account-id.txt", help="Private ephemeral output file."
    )
    args = parser.parse_args(argv)
    try:
        account_id, recovered = resolve_account_id(
            os.environ.get("OANDA_DEMO_TOKEN"),
            os.environ.get("OANDA_DEMO_ACCOUNT_ID"),
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(account_id + "\n", encoding="utf-8")
        if recovered:
            print(
                "OANDA Practice token is valid. Resolved the sole authorized practice account without exposing its ID. No orders sent."
            )
        else:
            print(
                "OANDA Practice token and configured account ID match. No orders sent."
            )
        return 0
    except (LabError, OSError) as error:
        print(str(error) if isinstance(error, LabError) else "Local file operation failed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
