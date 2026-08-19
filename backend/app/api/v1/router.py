from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.manufacturing import router as manufacturing_router
from app.api.v1.supply_chain import router as supply_chain_router
from app.api.v1.verify import router as verify_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(verify_router)
api_router.include_router(manufacturing_router)
api_router.include_router(supply_chain_router)
api_router.include_router(intelligence_router)
