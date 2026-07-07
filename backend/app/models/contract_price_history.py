"""合同单价变更历史"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ContractPriceHistory(Base):
    __tablename__ = "contract_price_history"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("fuel_contracts.id"), nullable=False, index=True)

    old_price = Column(Float, nullable=False, comment="原单价 元/吨")
    new_price = Column(Float, nullable=False, comment="新单价 元/吨")
    changed_by = Column(String(50), nullable=False, comment="变更人")
    reason = Column(Text, nullable=True, comment="变更原因")

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    contract = relationship("FuelContract", back_populates="price_history")
