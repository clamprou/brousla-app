import React, { createContext, useContext, useState, useEffect } from 'react'
import { login as apiLogin, register as apiRegister, handleGoogleOAuthCallback } from '../utils/apiClient.js'
import { getUserIdFromToken } from '../utils/userUtils.js'

const AuthContext = createContext(null)

const AUTH_TOKEN_KEY = 'authToken'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null)
  const [userId, setUserId] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  // Extract user ID from token
  const extractUserId = (tokenValue) => {
    if (tokenValue) {
      const id = getUserIdFromToken(tokenValue)
      setUserId(id)
      return id
    } else {
      setUserId(null)
      return null
    }
  }

  // Load token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY)
    if (storedToken) {
      setToken(storedToken)
      extractUserId(storedToken)
    }
    setIsLoading(false)
  }, [])

  const login = async (credentials) => {
    try {
      const result = await apiLogin(credentials)
      const newToken = result.token
      setToken(newToken)
      localStorage.setItem(AUTH_TOKEN_KEY, newToken)
      extractUserId(newToken)
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  const register = async (data) => {
    try {
      const result = await apiRegister(data)
      // Registration no longer returns a token - email confirmation required
      // Do NOT set token or auto-login
      return { success: true, message: result.message }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  const loginWithGoogle = async (callbackUrl) => {
    try {
      const result = await handleGoogleOAuthCallback(callbackUrl)
      const newToken = result.token
      setToken(newToken)
      localStorage.setItem(AUTH_TOKEN_KEY, newToken)
      extractUserId(newToken)
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  const logout = async () => {
    // Save userId before clearing it (for deactivation and clearing workflowManager)
    const currentUserId = userId
    
    // Deactivate all workflows before logout
    if (currentUserId) {
      try {
        const BACKEND_URL = 'http://127.0.0.1:8000'
        await fetch(`${BACKEND_URL}/workflows/deactivate-all`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'X-User-Id': currentUserId
          },
        })
      } catch (error) {
        console.error('Error deactivating workflows on logout:', error)
      }
      
      // Clear workflowManager's in-memory workflows (but don't delete from localStorage)
      // Workflows will be loaded from localStorage when user logs back in
      const { workflowManager } = await import('../utils/workflowManager.js')
      workflowManager.clearWorkflows()
      workflowManager.setUserId(null)
    }
    
    setToken(null)
    setUserId(null)
    localStorage.removeItem(AUTH_TOKEN_KEY)
    
    // NOTE: We do NOT delete userWorkflows from localStorage on logout
    // This allows workflows to persist across login sessions
  }

  const getUserId = () => {
    return userId
  }

  const isAuthenticated = !!token

  const value = {
    token,
    userId,
    isAuthenticated,
    isLoading,
    login,
    register,
    loginWithGoogle,
    logout,
    getUserId,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

