"""采购订单模型"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class OrderStatus(str, enum.Enum):
    PLANNED = "PLANNED"         # 计划中
    DISPATCHED = "DISPATCHED"   # 已发运
    PARTIAL_RECEIVED = "PARTIAL_RECEIVED"  # 部分到货
    RECEIVED = "RECEIVED"       # 已到货
    SETTLED = "SETTLED"         # 已结算
    CANCELLED = "CANCELLED"     # 已取消


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), unique=True, index=True, nullable=False, comment="订单编号")
    contract_id = Column(Integer, ForeignKey("fuel_contracts.id"), nullable=False, index=True)

    # 订单量
    planned_quantity = Column(Float, nullable=False, comment="计划数量（吨）")
    unit_price = Column(Float, nullable=False, comment="本次单价（元/吨）")
    planned_amount = Column(Float, nullable=False, comment="计划金额（万元）")

    # 履约
    delivered_quantity = Column(Float, default=0.0, comment="实际到货量（吨）")
    delivered_amount = Column(Float, default=0.0, comment="实际结算金额（万元）")

    # 时间
    planned_delivery_date = Column(DateTime, nullable=False, comment="计划到货日期")
    actual_delivery_date = Column(DateTime, nullable=True, comment="实际到货日期")

    # 运输
    transport_mode = Column(String(50), nullable=True, comment="运输方式")
    departure_port = Column(String(100), nullable=True, comment="发货港/矿")
    arrival_plant = Column(String(100), nullable=True, comment="到厂")

    # 状态
    status = Column(Enum(OrderStatus), default=OrderStatus.PLANNED, nullable=False, index=True)
    settled_by = Column(String(50), nullable=True, comment="结算人")
    settled_at = Column(DateTime, nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract = relationship("FuelContract", back_populates="orders")
