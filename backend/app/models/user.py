"""用户模型"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean
from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"             # 燃料部主任
    PROCUREMENT = "PROCUREMENT" # 采购员
    APPROVER = "APPROVER"       # 审批人
    VIEWER = "VIEWER"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    hashed_password = Column(String(200), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.PROCUREMENT, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
