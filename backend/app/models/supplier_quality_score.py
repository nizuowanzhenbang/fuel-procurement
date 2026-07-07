"""煤质系统推送的供应商质量评分（webhook 接收）"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.database import Base


class SupplierQualityScore(Base):
    """每次煤质系统打分推送的记录。
    通过 supplier_name 关联（与 coal-quality-monitor 约定）。
    最新一条用于 Dashboard 排名，历史用于趋势分析。
    """
    __tablename__ = "supplier_quality_scores"

    id = Column(Integer, primary_key=True, index=True)
    supplier_name = Column(String(200), nullable=False, index=True, comment="供应商名称")
    score = Column(Float, nullable=False, comment="质量综合评分 0-100")
    sample_count = Column(Integer, default=0, comment="参与评分的化验样本数")
    pass_rate = Column(Float, nullable=True, comment="合格率 %")
    evaluated_at = Column(DateTime, nullable=False, comment="评分时间（煤质系统）")
    notes = Column(Text, nullable=True)

    received_at = Column(DateTime, default=datetime.utcnow, index=True, comment="接收时间")
