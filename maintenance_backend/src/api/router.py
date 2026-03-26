from fastapi import APIRouter

from src.api.routes import alerts, auth, equipment, parameters, parts, readings, work_orders

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(equipment.router)
api_router.include_router(parameters.router)
api_router.include_router(parameters.thresholds_router)
api_router.include_router(readings.router)
api_router.include_router(alerts.router)
api_router.include_router(work_orders.router)
for r in work_orders.subrouters:
    api_router.include_router(r)
api_router.include_router(parts.router)
