"""Read-only OANDA credential diagnosis and practice account resolution.

Only fixed ``GET /v3/accounts`` requests are permitted. The practice endpoint is
used for normal operation. The live endpoint may be queried once, read-only,
only after a practice HTTP 401 so a misplaced live token can be identified.
No token or account identifier is ever printed.
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

LIVE_ORIGIN = "https://api-fxtrade.oanda.com"
ALLOWED_ORIGINS = {
    PRACTICE_ORIGIN: "Practice",
    LIVE_ORIGIN: "Live",
}
ACCOUNT_ID_RE = re.compile(r"[0-9]+(?:-[0-9]+){3}", re.ASCII)
TOKEN_PREFIXES = ("OANDA_DEMO_TOKEN", "OANDA_demo_API_token")
ACCOUNT_PREFIXES = ("OANDA_DEMO_ACCOUNT_ID", "OANDA_demo_account_ID")


class TokenRejected(LabError):
    """A fixed OANDA account-list endpoint returned HTTP 401."""

    def __init__(self, environment: str) -> None:
        self.environment = environment
        super().__init__(
            f"OANDA {environment} token check returned HTTP 401. No automatic retry."
        )


def _unwrap_secret(value: object, prefixes: tuple[str, ...]) -> tuple[str, bool]:
    """Remove only common copy/paste wrappers, never arbitrary token content."""
    secret = value.strip() if isinstance(value, str) else ""
    original = secret
    for _ in range(4):
        previous = secret
        folded = secret.casefold()
        for prefix in prefixes:
            marker = prefix + "="
            if folded.startswith(marker.casefold()):
                secret = secret[len(marker) :].strip()
                break
        if len(secret) >= 2 and secret[0] == secret[-1] and secret[0] in {"'", '"'}:
            secret = secret[1:-1].strip()
        if secret.casefold().startswith("bearer "):
            secret = secret[7:].strip()
        if secret == previous:
            break
    return secret, secret != original


def _normalized_token(value: object) -> tuple[str, bool]:
    token, adjusted = _unwrap_secret(value, TOKEN_PREFIXES)
    if (
        not token
        or len(token) > 4096
        or any(character.isspace() for character in token)
    ):
        raise LabError("Missing or invalid OANDA_DEMO_TOKEN; use secret storage.")
    return token, adjusted


def _normalized_account_id(value: object) -> tuple[str | None, bool]:
    account_id, adjusted = _unwrap_secret(value, ACCOUNT_PREFIXES)
    if not account_id or len(account_id) > 128:
        return None, adjusted
    return (
        account_id if ACCOUNT_ID_RE.fullmatch(account_id) else None,
        adjusted,
    )


def authorized_account_ids(
    token: object,
    opener=None,
    *,
    origin: str = PRACTICE_ORIGIN,
) -> tuple[str, ...]:
    """Return validated account IDs authorized by a token at a fixed endpoint."""
    if origin not in ALLOWED_ORIGINS:
        raise LabError("Unapproved OANDA API origin.")
    token, _ = _normalized_token(token)
    environment = ALLOWED_ORIGINS[origin]
    opener = opener or build_opener(NoRedirects())
    request = Request(
        origin + "/v3/accounts",
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        method="GET",
    )
    try:
        with opener.open(request, timeout=20) as response:
            body = response.read(MAX_RESPONSE + 1)
            if len(body) > MAX_RESPONSE:
                raise LabError(
                    f"OANDA {environment} account-list response exceeded the size limit."
                )
    except HTTPError as error:
        if error.code == 401:
            raise TokenRejected(environment) from None
        raise LabError(
            f"OANDA {environment} account-list check returned HTTP {error.code}. No automatic retry."
        ) from None
    except (URLError, TimeoutError):
        raise LabError(
            f"OANDA {environment} account-list check failed. No order was sent."
        ) from None

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise LabError(
            f"OANDA {environment} returned invalid account-list JSON."
        ) from None
    accounts = payload.get("accounts") if isinstance(payload, dict) else None
    if not isinstance(accounts, list) or not accounts:
        raise LabError(
            f"The OANDA {environment} token returned no authorized accounts."
        )

    identifiers: list[str] = []
    for account in accounts:
        identifier = account.get("id") if isinstance(account, dict) else None
        if (
            not isinstance(identifier, str)
            or len(identifier) > 128
            or not ACCOUNT_ID_RE.fullmatch(identifier)
            or identifier in identifiers
        ):
            raise LabError(f"OANDA {environment} returned an invalid account list.")
        identifiers.append(identifier)
    return tuple(identifiers)


def _resolve_from_authorized(
    authorized: tuple[str, ...], configured_account_id: object
) -> tuple[str, bool, bool]:
    configured, adjusted = _normalized_account_id(configured_account_id)
    if configured is not None:
        if configured in authorized:
            return configured, False, adjusted
        raise LabError(
            "OANDA_demo_account_ID is a valid-looking ID but is not authorized by the supplied practice token."
        )
    if len(authorized) == 1:
        return authorized[0], True, adjusted
    raise LabError(
        "The OANDA Practice token is valid and authorizes multiple accounts, but OANDA_demo_account_ID is not a valid matching v20 account ID."
    )


def resolve_account_id(
    token: object, configured_account_id: object, opener=None
) -> tuple[str, bool]:
    """Resolve a matching practice account; preserve the legacy two-value API."""
    authorized = authorized_account_ids(token, opener=opener)
    account_id, recovered, _ = _resolve_from_authorized(
        authorized, configured_account_id
    )
    return account_id, recovered


def diagnose_practice_credentials(
    token: object,
    configured_account_id: object,
    *,
    practice_opener=None,
    live_opener=None,
) -> tuple[str, bool, bool, bool]:
    """Resolve practice credentials and classify a possible live-only token.

    Returns ``(account_id, recovered, token_wrapper_removed,
    account_wrapper_removed)``. A live success is diagnostic only and always
    fails closed before any account ID is written or any further request occurs.
    """
    normalized_token, token_adjusted = _normalized_token(token)
    try:
        authorized = authorized_account_ids(
            normalized_token,
            opener=practice_opener,
            origin=PRACTICE_ORIGIN,
        )
    except TokenRejected:
        try:
            authorized_account_ids(
                normalized_token,
                opener=live_opener,
                origin=LIVE_ORIGIN,
            )
        except TokenRejected:
            raise LabError(
                "The stored OANDA token was rejected by both the Practice and Live account-list endpoints. Revoke it, generate a fresh personal access token from the intended OANDA profile, and replace OANDA_demo_API_token."
            ) from None
        raise LabError(
            "The stored token authenticates to OANDA Live but not OANDA Practice. Replace OANDA_demo_API_token with a token generated from the practice profile; no live trading request was made."
        ) from None

    account_id, recovered, account_adjusted = _resolve_from_authorized(
        authorized, configured_account_id
    )
    return account_id, recovered, token_adjusted, account_adjusted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve a read-only OANDA Practice account without exposing credentials."
    )
    parser.add_argument(
        "--output",
        default="state/oanda-resolved-account-id.txt",
        help="Private ephemeral output file.",
    )
    args = parser.parse_args(argv)
    try:
        account_id, recovered, token_adjusted, account_adjusted = (
            diagnose_practice_credentials(
                os.environ.get("OANDA_DEMO_TOKEN"),
                os.environ.get("OANDA_DEMO_ACCOUNT_ID"),
            )
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(account_id + "\n", encoding="utf-8")
        if token_adjusted or account_adjusted:
            print(
                "Normalized a harmless copy/paste wrapper around a stored credential. The secret value was not displayed."
            )
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
        print(
            str(error) if isinstance(error, LabError) else "Local file operation failed.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
