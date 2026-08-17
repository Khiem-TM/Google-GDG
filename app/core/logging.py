import logging
import re
from collections.abc import Callable

SENSITIVE_KEY_PATTERN = re.compile(r"(password|token|authorization|secret|nutrition|health)", re.IGNORECASE)


def redact_mapping(values: dict[str, object]) -> dict[str, object]:
    return {key: "[REDACTED]" if SENSITIVE_KEY_PATTERN.search(key) else value for key, value in values.items()}


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def redacted_extra(**values: object) -> dict[str, object]:
    return redact_mapping(values)


LogMethod = Callable[..., None]
