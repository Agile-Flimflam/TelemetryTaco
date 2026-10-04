import json
import logging
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

logger = logging.getLogger("telemetry_taco")

QueueFullPolicy = Literal["block", "drop_newest", "drop_oldest"]
_STOP = object()


@dataclass(frozen=True)
class QueuedEvent:
    distinct_id: str
    event_name: str
    properties: dict[str, Any]
    event_uuid: str
    sent_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "distinct_id": self.distinct_id,
            "event_name": self.event_name,
            "properties": self.properties,
            "event_uuid": self.event_uuid,
            "sent_at": self.sent_at,
        }


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.strip()
    if not normalized:
        raise ValueError("base_url must be a non-empty http:// or https:// URL")

    if "://" not in normalized:
        normalized = f"http://{normalized}"

    parsed = urllib.parse.urlparse(normalized)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url must be an absolute http:// or https:// URL")

    return normalized.rstrip("/")


class TelemetryTaco:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        *,
        batch_size: int = 50,
        flush_interval: float = 1.0,
        max_queue_size: int = 1000,
        request_timeout: float = 5.0,
        max_retries: int = 2,
        queue_full_policy: QueueFullPolicy = "drop_newest",
        _start_worker: bool = True,
    ):
        self.base_url = _normalize_base_url(base_url)
        self.batch_url = f"{self.base_url}/api/capture/batch"
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.queue_full_policy = queue_full_policy

        self._queue: queue.Queue[QueuedEvent | object] = queue.Queue(maxsize=max_queue_size)
        self._state_lock = threading.Lock()
        self._flush_requested = threading.Event()
        self._closed = False
        self._closing = False
        self._worker = None
        if _start_worker:
            self._worker = threading.Thread(
                target=self._run_worker,
                name="telemetry-taco-worker",
                daemon=True,
            )
            self._worker.start()

    def capture(
        self,
        distinct_id: str,
        event_name: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        with self._state_lock:
            if self._closed or self._closing:
                raise RuntimeError("TelemetryTaco client is closed")

            payload = QueuedEvent(
                distinct_id=distinct_id,
                event_name=event_name,
                properties=properties or {},
                event_uuid=str(uuid4()),
                sent_at=datetime.now(UTC).isoformat(),
            )
            self._enqueue(payload)

    def flush(self, timeout: float | None = None) -> None:
        deadline = None if timeout in (None, 0) else time.monotonic() + timeout
        self._flush_requested.set()

        while self._queue.unfinished_tasks:
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Timeout waiting for {self._queue.unfinished_tasks} event(s) to flush."
                )
            time.sleep(0.05)

        self._flush_requested.clear()

    def close(self, timeout: float | None = None) -> None:
        with self._state_lock:
            if self._closed or self._closing:
                return
            self._closing = True

        try:
            self.flush(timeout=timeout)
            self._queue.put(_STOP)
            if self._worker is not None:
                self._worker.join(timeout=timeout)
        except Exception:
            with self._state_lock:
                self._closing = False
            raise

        with self._state_lock:
            self._closed = True
            self._closing = False

    def __enter__(self) -> "TelemetryTaco":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _enqueue(self, payload: QueuedEvent) -> None:
        if self.queue_full_policy == "block":
            self._queue.put(payload, timeout=self.request_timeout)
            return

        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            if self.queue_full_policy == "drop_oldest":
                if self._replace_oldest_queued_event(payload):
                    logger.warning("TelemetryTaco queue full; dropped oldest event.")
                    return
                try:
                    self._queue.put_nowait(payload)
                    return
                except queue.Full:
                    logger.warning("TelemetryTaco queue full; dropped newest event.")
                    return

            logger.warning("TelemetryTaco queue full; dropped newest event.")

    def _replace_oldest_queued_event(self, payload: QueuedEvent) -> bool:
        with self._queue.mutex:
            pending_items = self._queue.queue
            if not pending_items or any(item is _STOP for item in pending_items):
                return False

            pending_items.popleft()
            pending_items.append(payload)
            return True

    def _run_worker(self) -> None:
        batch: list[QueuedEvent] = []
        last_flush = time.monotonic()
        stop_requested = False

        while True:
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                item = None

            if item is _STOP:
                self._queue.task_done()
                stop_requested = True

            if isinstance(item, QueuedEvent):
                batch.append(item)

            if self._flush_requested.is_set():
                stop_requested = self._drain_queue(batch) or stop_requested

            should_flush = (
                len(batch) >= self.batch_size
                or (batch and time.monotonic() - last_flush >= self.flush_interval)
                or (batch and self._flush_requested.is_set())
                or (batch and stop_requested)
            )

            if should_flush:
                self._flush_batch(batch)
                batch = []
                last_flush = time.monotonic()

            if stop_requested and not batch:
                return

    def _drain_queue(self, batch: list[QueuedEvent]) -> bool:
        stop_requested = False

        while len(batch) < self.batch_size:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break

            if item is _STOP:
                self._queue.task_done()
                stop_requested = True
                break

            if isinstance(item, QueuedEvent):
                batch.append(item)

        return stop_requested

    def _flush_batch(self, batch: list[QueuedEvent]) -> None:
        if not batch:
            return

        try:
            self._send_batch(batch)
        except Exception:
            logger.exception(
                "TelemetryTaco worker failed to send event batch; dropping %s event(s).",
                len(batch),
            )
        finally:
            for _ in batch:
                self._queue.task_done()

    def _send_batch(self, batch: list[QueuedEvent]) -> None:
        payload = {"events": [event.as_dict() for event in batch]}
        try:
            body = json.dumps(payload).encode("utf-8")
        except TypeError as exc:
            logger.error("TelemetryTaco failed to serialize event batch: %s", exc, exc_info=True)
            return

        request = urllib.request.Request(
            self.batch_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            },
            method="POST",
        )

        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
                    response.read()
                return
            except urllib.error.HTTPError as exc:
                if 400 <= exc.code < 500:
                    logger.error(
                        "TelemetryTaco rejected event batch: %s %s",
                        exc.code,
                        exc.reason,
                    )
                    return
                if attempt >= self.max_retries:
                    logger.error(
                        "TelemetryTaco server error after retries: %s %s",
                        exc.code,
                        exc.reason,
                    )
                    return
            except urllib.error.URLError as exc:
                if attempt >= self.max_retries:
                    logger.warning("TelemetryTaco network error after retries: %s", exc.reason)
                    return

            time.sleep(min(0.25 * (attempt + 1), 1.0))
