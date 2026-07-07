import axios from 'axios'
import type {
  ApiResponse, PaginatedResponse, Supplier, Contract, Order,
  OverviewData, MonthlyQuantityItem, SupplierShareItem,
  PriceTrendItem, CoalTypeShareItem,
  SupplierStatus, SupplierTier, ContractStatus, OrderStatus,
  SupplierDetail, ContractDetail, OrderDetail,
  PriceHistoryItem, ApprovalLevel,
  SupplierQualityRank, ExpiringContract,
} from '../types'

const api = axios.create({ baseURL: '/api', timeout: 15000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err.response?.data || err)
  },
)

function buildDownloadUrl(path: string, params?: Record<string, string | number | undefined>) {
  const qs = new URLSearchParams()
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v != null && v !== '') qs.append(k, String(v))
    }
  }
  return `/api${path}${qs.toString() ? `?${qs.toString()}` : ''}`
}

async function downloadFile(url: string, fallbackName = 'export.csv') {
  const token = localStorage.getItem('token')
  const resp = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!resp.ok) throw new Error(`下载失败 ${resp.status}`)
  const blob = await resp.blob()
  const cd = resp.headers.get('Content-Disposition') || ''
  let filename = fallbackName
  const m = cd.match(/filename\*?=(?:UTF-8'')?([^;]+)/i)
  if (m) {
    try { filename = decodeURIComponent(m[1].replace(/"/g, '')) } catch { /* ignore */ }
  }
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}

export const authApi = {
  login: (username: string, password: string) => {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    return api.post<unknown, { access_token: string; token_type: string }>('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  me: () => api.get<unknown, ApiResponse<{ id: number; username: string; role: string }>>('/auth/me'),
}

export const supplierApi = {
  list: (params?: { page?: number; page_size?: number; status?: SupplierStatus; tier?: SupplierTier; keyword?: string }) =>
    api.get<unknown, ApiResponse<PaginatedResponse<Supplier>>>('/suppliers', { params }),
  create: (data: Partial<Supplier>) =>
    api.post<unknown, ApiResponse<Supplier>>('/suppliers', data),
  get: (id: number) =>
    api.get<unknown, ApiResponse<SupplierDetail>>(`/suppliers/${id}`),
  update: (id: number, data: Partial<Supplier>) =>
    api.put<unknown, ApiResponse<Supplier>>(`/suppliers/${id}`, data),
  review: (id: number, approved: boolean, review_notes: string, tier?: SupplierTier) =>
    api.post<unknown, ApiResponse<Supplier>>(`/suppliers/${id}/review`, { approved, review_notes, tier }),
  suspend: (id: number) => api.post<unknown, ApiResponse<null>>(`/suppliers/${id}/suspend`),
  resume: (id: number) => api.post<unknown, ApiResponse<null>>(`/suppliers/${id}/resume`),
  exportCsv: (params?: { status?: SupplierStatus; tier?: SupplierTier; keyword?: string }) =>
    downloadFile(buildDownloadUrl('/suppliers/export', params), '供应商列表.csv'),
}

export const contractApi = {
  list: (params?: { page?: number; page_size?: number; status?: ContractStatus; supplier_id?: number; keyword?: string }) =>
    api.get<unknown, ApiResponse<PaginatedResponse<Contract>>>('/contracts', { params }),
  create: (data: Partial<Contract>) =>
    api.post<unknown, ApiResponse<Contract>>('/contracts', data),
  get: (id: number) =>
    api.get<unknown, ApiResponse<ContractDetail>>(`/contracts/${id}`),
  update: (id: number, data: Partial<Contract>) =>
    api.put<unknown, ApiResponse<Contract>>(`/contracts/${id}`, data),
  submit: (id: number) => api.post<unknown, ApiResponse<null>>(`/contracts/${id}/submit`),
  approve: (id: number, approver: string, approved: boolean, notes?: string) =>
    api.post<unknown, ApiResponse<Contract>>(`/contracts/${id}/approve`, { approver, approved, notes }),
  terminate: (id: number) => api.post<unknown, ApiResponse<null>>(`/contracts/${id}/terminate`),
  adjustPrice: (id: number, new_price: number, reason?: string) =>
    api.post<unknown, ApiResponse<Contract>>(`/contracts/${id}/adjust-price`, { new_price, reason }),
  priceHistory: (id: number) =>
    api.get<unknown, ApiResponse<PriceHistoryItem[]>>(`/contracts/${id}/price-history`),
  approvals: (id: number) =>
    api.get<unknown, ApiResponse<ApprovalLevel[]>>(`/contracts/${id}/approvals`),
  exportCsv: (params?: { status?: ContractStatus; supplier_id?: number; keyword?: string }) =>
    downloadFile(buildDownloadUrl('/contracts/export', params), '合同列表.csv'),
}

export const orderApi = {
  list: (params?: { page?: number; page_size?: number; status?: OrderStatus; contract_id?: number }) =>
    api.get<unknown, ApiResponse<PaginatedResponse<Order>>>('/orders', { params }),
  create: (data: Partial<Order>) =>
    api.post<unknown, ApiResponse<Order>>('/orders', data),
  get: (id: number) =>
    api.get<unknown, ApiResponse<OrderDetail>>(`/orders/${id}`),
  update: (id: number, data: Partial<Order>) =>
    api.put<unknown, ApiResponse<Order>>(`/orders/${id}`, data),
  dispatch: (id: number) => api.post<unknown, ApiResponse<null>>(`/orders/${id}/dispatch`),
  receive: (id: number, delivered_quantity: number, actual_delivery_date?: string) =>
    api.post<unknown, ApiResponse<Order>>(`/orders/${id}/receive`, { delivered_quantity, actual_delivery_date }),
  settle: (id: number, settled_by: string, delivered_amount?: number) =>
    api.post<unknown, ApiResponse<Order>>(`/orders/${id}/settle`, { settled_by, delivered_amount }),
  cancel: (id: number) => api.post<unknown, ApiResponse<null>>(`/orders/${id}/cancel`),
  exportCsv: (params?: { status?: OrderStatus; contract_id?: number }) =>
    downloadFile(buildDownloadUrl('/orders/export', params), '订单列表.csv'),
}

export const dashboardApi = {
  overview: () => api.get<unknown, ApiResponse<OverviewData>>('/dashboard/overview'),
  monthlyQuantity: (months?: number) =>
    api.get<unknown, ApiResponse<MonthlyQuantityItem[]>>('/dashboard/monthly-quantity', { params: { months } }),
  supplierShare: () =>
    api.get<unknown, ApiResponse<SupplierShareItem[]>>('/dashboard/supplier-share'),
  priceTrend: (days?: number) =>
    api.get<unknown, ApiResponse<PriceTrendItem[]>>('/dashboard/price-trend', { params: { days } }),
  coalTypeShare: () =>
    api.get<unknown, ApiResponse<CoalTypeShareItem[]>>('/dashboard/coal-type-share'),
  supplierQualityRanking: (limit = 10) =>
    api.get<unknown, ApiResponse<SupplierQualityRank[]>>('/dashboard/supplier-quality-ranking', { params: { limit } }),
  expiringContracts: (days = 30) =>
    api.get<unknown, ApiResponse<ExpiringContract[]>>('/dashboard/expiring-contracts', { params: { days } }),
}

export default api
