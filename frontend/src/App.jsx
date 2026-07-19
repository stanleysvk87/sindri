import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import ScriptList from './pages/ScriptList'
import ScriptDetail from './pages/ScriptDetail'
import AddScript from './pages/AddScript'
import Settings from './pages/Settings'
import { api } from './lib/api'

function RequireAuth({ children }) {
  const [status, setStatus] = useState('checking')
  const navigate = useNavigate()

  useEffect(() => {
    api
      .settings()
      .then(() => setStatus('ok'))
      .catch(() => {
        setStatus('redirect')
        navigate('/login')
      })
  }, [navigate])

  if (status !== 'ok') return null
  return <Layout>{children}</Layout>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <ScriptList />
          </RequireAuth>
        }
      />
      <Route
        path="/scripts/:id"
        element={
          <RequireAuth>
            <ScriptDetail />
          </RequireAuth>
        }
      />
      <Route
        path="/add"
        element={
          <RequireAuth>
            <AddScript />
          </RequireAuth>
        }
      />
      <Route
        path="/settings"
        element={
          <RequireAuth>
            <Settings />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
