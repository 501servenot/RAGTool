import type { ThemeConfig } from 'antd'
import { theme } from 'antd'

export const appAntdTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    borderRadius: 12,
    borderRadiusLG: 16,
    colorPrimary: 'var(--accent)',
    colorBgBase: 'var(--background)',
    colorBgContainer: 'rgba(255, 255, 255, 0.025)',
    colorBgElevated: '#111214',
    colorBgLayout: 'var(--background)',
    colorBorder: 'var(--border-subtle)',
    colorSplit: 'var(--border-subtle)',
    colorIcon: 'var(--muted-foreground)',
    colorIconHover: 'var(--foreground-soft)',
    colorText: 'var(--foreground)',
    colorTextPlaceholder: 'var(--muted-foreground)',
    colorTextSecondary: 'var(--muted-foreground)',
    controlHeight: 40,
    controlOutline: 'rgba(113, 112, 255, 0.12)',
    fontFamily: 'var(--font-body)',
  },
}
