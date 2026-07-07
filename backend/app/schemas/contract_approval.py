"""合同审批 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.contract_approval import ApprovalLevelStatus


class ApprovalLevelResponse(BaseModel):
    id: int
    level: int
    level_name: str
    status: ApprovalLevelStatus
    approver: Optional[str]
    approved_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ApprovalLevelAction(BaseModel):
    """单级审批"""
    approved: bool
    notes: Optional[str] = None


class PriceHistoryResponse(BaseModel):
    id: int
    old_price: float
    new_price: float
    changed_by: str
    reason: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PriceUpdatePayload(BaseModel):
    """单价调整（生效后合同的价格调整需要审计）"""
    new_price: float
    reason: Optional[str] = None
