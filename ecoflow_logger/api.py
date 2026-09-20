"""Minimal client for the EcoFlow Open Platform API.

Docs: https://developer.ecoflow.com/us/document/generalInfo

Authentication uses an HMAC-SHA256 signature over the sorted request
parameters, keyed with the account's secret key, per EcoFlow's signing
scheme.
"""

from __future__ import annotations

import hashlib
import hmac
import random
import time
from typing import Any

import requests

DEFAULT_BASE_URL = "https://api-e.ecoflow.com"
QUOTA_ALL_PATH = "/iot-open/sign/device/quota/all"


class EcoFlowAPIError(RuntimeError):
    """Raised when the EcoFlow API returns a non-success response."""


def _flatten(params: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten nested dicts/lists the way EcoFlow's signing scheme expects.

    Nested dict keys become ``parent.child`` and list items become
    ``parent[0]``. Only used for request bodies with nested params; the
    quota-all GET request used by this logger has no nested params.
    """
    flat: dict[str, Any] = {}
    for key, value in params.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, full_key))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    flat.update(_flatten(item, f"{full_key}[{i}]"))
                else:
                    flat[f"{full_key}[{i}]"] = item
        else:
            flat[full_key] = value
    return flat


def _qstring(params: dict[str, Any]) -> str:
    flat = _flatten(params)
    return "&".join(f"{k}={flat[k]}" for k in sorted(flat))


def _sign(request_params: dict[str, Any], auth_params: dict[str, Any], secret_key: str) -> str:
    """Build the string to sign and HMAC it.

    EcoFlow's scheme sorts the request params and the auth params
    (accessKey/nonce/timestamp) *separately* and concatenates the two
    query strings, rather than merging everything into one dict and
    sorting the combined set — request params come first.
    """
    parts = [_qstring(request_params)] if request_params else []
    parts.append(_qstring(auth_params))
    sign_str = "&".join(parts)
    return hmac.new(
        secret_key.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha256
    ).hexdigest()


class EcoFlowClient:
    """Talks to the EcoFlow Open Platform API for a single account."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        base_url: str = DEFAULT_BASE_URL,
        session: requests.Session | None = None,
        timeout: float = 10.0,
    ) -> None:
        if not access_key or not secret_key:
            raise ValueError("access_key and secret_key are required")
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    def _auth_params(self) -> dict[str, Any]:
        return {
            "accessKey": self.access_key,
            "nonce": str(random.randint(100000, 999999)),
            "timestamp": str(int(time.time() * 1000)),
        }

    def get_all_quota(self, device_sn: str) -> dict[str, Any]:
        """Fetch every reported quota value for a device.

        Returns the flat ``data`` dict from the API, e.g. with keys such
        as ``bmsMaster.soc``, ``pd.wattsInSum`` and ``pd.wattsOutSum``.
        """
        request_params = {"sn": device_sn}
        auth_params = self._auth_params()
        sign = _sign(request_params, auth_params, self.secret_key)

        headers = {**auth_params, "sign": sign}
        url = f"{self.base_url}{QUOTA_ALL_PATH}"
        response = self.session.get(
            url,
            params=request_params,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()

        code = str(payload.get("code", ""))
        if code not in ("0", "0000"):
            raise EcoFlowAPIError(
                f"EcoFlow API error (code={payload.get('code')!r}): "
                f"{payload.get('message')!r}"
            )
        return payload.get("data", {})
