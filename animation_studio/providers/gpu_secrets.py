"""GPU credential loading and redaction at configured logging output boundaries."""

import json
import logging
import os
from collections.abc import Mapping
from urllib.parse import quote, quote_plus

from pydantic import SecretStr

TOKEN_ENV = 'ANIMATION_GPU_TOKEN'


def load_gpu_token(environ: Mapping[str, str] | None = None) -> SecretStr:
    """Read one explicit variable. Never print values or fall back to a default."""
    value = (os.environ if environ is None else environ).get(TOKEN_ENV)
    if not isinstance(value, str) or not value or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ValueError('ANIMATION_GPU_TOKEN must contain a non-empty printable ASCII token')
    return SecretStr(value)


class SecretRedactingFormatter(logging.Formatter):
    """Redact final formatted output, including exception/stack text and extras.

    Wraps existing formatters. Raw LogRecords remain unchanged; install on every
    output handler, including handlers added later. Not a stdout/print scrubber.
    """

    def __init__(self, original: logging.Formatter | None = None):
        super().__init__()
        self._original = original or logging.Formatter()
        self._values: frozenset[str] = frozenset()

    def add_secret(self, secret: SecretStr):
        value = secret.get_secret_value()
        if not value:
            raise ValueError('Cannot redact an empty secret')
        self._values = self._values | {
            value,
            quote(value, safe=''),
            quote_plus(value),
            repr(value)[1:-1],
            repr(value.encode())[2:-1],
            json.dumps(value)[1:-1],
        }

    def format(self, record: logging.LogRecord) -> str:
        rendered = self._original.format(record)
        for value in sorted(self._values, key=len, reverse=True):
            rendered = rendered.replace(value, '[REDACTED]')
        return rendered


def configure_gpu_logging(secret: SecretStr) -> None:
    """Protect current root, GPU, HTTP and uvicorn handlers; repeat after reconfig.

    Creates a root stream handler if none exists. Does not alter logging levels,
    propagation or handler destinations. Previously registered tokens stay masked
    for late logs after token rotation. No secret is written to configuration.
    """
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    loggers = [root]
    for name, logger in list(logging.Logger.manager.loggerDict.items()):
        if isinstance(logger, logging.Logger) and name.startswith(
            ('animation_studio', 'httpx', 'httpcore', 'uvicorn')
        ):
            loggers.append(logger)
    for logger in loggers:
        for handler in logger.handlers:
            formatter = handler.formatter
            if not isinstance(formatter, SecretRedactingFormatter):
                formatter = SecretRedactingFormatter(formatter)
                handler.setFormatter(formatter)
            formatter.add_secret(secret)
