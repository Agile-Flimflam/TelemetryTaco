import pytest

from events.services.exceptions import InvalidBatchError
from events.services.ingestion import CapturedEvent, enqueue_events


def test_enqueue_events_rejects_an_empty_batch():
    with pytest.raises(InvalidBatchError, match="at least one event"):
        enqueue_events([])


def test_enqueue_events_rejects_an_oversized_batch(settings):
    settings.MAX_CAPTURE_BATCH_SIZE = 1
    events = [CapturedEvent(distinct_id="u1", event_name="a")] * 2

    with pytest.raises(InvalidBatchError, match="maximum of 1 events"):
        enqueue_events(events)
