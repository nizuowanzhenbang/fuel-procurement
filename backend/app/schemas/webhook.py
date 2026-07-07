"""集成 webhook schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class QualityScorePayload(BaseModel):
    """煤质系统推送的供应商质量评分"""
    supplier_name: str
    score: float
    sample_count: Optional[int] = 0
    pass_rate: Optional[float] = None
    evaluated_at: datetime
    notes: Optional[str] = None
