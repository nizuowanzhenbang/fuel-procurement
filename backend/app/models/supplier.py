"""供应商模型"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base


class SupplierStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"   # 待审核（新申请）
    ACTIVE = "ACTIVE"                   # 已准入合作中
    SUSPENDED = "SUSPENDED"             # 暂停合作
    BLACKLISTED = "BLACKLISTED"         # 黑名单
    ARCHIVED = "ARCHIVED"               # 归档（不再合作）


class SupplierTier(str, enum.Enum):
    STRATEGIC = "STRATEGIC"   # 战略合作（长协优先）
    PREFERRED = "PREFERRED"   # 优先采购
    QUALIFIED = "QUALIFIED"   # 合格供应商
    PROBATION = "PROBATION"   # 试用期


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="供应商编码")
    name = Column(String(200), unique=True, nullable=False, index=True, comment="供应商名称")
    short_name = Column(String(50), nullable=True, comment="简称")

    # 资质信息
    legal_representative = Column(String(50), nullable=True, comment="法定代表人")
    contact_person = Column(String(50), nullable=True, comment="联系人")
    contact_phone = Column(String(50), nullable=True, comment="联系电话")
    address = Column(String(300), nullable=True, comment="地址")
    business_license = Column(String(100), nullable=True, comment="营业执照号")
    registered_capital = Column(Float, nullable=True, comment="注册资本（万元）")

    # 业务信息
    coal_types = Column(String(200), nullable=True, comment="可供煤种（逗号分隔）")
    coal_origin = Column(String(200), nullable=True, comment="煤炭产地")
    annual_capacity = Column(Float, nullable=True, comment="年供应能力（吨）")
    transport_modes = Column(String(100), nullable=True, comment="运输方式（铁路/汽运/水运）")

    # 评级
    tier = Column(Enum(SupplierTier), default=SupplierTier.PROBATION, comment="供应商等级")
    credit_score = Column(Float, default=80.0, comment="信用评分 0-100")

    # 状态
    status = Column(Enum(SupplierStatus), default=SupplierStatus.PENDING_REVIEW, nullable=False, index=True)
    reviewed_by = Column(String(50), nullable=True, comment="审核人")
    reviewed_at = Column(DateTime, nullable=True, comment="审核时间")
    review_notes = Column(Text, nullable=True, comment="审核意见")

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contracts = relationship("FuelContract", back_populates="supplier", cascade="all, delete-orphan")
