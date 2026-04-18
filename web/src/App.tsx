import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './layouts/AppShell'
import ChatPage from './pages/ChatPage'
import ConfigPage from './pages/ConfigPage'
import KnowledgePage from './pages/KnowledgePage'
import UploadPage from './pages/UploadPage'
import './App.css'

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/config" element={<ConfigPage />} />
      </Route>
    </Routes>
  )
}

export default App
