import ipaddress

from django.conf import settings
from django.http import HttpRequest


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
