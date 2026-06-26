from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import ccxt


@dataclass(frozen=True)
class ExternalErrorInfo:
    kind: str
    message: str
    retryable: bool
    status_code: int

    def model_dump(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "retryable": self.retryable,
            "status_code": self.status_code,
        }


def classify_external_error(exc: Exception) -> ExternalErrorInfo:
    message = str(exc)[:240] or exc.__class__.__name__
    if isinstance(exc, (ccxt.AuthenticationError, ccxt.PermissionDenied)):
        return ExternalErrorInfo("credentials_invalid", message, False, 401)
    if isinstance(exc, (ccxt.BadSymbol, ccxt.BadRequest)):
        return ExternalErrorInfo("symbol_invalid", message, False, 400)
    if isinstance(exc, (ccxt.RateLimitExceeded, ccxt.DDoSProtection)):
        return ExternalErrorInfo("rate_limit", message, True, 429)
    if isinstance(exc, (ccxt.NetworkError, ccxt.RequestTimeout, ccxt.ExchangeNotAvailable)):
        return ExternalErrorInfo("network", message, True, 503)
    if isinstance(exc, ccxt.ExchangeError):
        return ExternalErrorInfo("exchange", message, True, 502)
    return ExternalErrorInfo("unknown", message, True, 500)
