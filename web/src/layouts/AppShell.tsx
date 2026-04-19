import type { MouseEvent } from 'react'
import { BarChart3, Database, FileUp, MessageSquare, Settings, Sparkles } from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import type { NavLinkRenderProps } from 'react-router-dom'

import { useConfigNavigationGuard } from '../contexts/ConfigNavigationGuard'
import { cn } from '../lib/utils'

const navItems = [
  {
    to: '/chat',
    label: 'PlayGround',
    icon: MessageSquare,
  },
  {
    to: '/upload',
    label: 'Upload',
    icon: FileUp,
  },
  {
    to: '/knowledge',
    label: 'KnowledgeBase',
    icon: Database,
  },
  {
    to: '/evaluate',
    label: 'Evaluate',
    icon: BarChart3,
  },
  {
    to: '/config',
    label: 'Settings',
    icon: Settings,
  },
]

export default function AppShell() {
  const location = useLocation()
  const { isConfigDirty, showUnsavedWarning } = useConfigNavigationGuard()

  const handleNavClick = (event: MouseEvent<HTMLAnchorElement>, nextPath: string) => {
    const isLeavingConfig = location.pathname === '/config' && nextPath !== '/config'
    if (!isLeavingConfig || !isConfigDirty) return

    event.preventDefault()
    showUnsavedWarning()
  }

  return (
    <div className="grid h-[100svh] overflow-hidden bg-transparent [grid-template-columns:264px_minmax(0,1fr)] max-[960px]:grid-cols-1">
      <aside className="flex flex-col gap-6 overflow-auto bg-[linear-gradient(180deg,rgba(17,18,20,0.98),rgba(11,12,14,0.96))] px-3 pt-4 pb-4 backdrop-blur-[14px] max-[960px]:gap-3 max-[640px]:px-[14px] max-[640px]:pt-[16px] max-[640px]:pb-[12px]">
        <div className="mx-auto flex w-full max-w-[214px] min-w-0 items-center gap-2.5 px-1 pt-4 pb-1.5">
          <span
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-[linear-gradient(135deg,rgba(113,112,255,0.32),rgba(94,106,210,0.18))] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]"
            aria-hidden="true"
          >
            <Sparkles size={16} strokeWidth={2.2} />
          </span>
          <span className="min-w-0 truncate text-[20px] leading-none font-[560] tracking-[-0.01em] text-[color:var(--foreground)]">
            RAGTool
          </span>
        </div>

        <div className="flex min-w-0 flex-col gap-2">
          <nav className="mt-0.5 flex flex-col gap-2 max-[960px]:overflow-auto max-[960px]:pb-1">
            {navItems.map((item) => (
              <SidebarNavItem key={item.to} item={item} onClick={handleNavClick} />
            ))}
          </nav>
        </div>

        <div className="mt-auto overflow-hidden px-2.5 pt-2.5">
          <span className="block text-[11px] leading-[1.45] text-[color:var(--subtle-foreground)]">
            支持问答、上传、检索与配置管理
          </span>
        </div>
      </aside>

      <div className="app-content">
        <Outlet />
      </div>
    </div>
  )
}

interface SidebarNavItemProps {
  item: {
    to: string
    label: string
    icon: LucideIcon
  }
  onClick: (event: MouseEvent<HTMLAnchorElement>, nextPath: string) => void
}

function SidebarNavItem({ item, onClick }: SidebarNavItemProps) {
  const Icon = item.icon

  return (
    <NavLink
      to={item.to}
      onClick={(event) => onClick(event, item.to)}
      aria-label={item.label}
      className={({ isActive }: NavLinkRenderProps) =>
        cn(
          'mx-auto flex min-h-[54px] w-full max-w-[214px] min-w-0 items-center justify-start gap-2.5 overflow-hidden rounded-[20px] bg-[rgba(255,255,255,0.025)] px-4 py-3 text-[color:var(--foreground-soft)] transition-[background-color,color,transform,box-shadow] duration-200 hover:-translate-y-px hover:bg-[rgba(255,255,255,0.045)] hover:text-[color:var(--foreground)] max-[960px]:min-w-[180px] max-[640px]:min-w-[148px]',
          isActive &&
            'bg-[linear-gradient(180deg,rgba(255,255,255,0.07),rgba(255,255,255,0.035))] text-[color:var(--foreground)] shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]',
        )
      }
    >
      <span
        className="inline-flex shrink-0 items-center justify-center text-current"
        aria-hidden="true"
      >
        <Icon size={18} strokeWidth={2.1} />
      </span>
      <span className="min-w-0 flex-1 overflow-hidden">
        <span className="block truncate text-[15px] leading-5 font-[510]">{item.label}</span>
      </span>
    </NavLink>
  )
}
