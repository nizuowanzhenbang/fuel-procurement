"""集成 webhook 接收端"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.models.supplier_quality_score import SupplierQualityScore
from app.schemas.webhook import QualityScorePayload
from app.utils.helpers import api_response

router = APIRouter(prefix="/api/webhook", tags=["集成 webhook"])


def _verify_token(x_integration_token: str = Header(None, alias="X-Integration-Token")):
    if x_integration_token != settings.QUALITY_INTEGRATION_SECRET:
        raise HTTPException(401, "集成 token 校验失败")


@router.post("/quality-score", dependencies=[Depends(_verify_token)])
def receive_quality_score(payload: QualityScorePayload, db: Session = Depends(get_db)):
    """煤质系统推送的供应商质量评分，按供应商名称落库（追加历史）"""
    record = SupplierQualityScore(
        supplier_name=payload.supplier_name,
        score=payload.score,
        sample_count=payload.sample_count or 0,
        pass_rate=payload.pass_rate,
        evaluated_at=payload.evaluated_at,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return api_response(
        message="质量评分已接收",
        data={"id": record.id, "supplier_name": record.supplier_name, "score": record.score},
    )
