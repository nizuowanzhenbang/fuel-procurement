"""FastAPI 应用入口"""
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, SessionLocal, Base
from app.models.user import User, UserRole
from app.models.supplier import Supplier
from app.models.contract import FuelContract
from app.models.order import PurchaseOrder
from app.models.contract_approval import ContractApproval
from app.models.contract_price_history import ContractPriceHistory
from app.models.supplier_quality_score import SupplierQualityScore
from app.api import auth, suppliers, contracts, orders, dashboard, webhooks, integration
from app.api.deps import hash_password

_ = (
    User, Supplier, FuelContract, PurchaseOrder,
    ContractApproval, ContractPriceHistory, SupplierQualityScore,
)


def _create_default_users(db) -> None:
    defaults = [
        ("admin",    "admin123",    UserRole.ADMIN),
        ("buyer",    "buyer123",    UserRole.PROCUREMENT),
        ("approver", "approver123", UserRole.APPROVER),
        ("viewer",   "viewer123",   UserRole.VIEWER),
    ]
    created = []
    for username, pwd, role in defaults:
        if db.query(User).filter(User.username == username).first():
            continue
        db.add(User(
            username=username,
            hashed_password=hash_password(pwd),
            role=role,
            is_active=True,
            created_at=datetime.utcnow(),
        ))
        created.append(username)
    if created:
        db.commit()
        print(f"[启动] 已创建默认账户：{', '.join(created)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _create_default_users(db)
    finally:
        db.close()
    print(f"[启动] {settings.APP_NAME} v{settings.APP_VERSION} 已就绪")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="发电厂燃料采购管理系统：供应商准入 + 合同执行 + 订单履约",
    lifespan=lifespan,
)

allowed = settings.ALLOWED_ORIGINS or [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(suppliers.router)
app.include_router(contracts.router)
app.include_router(orders.router)
app.include_router(dashboard.router)
app.include_router(webhooks.router)
app.include_router(integration.router)


@app.get("/health", tags=["系统"])
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/", tags=["系统"])
def root():
    return {"message": f"欢迎使用 {settings.APP_NAME}", "docs": "/docs"}
