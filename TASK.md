# 任务跟踪

## v1.0（已完成）

### 后端
- [x] User / Supplier / FuelContract / PurchaseOrder 四个模型
- [x] 供应商：登记 / 审核 / 暂停 / 恢复 状态流转
- [x] 合同：草稿 / 提交 / 审批 / 解除 状态流转
- [x] 订单：发运 / 到货（支持分批）/ 结算 / 取消
- [x] 订单到货自动累计到合同 `delivered_quantity`，达 99% 自动 `COMPLETED`
- [x] 5 个 Dashboard 接口：总览 + 月度采购量 + 供应商占比 + 单价趋势 + 煤种占比
- [x] seed_data：8 个真实风格供应商 + 15 个合同 + ~40 个订单

### 前端
- [x] 登录页（紫色主题）
- [x] Layout 侧边栏导航
- [x] Dashboard：4 KPI + 月度量金额双轴图 + 供应商饼图 + 单价折线图 + 煤种饼图
- [x] SupplierList：分页 + 筛选 + 登记 + 详情 + 准入审核 + 暂停/恢复
- [x] ContractList：分页 + 筛选 + 创建 + 详情 + 提交审批 + 审批 + 解除 + 执行进度
- [x] OrderList：分页 + 筛选 + 创建（带合同剩余量提示）+ 发运 + 到货 + 结算 + 取消

### 文档
- [x] README.md
- [x] CLAUDE.md
- [x] TASK.md

## v2.0（已完成）

### 与 coal-quality-monitor 集成
- [x] 配置 `QUALITY_SYSTEM_URL`，供应商详情通过 `utils/quality_client` 拉取煤质系统信用分（失败降级 None）
- [x] Webhook `POST /api/webhook/quality-score`（带 `X-Integration-Token` 校验），落库 `supplier_quality_scores`
- [x] Dashboard 新增 `/dashboard/supplier-quality-ranking`（取每家最新评分排序）

### 业务扩展
- [x] 合同多级审批：金额阈值触发不同级别（&lt;100 万 1 级 / 100-500 万 2 级 / &gt;500 万 3 级）
  - 新增 `contract_approvals` 表，`/contracts/{id}/submit` 自动建链
  - `/contracts/{id}/approve` 推进当前级，最后一级通过 → ACTIVE；拒绝 → 退回 DRAFT
  - 前端详情用 Steps 展示审批流
- [x] 长协合同到期前 30 天提醒：`/dashboard/expiring-contracts`，前端 Dashboard 加预警卡片
- [x] 单价历史变更追踪：`contract_price_history` 表
  - 草稿期 `PUT /contracts/{id}` 改价自动写入
  - 生效合同新增 `POST /contracts/{id}/adjust-price`（审批人权限）
  - 详情页展示最近 3 条 + 抽屉查看全部

### 体验
- [x] CSV 导出：供应商 / 合同 / 订单三个列表 `/{...}/export?...` 同 list 筛选参数，UTF-8 BOM 防乱码
- [x] 角色权限拦截：ADMIN / PROCUREMENT / APPROVER / VIEWER
  - `deps.require_write`：管理员或采购员（创建/修改/到货/取消）
  - `deps.require_approver`：管理员或审批人（审批/调价/结算/暂停恢复/供应商审核）
  - seed 增加 buyer/approver/viewer 三个账户
  - 前端通过 `canWrite`/`canApprove` 禁用按钮 + tooltip 提示
- [x] 订单详情显示煤质化验结果：`/orders/{id}` 聚合调用煤质系统 `/api/integration/order-quality`

## v2.1（已完成，2026-05-20）

### 与 coal-yard-management 上游集成
- [x] 新增 `app/api/integration.py`（统一鉴权 header `X-Integration-Token` + `settings.INTEGRATION_SECRET`）
- [x] `GET /api/integration/order-info?order_no=` 返回订单履约信息（含合同、供应商、煤种、煤质基准）
- [x] `POST /api/integration/yard-stocked` 接收煤场入场通知，自动累计 `delivered_quantity` + 推进订单/合同状态机
- [x] `config.py` 新增 `INTEGRATION_SECRET`（默认与煤场/煤质共享 `coal-integration-shared-secret`）

## v3.0（规划）

- [ ] 招标比价模块（多供应商对同一需求报价）
- [ ] 发票管理 + 应付账款
- [ ] 移动端：现场到货扫码登记
- [ ] AI 辅助：根据历史价格预测下月最优采购量
- [ ] 与 ERP / 财务系统对接
- [ ] WebSocket 实时通知（合同审批/到货/到期）
- [ ] 黑名单状态机（SupplierStatus.BLACKLISTED 操作 API）

## 已知简化（v2 仍存在）

- 合同审批人字段为字符串，未关联 users 表（多级审批的 approver 同样如此）
- 订单结算金额支持手动覆盖，未做差异审计
- 没有 WebSocket（采购场景实时性要求不高）
- `coal-quality-monitor` 的对端 `/api/integration/supplier-credit` 和 `/order-quality` 接口约定，需对方在 v2 配套实现
