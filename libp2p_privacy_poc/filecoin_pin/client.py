"""Minimal HTTP client for pinning/fetching bytes from a Filecoin pin service."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib import error, parse, request

from .errors import (
    PinClientError,
    PinConfigError,
    PinPayloadTooLargeError,
    PinResponseError,
)

DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_PIN_PAYLOAD_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class _Config:
    endpoint: str
    token: str
    timeout_seconds: float


def pin_bytes(data: bytes, name: str | None = None) -> str:
    config = _load_config()
    if not isinstance(data, (bytes, bytearray)):
        raise PinClientError("pin payload must be bytes")
    payload = bytes(data)
    if len(payload) > MAX_PIN_PAYLOAD_BYTES:
        raise PinPayloadTooLargeError(
            f"payload exceeds max size ({len(payload)} > {MAX_PIN_PAYLOAD_BYTES})"
        )

    body: Dict[str, Any] = {"data_b64": base64.b64encode(payload).decode("ascii")}
    if name:
        body["name"] = name
    response = _json_request(
        url=f"{config.endpoint}/pin",
        method="POST",
        token=config.token,
        timeout_seconds=config.timeout_seconds,
        payload=body,
    )
    cid = response.get("cid") or response.get("CID")
    if not isinstance(cid, str) or not cid.strip():
        raise PinResponseError("pin service response missing cid")
    return cid


def fetch_bytes(cid: str) -> bytes:
    config = _load_config()
    if not isinstance(cid, str) or not cid.strip():
        raise PinClientError("cid is required")

    query = parse.urlencode({"cid": cid})
    url = f"{config.endpoint}/fetch?{query}"
    req = request.Request(url=url, method="GET")
    req.add_header("Authorization", f"Bearer {config.token}")
    req.add_header("Accept", "application/octet-stream,application/json")

    try:
        with request.urlopen(req, timeout=config.timeout_seconds) as resp:
            raw = resp.read()
            content_type = (resp.headers.get("Content-Type") or "").lower()
    except error.HTTPError as exc:
        status = getattr(exc, "code", "unknown")
        raise PinResponseError(
            f"fetch request failed with status={status} at {_safe_endpoint(config.endpoint)}"
        ) from exc
    except error.URLError as exc:
        raise PinResponseError(
            f"fetch request failed at {_safe_endpoint(config.endpoint)}: {exc.reason}"
        ) from exc

    if "application/json" in content_type or _looks_like_json(raw):
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise PinResponseError("fetch response JSON decoding failed") from exc
        data_b64 = payload.get("data_b64")
        if not isinstance(data_b64, str):
            raise PinResponseError("fetch response missing data_b64")
        try:
            decoded = base64.b64decode(data_b64, validate=True)
        except Exception as exc:
            raise PinResponseError("fetch response data_b64 is invalid") from exc
        return decoded
    return raw


def _json_request(
    *,
    url: str,
    method: str,
    token: str,
    timeout_seconds: float,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    req = request.Request(url=url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read()
    except error.HTTPError as exc:
        status = getattr(exc, "code", "unknown")
        raise PinResponseError(
            f"pin request failed with status={status} at {_safe_endpoint(url)}"
        ) from exc
    except error.URLError as exc:
        raise PinResponseError(
            f"pin request failed at {_safe_endpoint(url)}: {exc.reason}"
        ) from exc

    try:
        response_payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise PinResponseError("pin service response is not valid JSON") from exc
    if not isinstance(response_payload, dict):
        raise PinResponseError("pin service response must be a JSON object")
    return response_payload


def _load_config() -> _Config:
    endpoint = os.environ.get("FILECOIN_PIN_ENDPOINT", "").strip()
    token = os.environ.get("FILECOIN_PIN_TOKEN", "").strip()
    timeout_raw = os.environ.get("FILECOIN_PIN_TIMEOUT_SECONDS", "").strip()

    if not endpoint:
        raise PinConfigError(
            "missing FILECOIN_PIN_ENDPOINT (expected pin service base URL)"
        )
    if not token:
        raise PinConfigError(
            "missing FILECOIN_PIN_TOKEN (expected bearer token for pin service)"
        )
    endpoint = endpoint.rstrip("/")
    timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    if timeout_raw:
        try:
            timeout_seconds = float(timeout_raw)
        except ValueError as exc:
            raise PinConfigError(
                "FILECOIN_PIN_TIMEOUT_SECONDS must be a positive number"
            ) from exc
        if timeout_seconds <= 0:
            raise PinConfigError(
                "FILECOIN_PIN_TIMEOUT_SECONDS must be greater than zero"
            )

    return _Config(endpoint=endpoint, token=token, timeout_seconds=timeout_seconds)


def _safe_endpoint(endpoint: str) -> str:
    parsed = parse.urlparse(endpoint)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return endpoint


def _looks_like_json(payload: bytes) -> bool:
    stripped = payload.lstrip()
    return bool(stripped) and stripped[:1] in {b"{", b"["}

