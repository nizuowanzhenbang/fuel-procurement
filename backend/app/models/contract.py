"""采购合同模型"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ContractType(str, enum.Enum):
    LONG_TERM = "LONG_TERM"   # 长协合同
    SPOT = "SPOT"             # 现货合同
    FRAMEWORK = "FRAMEWORK"   # 框架协议


class PricingMode(str, enum.Enum):
    DELIVERED = "DELIVERED"     # 到厂价（含运费）
    EX_MINE = "EX_MINE"         # 坑口价
    FOB = "FOB"                 # 车板价
    CIF = "CIF"                 # 到港价


class ContractStatus(str, enum.Enum):
    DRAFT = "DRAFT"             # 草稿
    PENDING_APPROVAL = "PENDING_APPROVAL"   # 待审批
    ACTIVE = "ACTIVE"           # 生效执行中
    COMPLETED = "COMPLETED"     # 已完成（履约完毕）
    EXPIRED = "EXPIRED"         # 已到期未完成
    TERMINATED = "TERMINATED"   # 提前解除


class FuelContract(Base):
    __tablename__ = "fuel_contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_no = Column(String(50), unique=True, index=True, nullable=False, comment="合同编号")
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # 基本信息
    contract_type = Column(Enum(ContractType), default=ContractType.SPOT, comment="合同类型")
    coal_type = Column(String(50), nullable=False, comment="煤种")
    coal_origin = Column(String(100), nullable=True, comment="产地")

    # 数量与价格
    contract_quantity = Column(Float, nullable=False, comment="合同总量（吨）")
    unit_price = Column(Float, nullable=False, comment="合同单价（元/吨）")
    pricing_mode = Column(Enum(PricingMode), default=PricingMode.DELIVERED, comment="计价方式")
    total_amount = Column(Float, nullable=False, comment="合同总金额（万元）")

    # 煤质基准（合同验收依据）
    spec_calorific_value = Column(Float, nullable=True, comment="基准热值 Qnet,ar kcal/kg")
    spec_ash_max = Column(Float, nullable=True, comment="灰分上限 %")
    spec_sulfur_max = Column(Float, nullable=True, comment="硫分上限 %")
    spec_moisture_max = Column(Float, nullable=True, comment="水分上限 %")

    # 履约
    effective_date = Column(DateTime, nullable=False, comment="生效日期")
    expiry_date = Column(DateTime, nullable=False, comment="到期日期")
    delivered_quantity = Column(Float, default=0.0, comment="累计交付量（吨）")

    # 状态
    status = Column(Enum(ContractStatus), default=ContractStatus.DRAFT, nullable=False, index=True)
    approved_by = Column(String(50), nullable=True, comment="审批人")
    approved_at = Column(DateTime, nullable=True, comment="审批时间")

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="contracts")
    orders = relationship("PurchaseOrder", back_populates="contract", cascade="all, delete-orphan")
    approvals = relationship(
        "ContractApproval",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractApproval.level",
    )
    price_history = relationship(
        "ContractPriceHistory",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractPriceHistory.created_at.desc()",
    )
