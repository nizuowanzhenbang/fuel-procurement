"""通用工具"""
from datetime import datetime
from typing import Any


def api_response(data: Any = None, message: str = "ok", code: int = 200) -> dict:
    return {"code": code, "message": message, "data": data}


def paginate_response(items: list, total: int, page: int, page_size: int) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
    }


def generate_supplier_code(seq: int) -> str:
    """供应商编码：GYS-NNNN"""
    return f"GYS-{seq:04d}"


def generate_contract_no(seq: int) -> str:
    """合同编号：HT-YYYYMM-NNNN"""
    return f"HT-{datetime.now().strftime('%Y%m')}-{seq:04d}"


def generate_order_no(seq: int) -> str:
    """订单编号：PO-YYYYMMDD-NNNN"""
    return f"PO-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"
