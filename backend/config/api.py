from ninja import NinjaAPI

from events.api import router as events_router

api = NinjaAPI(title="TelemetryTaco API", version="1.1.0")
api.add_router("/", events_router)
