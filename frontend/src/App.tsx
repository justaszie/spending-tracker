import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './components/Login'
import Signup from './components/Signup'
import TransactionsTable from './components/TransactionsTable'
import StatementUpload from './components/StatementUpload'
import './App.css'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route
              path="/transactions"
              element={
                <ProtectedRoute>
                  <TransactionsTable />
                </ProtectedRoute>
              }
            />
            <Route
              path="/upload"
              element={
                <ProtectedRoute>
                  <StatementUpload />
                </ProtectedRoute>
              }
            />
            <Route path="/" element={<Navigate to="/transactions" replace />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
