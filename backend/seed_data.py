"""演示数据生成器：admin + 供应商 + 合同 + 订单"""
import random
from datetime import datetime, timedelta

from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.supplier import Supplier, SupplierStatus, SupplierTier
from app.models.contract import FuelContract, ContractType, PricingMode, ContractStatus
from app.models.order import PurchaseOrder, OrderStatus
from app.api.deps import hash_password
from app.utils.helpers import (
    generate_supplier_code,
    generate_contract_no,
    generate_order_no,
)


SUPPLIERS = [
    ("神华神东煤炭集团", "动力煤,长焰煤", "陕西神木", 8000000, "战略合作"),
    ("中煤平朔煤业公司", "动力煤,弱粘煤", "山西朔州", 5000000, "战略合作"),
    ("伊泰煤炭股份", "动力煤", "内蒙古鄂尔多斯", 3000000, "优先采购"),
    ("陕煤化运销集团", "动力煤,混煤", "陕西榆林", 4000000, "优先采购"),
    ("兖州煤业", "动力煤,1/3焦煤", "山东济宁", 2000000, "合格供应商"),
    ("同煤集团", "动力煤", "山西大同", 6000000, "战略合作"),
    ("准能集团", "动力煤,褐煤", "内蒙古准格尔", 3500000, "优先采购"),
    ("华能伊敏煤电", "褐煤", "内蒙古呼伦贝尔", 2500000, "合格供应商"),
]

COAL_TYPES = ["动力煤", "长焰煤", "弱粘煤", "1/3焦煤", "褐煤", "混煤"]
PORTS = ["秦皇岛港", "黄骅港", "唐山港", "天津港", "曹妃甸港"]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # admin
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(
                username="admin",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
                is_active=True,
            ))
            db.commit()
            print("✓ admin 已创建")

        # 供应商
        if db.query(Supplier).count() == 0:
            tier_map = {
                "战略合作": SupplierTier.STRATEGIC,
                "优先采购": SupplierTier.PREFERRED,
                "合格供应商": SupplierTier.QUALIFIED,
            }
            for i, (name, types, origin, capacity, tier) in enumerate(SUPPLIERS, 1):
                s = Supplier(
                    code=generate_supplier_code(i),
                    name=name,
                    short_name=name[:4],
                    contact_person=f"联系人{i}",
                    contact_phone=f"139{random.randint(10000000, 99999999)}",
                    address=f"{origin}市经济开发区",
                    business_license=f"9114{random.randint(10000000000, 99999999999)}",
                    registered_capital=random.uniform(5000, 50000),
                    coal_types=types,
                    coal_origin=origin,
                    annual_capacity=capacity,
                    transport_modes="铁路,汽运",
                    tier=tier_map.get(tier, SupplierTier.PROBATION),
                    credit_score=round(random.uniform(75, 98), 1),
                    status=SupplierStatus.ACTIVE,
                    reviewed_by="admin",
                    reviewed_at=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                    review_notes="资质齐全，准入合格",
                )
                db.add(s)
            db.commit()
            print(f"✓ 已生成 {len(SUPPLIERS)} 个供应商")

        # 合同
        suppliers = db.query(Supplier).filter(Supplier.status == SupplierStatus.ACTIVE).all()
        if db.query(FuelContract).count() == 0 and suppliers:
            for i in range(1, 16):
                supplier = random.choice(suppliers)
                coal_type = random.choice(COAL_TYPES)
                qty = random.randint(20000, 200000)
                price = random.randint(500, 900)
                eff = datetime.utcnow() - timedelta(days=random.randint(30, 180))
                exp = eff + timedelta(days=random.randint(180, 730))
                ctype = random.choice([ContractType.LONG_TERM, ContractType.SPOT, ContractType.SPOT])

                c = FuelContract(
                    contract_no=generate_contract_no(i),
                    supplier_id=supplier.id,
                    contract_type=ctype,
                    coal_type=coal_type,
                    coal_origin=supplier.coal_origin,
                    contract_quantity=qty,
                    unit_price=price,
                    pricing_mode=PricingMode.DELIVERED,
                    total_amount=round(qty * price / 10000, 2),
                    spec_calorific_value=random.randint(4800, 5800),
                    spec_ash_max=round(random.uniform(15, 25), 1),
                    spec_sulfur_max=round(random.uniform(0.4, 1.0), 2),
                    spec_moisture_max=round(random.uniform(8, 15), 1),
                    effective_date=eff,
                    expiry_date=exp,
                    status=ContractStatus.ACTIVE,
                    approved_by="admin",
                    approved_at=eff,
                )
                db.add(c)
            db.commit()
            print(f"✓ 已生成 15 个合同")

        # 订单
        contracts = db.query(FuelContract).filter(FuelContract.status == ContractStatus.ACTIVE).all()
        if db.query(PurchaseOrder).count() == 0 and contracts:
            now = datetime.utcnow()
            seq = 1
            for contract in contracts:
                # 每个合同 1-4 个订单
                for _ in range(random.randint(1, 4)):
                    qty = random.randint(2000, 15000)
                    planned_date = contract.effective_date + timedelta(days=random.randint(5, 150))
                    if planned_date > now:
                        planned_date = now - timedelta(days=random.randint(1, 20))

                    roll = random.random()
                    if roll < 0.2:
                        status = OrderStatus.PLANNED
                        delivered_qty = 0
                        delivered_amount = 0
                        actual_date = None
                        settled_at = None
                    elif roll < 0.4:
                        status = OrderStatus.DISPATCHED
                        delivered_qty = 0
                        delivered_amount = 0
                        actual_date = None
                        settled_at = None
                    elif roll < 0.6:
                        status = OrderStatus.PARTIAL_RECEIVED
                        delivered_qty = qty * random.uniform(0.3, 0.7)
                        delivered_amount = round(delivered_qty * contract.unit_price / 10000, 2)
                        actual_date = planned_date + timedelta(days=random.randint(0, 3))
                        settled_at = None
                    elif roll < 0.85:
                        status = OrderStatus.RECEIVED
                        delivered_qty = qty
                        delivered_amount = round(qty * contract.unit_price / 10000, 2)
                        actual_date = planned_date + timedelta(days=random.randint(-2, 5))
                        settled_at = None
                    else:
                        status = OrderStatus.SETTLED
                        delivered_qty = qty
                        delivered_amount = round(qty * contract.unit_price / 10000, 2)
                        actual_date = planned_date + timedelta(days=random.randint(-2, 5))
                        settled_at = actual_date + timedelta(days=random.randint(7, 30))

                    o = PurchaseOrder(
                        order_no=generate_order_no(seq),
                        contract_id=contract.id,
                        planned_quantity=qty,
                        unit_price=contract.unit_price,
                        planned_amount=round(qty * contract.unit_price / 10000, 2),
                        delivered_quantity=round(delivered_qty, 1),
                        delivered_amount=delivered_amount,
                        planned_delivery_date=planned_date,
                        actual_delivery_date=actual_date,
                        transport_mode=random.choice(["铁路", "汽运"]),
                        departure_port=random.choice(PORTS),
                        arrival_plant="本厂",
                        status=status,
                        settled_by="admin" if settled_at else None,
                        settled_at=settled_at,
                    )
                    db.add(o)
                    seq += 1
            db.commit()

            # 更新合同累计交付量
            from sqlalchemy import func
            for contract in contracts:
                delivered = (
                    db.query(func.coalesce(func.sum(PurchaseOrder.delivered_quantity), 0))
                    .filter(PurchaseOrder.contract_id == contract.id)
                    .scalar() or 0
                )
                contract.delivered_quantity = round(float(delivered), 1)
            db.commit()
            print(f"✓ 已生成 {seq - 1} 个订单")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
