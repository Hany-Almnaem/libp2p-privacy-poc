"""Errors for Filecoin Pin integration."""

from __future__ import annotations


class PinClientError(RuntimeError):
    """Base class for pin client failures."""


class PinConfigError(PinClientError):
    """Required pin client configuration is missing or invalid."""


class PinPayloadTooLargeError(PinClientError):
    """Payload exceeds configured pin request limit."""


class PinResponseError(PinClientError):
    """Pin service returned an invalid or unexpected response."""


class RecordValidationError(ValueError):
    """Proof verification record failed schema validation."""

