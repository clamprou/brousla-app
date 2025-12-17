import React from 'react'
import { useAuth } from '../contexts/AuthContext.jsx'
import LoginForm from './LoginForm.jsx'

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen w-screen bg-gray-950">
        <div className="text-gray-400">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-screen w-screen bg-gray-950 p-4">
        <LoginForm />
      </div>
    )
  }

  return <>{children}</>
}

