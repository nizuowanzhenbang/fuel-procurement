"""应用配置"""
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./fuel_procurement.db"
    SECRET_KEY: str = "fuel-procurement-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    APP_NAME: str = "发电厂燃料采购管理系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: Optional[List[str]] = None

    # 闭环集成：煤质化验系统（查询供应商信用分）
    QUALITY_SYSTEM_URL: str = ""
    QUALITY_INTEGRATION_SECRET: str = "coal-integration-shared-secret"
    # 闭环集成：煤场库存系统（接收入煤场通知 / 提供订单查询）
    INTEGRATION_SECRET: str = "coal-integration-shared-secret"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
