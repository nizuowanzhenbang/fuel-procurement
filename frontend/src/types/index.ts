export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type SupplierStatus =
  | 'PENDING_REVIEW' | 'ACTIVE' | 'SUSPENDED' | 'BLACKLISTED' | 'ARCHIVED'
export type SupplierTier =
  | 'STRATEGIC' | 'PREFERRED' | 'QUALIFIED' | 'PROBATION'

export interface Supplier {
  id: number
  code: string
  name: string
  short_name: string | null
  legal_representative: string | null
  contact_person: string | null
  contact_phone: string | null
  address: string | null
  business_license: string | null
  registered_capital: number | null
  coal_types: string | null
  coal_origin: string | null
  annual_capacity: number | null
  transport_modes: string | null
  tier: SupplierTier
  credit_score: number
  status: SupplierStatus
  reviewed_by: string | null
  reviewed_at: string | null
  review_notes: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export type ContractType = 'LONG_TERM' | 'SPOT' | 'FRAMEWORK'
export type PricingMode = 'DELIVERED' | 'EX_MINE' | 'FOB' | 'CIF'
export type ContractStatus =
  | 'DRAFT' | 'PENDING_APPROVAL' | 'ACTIVE'
  | 'COMPLETED' | 'EXPIRED' | 'TERMINATED'

export interface Contract {
  id: number
  contract_no: string
  supplier_id: number
  supplier_name: string | null
  contract_type: ContractType
  coal_type: string
  coal_origin: string | null
  contract_quantity: number
  unit_price: number
  pricing_mode: PricingMode
  total_amount: number
  spec_calorific_value: number | null
  spec_ash_max: number | null
  spec_sulfur_max: number | null
  spec_moisture_max: number | null
  effective_date: string
  expiry_date: string
  delivered_quantity: number
  status: ContractStatus
  approved_by: string | null
  approved_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export type OrderStatus =
  | 'PLANNED' | 'DISPATCHED' | 'PARTIAL_RECEIVED'
  | 'RECEIVED' | 'SETTLED' | 'CANCELLED'

export interface Order {
  id: number
  order_no: string
  contract_id: number
  contract_no: string | null
  supplier_name: string | null
  coal_type: string | null
  planned_quantity: number
  unit_price: number
  planned_amount: number
  delivered_quantity: number
  delivered_amount: number
  planned_delivery_date: string
  actual_delivery_date: string | null
  transport_mode: string | null
  departure_port: string | null
  arrival_plant: string | null
  status: OrderStatus
  settled_by: string | null
  settled_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface OverviewData {
  active_suppliers: number
  pending_review: number
  active_contracts: number
  pending_approval: number
  month_delivered_tons: number
  month_settled_amount: number
  in_transit_orders: number
  avg_unit_price: number | null
}

export interface MonthlyQuantityItem {
  month: string
  quantity: number
  amount: number
}

export interface SupplierShareItem {
  supplier_name: string
  quantity: number
}

export interface PriceTrendItem {
  date: string
  avg_price: number
}

export interface CoalTypeShareItem {
  coal_type: string
  quantity: number
}

// === v2 集成 / 多级审批 / 价格历史 / 质量评分 ===

export type UserRole = 'ADMIN' | 'PROCUREMENT' | 'APPROVER' | 'VIEWER'

export interface QualityScore {
  score: number
  sample_count: number | null
  pass_rate: number | null
  evaluated_at: string
  source: 'synced' | 'live'
}

export interface SupplierDetail extends Supplier {
  quality_score: QualityScore | null
}

export type ApprovalLevelStatus = 'PENDING' | 'APPROVED' | 'REJECTED'

export interface ApprovalLevel {
  id: number
  level: number
  level_name: string
  status: ApprovalLevelStatus
  approver: string | null
  approved_at: string | null
  notes: string | null
  created_at: string
}

export interface PriceHistoryItem {
  id: number
  old_price: number
  new_price: number
  changed_by: string
  reason: string | null
  created_at: string
}

export interface ContractDetail extends Contract {
  approvals: ApprovalLevel[]
  price_history: PriceHistoryItem[]
}

export interface QualityResult {
  sample_no?: string
  sampled_at?: string
  calorific_value?: number | null
  ash?: number | null
  sulfur?: number | null
  moisture?: number | null
  conclusion?: string | null
  [key: string]: unknown
}

export interface OrderDetail extends Order {
  quality_results: QualityResult[] | null
}

export interface SupplierQualityRank {
  rank: number
  supplier_name: string
  score: number
  sample_count: number | null
  pass_rate: number | null
  evaluated_at: string
  tier: string | null
  credit_score: number | null
}

export interface ExpiringContract {
  id: number
  contract_no: string
  supplier_name: string | null
  coal_type: string
  expiry_date: string
  days_left: number
  contract_quantity: number
  delivered_quantity: number
  remaining_quantity: number
  completion_rate: number
  unit_price: number
}
