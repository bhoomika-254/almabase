import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import AuthPage from './pages/AuthPage'
import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'
import ReviewPage from './pages/ReviewPage'
import VersionHistoryPage from './pages/VersionHistoryPage'
import SearchReferencesPage from './pages/SearchReferencesPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/projects/:projectId/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
          <Route path="/projects/:projectId/review" element={<ProtectedRoute><ReviewPage /></ProtectedRoute>} />
          <Route path="/projects/:projectId/history" element={<ProtectedRoute><VersionHistoryPage /></ProtectedRoute>} />
          <Route path="/projects/:projectId/search" element={<ProtectedRoute><SearchReferencesPage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
