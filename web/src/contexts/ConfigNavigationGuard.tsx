import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react'
import type { ReactNode } from 'react'

interface ConfigNavigationGuardContextValue {
  isConfigDirty: boolean
  unsavedWarning: string | null
  setConfigDirty: (dirty: boolean) => void
  showUnsavedWarning: (message?: string) => void
  clearUnsavedWarning: () => void
}

const ConfigNavigationGuardContext =
  createContext<ConfigNavigationGuardContextValue | null>(null)

export function ConfigNavigationGuardProvider({
  children,
}: {
  children: ReactNode
}) {
  const [isConfigDirty, setIsConfigDirty] = useState(false)
  const [unsavedWarning, setUnsavedWarning] = useState<string | null>(null)

  const setConfigDirty = useCallback((dirty: boolean) => {
    setIsConfigDirty(dirty)
    if (!dirty) {
      setUnsavedWarning(null)
    }
  }, [])

  const showUnsavedWarning = useCallback((message = '有策略未保存，请保存后再试') => {
    setUnsavedWarning(message)
  }, [])

  const clearUnsavedWarning = useCallback(() => {
    setUnsavedWarning(null)
  }, [])

  const value = useMemo<ConfigNavigationGuardContextValue>(
    () => ({
      isConfigDirty,
      unsavedWarning,
      setConfigDirty,
      showUnsavedWarning,
      clearUnsavedWarning,
    }),
    [clearUnsavedWarning, isConfigDirty, setConfigDirty, showUnsavedWarning, unsavedWarning],
  )

  return (
    <ConfigNavigationGuardContext.Provider value={value}>
      {children}
    </ConfigNavigationGuardContext.Provider>
  )
}

export function useConfigNavigationGuard() {
  const context = useContext(ConfigNavigationGuardContext)
  if (!context) {
    throw new Error('useConfigNavigationGuard must be used within ConfigNavigationGuardProvider')
  }
  return context
}
