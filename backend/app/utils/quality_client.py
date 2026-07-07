"""煤质化验系统（coal-quality-monitor）HTTP 客户端。
失败时降级返回 None，不阻塞主流程。
"""
from typing import Optional, List
import httpx

from app.config import settings


def _base_url() -> Optional[str]:
    url = (settings.QUALITY_SYSTEM_URL or "").strip()
    return url.rstrip("/") if url else None


def _headers() -> dict:
    return {"X-Integration-Token": settings.QUALITY_INTEGRATION_SECRET}


def fetch_supplier_credit(supplier_name: str) -> Optional[dict]:
    """查询煤质系统中该供应商的信用评分摘要。
    返回 {score, sample_count, pass_rate, evaluated_at} 或 None。
    """
    base = _base_url()
    if not base:
        return None
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"{base}/api/integration/supplier-credit",
                params={"supplier_name": supplier_name},
                headers=_headers(),
            )
            if resp.status_code != 200:
                return None
            payload = resp.json()
            return payload.get("data") if isinstance(payload, dict) else None
    except Exception:
        return None


def fetch_order_quality_results(order_no: str) -> Optional[List[dict]]:
    """按订单号查询煤质化验结果列表。"""
    base = _base_url()
    if not base:
        return None
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"{base}/api/integration/order-quality",
                params={"order_no": order_no},
                headers=_headers(),
            )
            if resp.status_code != 200:
                return None
            payload = resp.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            return data if isinstance(data, list) else None
    except Exception:
        return None
