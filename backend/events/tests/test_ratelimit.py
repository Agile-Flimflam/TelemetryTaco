from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import RequestFactory
from django_ratelimit.core import is_ratelimited

from events.api.ratelimit import client_ip


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    cache.clear()
    yield
    cache.clear()


def _request(remote_addr: str = "10.0.0.1", forwarded_for: str | None = None):
    extra = {"REMOTE_ADDR": remote_addr}
    if forwarded_for is not None:
        extra["HTTP_X_FORWARDED_FOR"] = forwarded_for
    return RequestFactory().get("/api/insights", **extra)


def _hit(request) -> bool:
    return is_ratelimited(request, group="test", key="ip", rate="1/m", increment=True)


def test_client_ip_ignores_forwarded_for_by_default(settings):
    settings.TRUSTED_PROXY_COUNT = 0

    assert client_ip(_request(forwarded_for="203.0.113.7")) == "10.0.0.1"


@pytest.mark.parametrize(
    ("trusted_proxies", "forwarded_for", "expected"),
    [
        (1, "203.0.113.7", "203.0.113.7"),
        # The left entry was sent by the client, so it's never trusted over the proxy's entry.
        (1, "198.51.100.1, 203.0.113.7", "203.0.113.7"),
        (2, "198.51.100.1, 203.0.113.7, 10.0.0.2", "203.0.113.7"),
        (1, "2001:db8::1", "2001:db8::1"),
        # Fewer hops than configured proxies, or garbage, falls back to the socket address.
        (2, "203.0.113.7", "10.0.0.1"),
        (1, "not-an-ip", "10.0.0.1"),
        (1, "", "10.0.0.1"),
    ],
)
def test_client_ip_reads_forwarded_for_from_trusted_proxies(
    settings, trusted_proxies, forwarded_for, expected
):
    settings.TRUSTED_PROXY_COUNT = trusted_proxies

    assert client_ip(_request(forwarded_for=forwarded_for)) == expected


def test_forwarded_clients_share_one_bucket_when_proxy_is_not_trusted(settings):
    settings.TRUSTED_PROXY_COUNT = 0

    assert _hit(_request(forwarded_for="203.0.113.7")) is False
    assert _hit(_request(forwarded_for="198.51.100.9")) is True


def test_forwarded_clients_get_separate_buckets_behind_a_trusted_proxy(settings):
    settings.TRUSTED_PROXY_COUNT = 1

    assert _hit(_request(forwarded_for="203.0.113.7")) is False
    assert _hit(_request(forwarded_for="198.51.100.9")) is False
    assert _hit(_request(forwarded_for="203.0.113.7")) is True


@pytest.mark.django_db
def test_capture_over_the_limit_returns_429_with_retry_after(client, settings):
    settings.RATE_LIMIT_CAPTURE_EVENT = "1/m"
    payload = {"events": [{"distinct_id": "user-1", "event_name": "page_view"}]}

    first = client.post("/api/capture/batch", data=payload, content_type="application/json")
    second = client.post("/api/capture/batch", data=payload, content_type="application/json")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second["Content-Type"] == "application/json; charset=utf-8"
    assert second.json()["detail"].startswith("Rate limit exceeded")
    assert 1 <= int(second["Retry-After"]) <= 61


@pytest.mark.django_db
def test_reads_over_the_limit_return_429(client, settings):
    settings.RATE_LIMIT_LIST_EVENTS = "1/m"

    assert client.get("/api/events").status_code == 200
    assert client.get("/api/events").status_code == 429


@pytest.mark.django_db
def test_rate_limits_can_be_turned_off(client, settings):
    settings.RATE_LIMIT_CAPTURE_EVENT = "1/m"
    settings.RATELIMIT_ENABLE = False
    payload = {"distinct_id": "user-1", "event_name": "page_view"}

    for _ in range(3):
        response = client.post("/api/capture", data=payload, content_type="application/json")
        assert response.status_code == 200


@pytest.mark.django_db
def test_retry_after_is_exactly_when_the_limit_resets(client, settings):
    settings.RATE_LIMIT_LIST_EVENTS = "1/m"
    now = 1_700_000_000.5

    with patch("django_ratelimit.core.time.time", side_effect=lambda: now):
        client.get("/api/events")
        retry_after = int(client.get("/api/events")["Retry-After"])

        now += retry_after - 1
        assert client.get("/api/events").status_code == 429

        now += 1
        assert client.get("/api/events").status_code == 200
