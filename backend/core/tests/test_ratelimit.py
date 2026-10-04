import pytest
from django.core.cache import cache
from django.test import RequestFactory
from django_ratelimit.core import is_ratelimited

from core.api.ratelimit import client_ip


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
