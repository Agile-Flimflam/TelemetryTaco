from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI

from events.api import router as events_router
from events.api.ratelimit import RateLimited

api = NinjaAPI(title="TelemetryTaco API", version="1.1.0")
api.add_router("/", events_router)


@api.exception_handler(RateLimited)
def rate_limited(request: HttpRequest, exc: RateLimited) -> HttpResponse:
    response = api.create_response(request, {"detail": str(exc)}, status=429)
    response["Retry-After"] = str(exc.retry_after)
    return response
