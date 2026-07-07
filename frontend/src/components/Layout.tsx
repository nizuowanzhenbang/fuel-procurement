import { Layout as AntLayout, Menu, Button, Typography, Space } from 'antd'
import {
  DashboardOutlined, TeamOutlined, FileTextOutlined,
  ShoppingCartOutlined, LogoutOutlined, GoldOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore, ROLE_LABEL } from '../stores/auth'

const { Sider, Header, Content } = AntLayout
const { Title, Text } = Typography

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { username, role, logout } = useAuthStore()

  const menuItems = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: '/suppliers', icon: <TeamOutlined />, label: '供应商管理' },
    { key: '/contracts', icon: <FileTextOutlined />, label: '采购合同' },
    { key: '/orders', icon: <ShoppingCartOutlined />, label: '采购订单' },
  ]

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider width={220} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: '20px 16px', borderBottom: '1px solid #f0f0f0' }}>
          <Space>
            <GoldOutlined style={{ fontSize: 22, color: '#722ed1' }} />
            <Title level={5} style={{ margin: 0 }}>燃料采购</Title>
          </Space>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <AntLayout>
        <Header
          style={{
            background: '#fff', padding: '0 24px',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <Text strong style={{ fontSize: 16 }}>发电厂燃料采购管理系统</Text>
          <Space>
            <Text type="secondary">{username} · {role ? ROLE_LABEL[role] || role : ''}</Text>
            <Button type="text" icon={<LogoutOutlined />} onClick={() => { logout(); navigate('/login') }}>
              退出
            </Button>
          </Space>
        </Header>
        <Content style={{ padding: 20, background: '#f5f5f5' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
