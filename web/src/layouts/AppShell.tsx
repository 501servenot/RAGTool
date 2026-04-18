import { NavLink, Outlet } from 'react-router-dom'
import type { NavLinkRenderProps } from 'react-router-dom'

const navItems = [
  { to: '/chat', label: '对话', description: '检索问答与会话管理' },
  { to: '/upload', label: '文档上传', description: '将资料写入知识库索引' },
  { to: '/knowledge', label: '知识库', description: '查看文档、切片与状态' },
]

export default function AppShell() {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-sidebar__header">
          <span className="app-sidebar__eyebrow">RAG Console</span>
          <div className="app-sidebar__brand">
            <span className="app-sidebar__brand-mark" aria-hidden="true" />
            <div>
              <h1>Neural Ops</h1>
              <p>知识库、检索与连续对话工作台</p>
            </div>
          </div>
        </div>

        <nav className="app-sidebar__nav" aria-label="主导航">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }: NavLinkRenderProps) =>
                isActive ? 'app-nav-link app-nav-link--active' : 'app-nav-link'
              }
            >
              <span className="app-nav-link__label">{item.label}</span>
              <span className="app-nav-link__description">{item.description}</span>
            </NavLink>
          ))}
        </nav>

        <div className="app-sidebar__footer">
          <span className="app-sidebar__footer-label">暗色原生工作台</span>
          <span className="app-sidebar__footer-meta">Linear 风格的精密界面语言</span>
        </div>
      </aside>

      <div className="app-content">
        <Outlet />
      </div>
    </div>
  )
}
