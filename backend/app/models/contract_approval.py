"""合同多级审批记录"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ApprovalLevelStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ContractApproval(Base):
    """合同多级审批流水。
    金额阈值规则（万元）：
      <100  → 1 级（采购主管）
      100-500 → 2 级（采购主管 → 燃料部主任）
      >500  → 3 级（采购主管 → 燃料部主任 → 总经理）
    """
    __tablename__ = "contract_approvals"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("fuel_contracts.id"), nullable=False, index=True)
    level = Column(Integer, nullable=False, comment="审批级别 1/2/3")
    level_name = Column(String(50), nullable=False, comment="级别名称")

    status = Column(Enum(ApprovalLevelStatus), default=ApprovalLevelStatus.PENDING, nullable=False)
    approver = Column(String(50), nullable=True, comment="审批人")
    approved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("FuelContract", back_populates="approvals")
