import { App as AntdApp, ConfigProvider } from 'antd'
import { Navigate, Route, Routes } from 'react-router-dom'
import { ConfigNavigationGuardProvider } from './contexts/ConfigNavigationGuard'
import { appAntdTheme } from './lib/antdTheme'
import AppShell from './layouts/AppShell'
import ChatPage from './pages/ChatPage'
import ConfigPage from './pages/ConfigPage'
import EvaluatePage from './pages/EvaluatePage'
import KnowledgePage from './pages/KnowledgePage'
import UploadPage from './pages/UploadPage'
import './App.css'

function App() {
  return (
    <ConfigNavigationGuardProvider>
      <ConfigProvider theme={appAntdTheme}>
        <AntdApp>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/knowledge" element={<KnowledgePage />} />
              <Route path="/evaluate" element={<EvaluatePage />} />
              <Route path="/config" element={<ConfigPage />} />
            </Route>
          </Routes>
        </AntdApp>
      </ConfigProvider>
    </ConfigNavigationGuardProvider>
  )
}

export default App
