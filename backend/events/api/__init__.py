from ninja import Router

from .events import router as events_router
from .persons import router as persons_router

router = Router()
router.add_router("/", events_router)
router.add_router("/persons", persons_router)

__all__ = ["router"]
