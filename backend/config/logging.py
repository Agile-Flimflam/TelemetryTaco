"""Log formatters that keep the fields passed as logger.info(..., extra={...}).

The stdlib formatters drop anything not named in their format string, which is how the
task logs lost their counts.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

# Attributes every LogRecord has. Anything else on a record came from `extra`.
_BLANK_RECORD = logging.LogRecord("", logging.INFO, "", 0, "", None, None)
_RECORD_ATTRIBUTES = frozenset(vars(_BLANK_RECORD)) | {"message", "asctime"}
# Celery's task-result logs attach `data`, which repeats the message plus the task's
# arguments: whole event payloads, properties included. Leave it out.
_IGNORED_EXTRAS = frozenset({"data"})


def extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: value
        for key, value in vars(record).items()
        if key not in _RECORD_ATTRIBUTES and key not in _IGNORED_EXTRAS and not key.startswith("_")
    }


class TextFormatter(logging.Formatter):
    """`time level logger message key=value ...`, for reading in a terminal."""

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        fields = extra_fields(record)
        if not fields:
            return line
        rendered = " ".join(f"{key}={value}" for key, value in fields.items())
        # Keep a traceback, if any, after the fields rather than splitting them from the message.
        head, newline, rest = line.partition("\n")
        return f"{head} {rendered}{newline}{rest}"


class JsonFormatter(logging.Formatter):
    """One JSON object per line, for log collectors."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **extra_fields(record),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)
