import ipaddress
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django_ratelimit.core import get_usage


class RateLimited(Exception):  # noqa: N818 - reads as the condition, like django-ratelimit's
    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Rate limit exceeded; retry after {retry_after} seconds")
        self.retry_after = retry_after


def rate_limit(
    rate_setting: str, method: str
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Limit a view per client IP, raising RateLimited when the client is over the limit.

    django-ratelimit's own decorator raises PermissionDenied, which Django turns into a 403 HTML
    page. Clients treat a 403 as a permanent rejection and drop the request, so this raises an
    exception the API maps to a 429 with Retry-After instead.

    The rate is read from the named setting on each request rather than at import, so it can be
    overridden in tests.
    """

    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            usage = get_usage(
                request,
                fn=view,
                key="ip",
                rate=getattr(settings, rate_setting),
                method=method,
                increment=True,
            )
            if usage is not None and usage["should_limit"]:
                # django-ratelimit's window still includes the second time_left points at, so the
                # next window opens one second later. time_left is negative when the cache is
                # unreachable; ask for a short wait then.
                raise RateLimited(retry_after=max(usage["time_left"] + 1, 1))
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


def client_ip(request: HttpRequest) -> str:
    """Return the address rate limits are keyed on.

    Behind a reverse proxy, REMOTE_ADDR is the proxy, so every client would share one bucket.
    X-Forwarded-For is only trusted when TRUSTED_PROXY_COUNT says how many proxies sit in front
    of the app. Each proxy appends the address it received the request from, so the client is
    the Nth entry from the right. Anything left of that was written by the client and can be
    spoofed, which is why the header is never read from the left.
    """
    remote_addr = request.META.get("REMOTE_ADDR", "")
    trusted_proxies = settings.TRUSTED_PROXY_COUNT
    if trusted_proxies <= 0:
        return remote_addr

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
    if len(hops) < trusted_proxies:
        return remote_addr

    candidate = hops[-trusted_proxies]
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return remote_addr
    return candidate
