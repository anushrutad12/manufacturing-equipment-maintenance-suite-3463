from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.core.settings import get_settings

openapi_tags = [
    {"name": "Auth", "description": "Authentication endpoints (JWT)."},
    {"name": "Equipment", "description": "Equipment registration and lifecycle management."},
    {"name": "Parameters", "description": "Parameter (sensor/metric) definitions."},
    {"name": "Thresholds", "description": "Equipment-specific parameter thresholds and baselines."},
    {"name": "Readings", "description": "Sensor/manual readings ingestion and retrieval."},
    {"name": "Alerts", "description": "Automatically generated alerts and lifecycle actions."},
    {"name": "Work Orders", "description": "Work order lifecycle management for maintenance actions."},
    {"name": "Work Order Tasks", "description": "Work order task checklist management."},
    {"name": "Work Order Parts", "description": "Track parts usage per work order and decrement inventory."},
    {"name": "Work Order Outcomes", "description": "Close-out outcomes with root cause and cost tracking."},
    {"name": "Spare Parts", "description": "Spare parts inventory management."},
]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: configured application instance.
    """
    s = get_settings()
    app = FastAPI(
        title=s.app_title,
        description=s.app_description,
        version=s.app_version,
        openapi_tags=openapi_tags,
    )

    allow_origins = s.allowed_origins if s.allowed_origins and s.allowed_origins != ["*"] else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get(
        "/",
        tags=["Health"],
        summary="Health check",
        description="Simple health check endpoint.",
        operation_id="health_check",
    )
    def health_check():
        """Health check endpoint."""
        return {"message": "Healthy"}

    return app


app = create_app()
