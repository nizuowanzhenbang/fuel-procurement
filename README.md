# 燃料采购的"账房先生" · 发电厂燃料采购管理系统

> 💰 燃料是火电厂最大的运营成本，但采购环节常年乱：供应商档案散在 Excel、合同审批靠群里 @ 领导、订单到货量谁都说不清楚、煤质不达标的供应商下次还能继续中标。一年算下来，多花的钱都够给职工发年终奖。

**这套系统把"供应商准入 → 合同签订 → 订单履约"绑成一条三层闭环**：供应商要先审核才能进白名单；合同按金额走 1/2/3 级审批，单价变更全程留痕；订单到货量自动汇总到合同，达 99% 自动转 COMPLETED。还跟[煤质化验系统](https://github.com/nizuowanzhenbang/coal-quality-monitor)双向联动——供应商的实时煤质信用分直接显示在采购页面上，质量不达标的供应商下次询价排序自动靠后。

> ⚠️ **免责声明**：本系统是 **厂内业务管理工具**，不能替代 ERP / 财务系统的法定单据，也不能替代国资 / 央企采购平台的合规公示流程。

---

## ⚡ 30 秒看明白你能用它做什么

| 你是谁 | 它帮你做什么 |
|---|---|
| 🤝 采购员 | 登记供应商、起草合同、下订单、登记到货，全程不用 Excel |
| ✅ 审批领导 | 按金额自动分配到对应级别审批；移动端也能审；调价留痕可追溯 |
| 📦 仓库验收 | 分批到货登记，自动汇总到合同累计履约量 |
| 💼 燃料部主任 | 大屏一眼看完供应商质量排名、合同执行进度、月度采购金额 |
| 👀 审计 | 谁批的、什么时候批的、调过几次价、原因是什么，全在审计历史里 |

---

## ✨ 核心场景

### 🏢 供应商三段式准入
```
PENDING_REVIEW（新登记）→ ACTIVE（已准入）⇄ SUSPENDED（暂停）→ BLACKLISTED / ARCHIVED
```
- 只有 `ACTIVE` 状态的供应商可签新合同
- 供应商档案沉淀：煤种、产地、计价方式、运输能力、信用评级
- **质量信用分**直接从煤质化验系统拉，不达标的下次询价排序靠后

### 📄 合同三层闭环 + 金额分级审批

| 合同金额 | 审批级别 |
|---|---|
| < 100 万 | 1 级（部门审批） |
| 100–500 万 | 2 级（分管副总） |
| > 500 万 | 3 级（总经理 / 总师） |

- 状态机：`DRAFT → PENDING_APPROVAL → ACTIVE → COMPLETED / TERMINATED`
- 合同里写明 **煤质基准**（热值 / 灰分 / 硫分 / 水分上限），与化验系统同口径
- **单价变更全留痕**：`/adjust-price` 接口写审计历史（谁调的、为什么、生效时间）
- 长协合同 **到期前 30 天自动提醒**

### 📦 订单履约链：从计划到结算
```
PLANNED → DISPATCHED（发运）→ PARTIAL_RECEIVED（分批到货）→ RECEIVED（满载到货）→ SETTLED（结算）
```
- 到货量 ≥ 计划 99% 自动转 `RECEIVED`
- **订单详情自动拉化验结果**——这单煤热值多少、硫分超没超合同基准，一目了然
- 累计履约量自动汇总到合同；合同达 99% 自动 `COMPLETED`

### 🔗 与煤质化验系统双向联动
> 💡 **怎么打通的？**
> - 采购系统的供应商详情 → 实时调煤质系统 `/api/integration/supplier-credit` 拉信用分
> - 煤质系统化验结果出炉 → webhook 推送到采购系统 `/api/webhook/quality-score`，落库后影响 Dashboard 排名
> - 共享密钥 `QUALITY_INTEGRATION_SECRET`，按"供应商名称"做主键关联
> - 合同里的 `spec_calorific_value / ash_max / sulfur_max / moisture_max` 与化验系统字段名一致

### 📊 五个看板视角
- 月度采购金额趋势 / 煤种构成 / 供应商集中度
- 合同执行进度 TOP / 即将到期合同
- **供应商质量综合评分排名**（来自化验系统 webhook）
- 待审批合同 / 待结算订单 KPI

---

## 🚀 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
python seed_data.py                  # 演示数据：8 供应商 + 15 合同 + ~40 订单
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

打开 http://localhost:5173 → 用 `admin / admin123` 登录。

## 🔐 默认账户

| 用户名 | 密码 | 角色 | 主要权限 |
|---|---|---|---|
| `admin` | `admin123` | 管理员 | 全部 |
| `buyer` | `buyer123` | 采购员 | 登记供应商、起草合同、下订单、登记到货 |
| `approver` | `approver123` | 审批人 | 合同审批、调价、结算、供应商暂停/恢复 |
| `viewer` | `viewer123` | 只读 | 仅查看 |

> 🔒 生产部署请务必删掉 seed 用户、改强密码。

---

## 📋 业务规则速查

| 项 | 规则 |
|---|---|
| 供应商签合同 | 必须 `ACTIVE` 状态 |
| 合同金额分级 | < 100 万 / 100–500 万 / > 500 万 → 1/2/3 级审批 |
| 合同自动完成 | 累计交付 ≥ 99% |
| 订单完整到货 | 累计到货量 ≥ 计划 99% |
| 编号规则 | 供应商 `GYS-NNNN` / 合同 `HT-YYYYMM-NNNN` / 订单 `PO-YYYYMMDD-NNNN` |

---

## 🛠️ 技术栈

| 层 | 选型 |
|---|---|
| 后端 | FastAPI · SQLAlchemy · Pydantic v2 · JWT |
| 前端 | React 18 · TypeScript · Ant Design 5 · ECharts · Zustand · Vite |
| 数据 | SQLite（开发）/ PostgreSQL（生产） |
| 端口 | 后端 `8000` / 前端 `5173` |

## 📁 目录结构

```
fuel-procurement/
├── backend/
│   ├── app/
│   │   ├── api/          # auth / suppliers / contracts / orders / dashboard / integration / webhook
│   │   ├── models/       # User / Supplier / FuelContract / PurchaseOrder
│   │   ├── schemas/
│   │   ├── utils/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   └── seed_data.py
└── frontend/
    └── src/
        ├── pages/        # Dashboard / SupplierList / ContractList / OrderList / LoginPage
        ├── components/   # Layout
        ├── api/
        ├── stores/
        └── types/
```

---

## 🔗 智慧发电厂全家桶中的位置

本项目是 [smart-power-plant](https://github.com/nizuowanzhenbang/smart-power-plant) 七大子系统中的"燃料采购"模块，已联动：

| 系统 | 关系 |
|---|---|
| [coal-quality-monitor](https://github.com/nizuowanzhenbang/coal-quality-monitor) | 双向：供应商信用分实时查询 + webhook 推送 + 订单详情拉化验结果 |
| [equipment-inspection](https://github.com/nizuowanzhenbang/equipment-inspection) | 接收备件采购申请（v3 起） |
| [coal-yard-management](https://github.com/nizuowanzhenbang/coal-yard-management) | 订单 `RECEIVED` 触发入煤场（v3 规划） |

---

## 🚧 路线图

- ✅ **v1.0**：供应商 + 合同 + 订单 + Dashboard
- ✅ **v2.0**：与煤质系统双向集成 + 多级审批 + 调价留痕 + 角色权限 + CSV 导出
- 🚧 **v3.0**：招标比价（多供应商报价对比）+ 与煤场联动入库
- 📋 **v4.0**：发票管理 + 应付账款 + 与财务系统对接

## 📜 License

私有项目，未开源。


## 持续维护

[开发与验收说明](docs/MAINTENANCE.md)：自动检查、回归测试与演示边界。
