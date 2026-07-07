import { create } from 'zustand'

export type Role = 'ADMIN' | 'PROCUREMENT' | 'APPROVER' | 'VIEWER'

interface AuthState {
  token: string | null
  username: string | null
  role: string | null
  setAuth: (token: string, username: string, role: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  username: localStorage.getItem('username'),
  role: localStorage.getItem('role'),
  setAuth: (token, username, role) => {
    localStorage.setItem('token', token)
    localStorage.setItem('username', username)
    localStorage.setItem('role', role)
    set({ token, username, role })
  },
  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
    set({ token: null, username: null, role: null })
  },
}))

/** 写操作（创建/修改/发起流程）：ADMIN、采购员 */
export const canWrite = (role: string | null) =>
  role === 'ADMIN' || role === 'PROCUREMENT'

/** 审批操作（合同审批、供应商审核、结算、调价、暂停/恢复）：ADMIN、审批人 */
export const canApprove = (role: string | null) =>
  role === 'ADMIN' || role === 'APPROVER'

export const ROLE_LABEL: Record<string, string> = {
  ADMIN: '管理员',
  PROCUREMENT: '采购员',
  APPROVER: '审批人',
  VIEWER: '查看者',
}
