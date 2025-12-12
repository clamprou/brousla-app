import React, { createContext, useContext, useState, useEffect } from 'react'
import { login as apiLogin, register as apiRegister, handleGoogleOAuthCallback } from '../utils/apiClient.js'
import { getUserIdFromToken } from '../utils/userUtils.js'
import { BASE_API_URL } from '../config/api.js'

const AuthContext = createContext(null)

const AUTH_TOKEN_KEY = 'authToken'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null)
  const [userId, setUserId] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isValidated, setIsValidated] = useState(false)

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

  // Validate token with backend
  const validateToken = async (tokenToValidate) => {
    if (!tokenToValidate) {
      return false
    }

    try {
      const response = await fetch(`${BASE_API_URL}/auth/me`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${tokenToValidate}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const data = await response.json()
        // Token is valid, update userId from response
        setUserId(data.id)
        return true
      } else {
        // Token is invalid or expired
        return false
      }
    } catch (error) {
      console.error('Error validating token:', error)
      return false
    }
  }

  // Load and validate token from localStorage on mount
  useEffect(() => {
    const loadAndValidateToken = async () => {
      const storedToken = localStorage.getItem(AUTH_TOKEN_KEY)
      
      if (storedToken) {
        // Validate token with backend
        const isValid = await validateToken(storedToken)
        
        if (isValid) {
          // Token is valid, set it
          setToken(storedToken)
          extractUserId(storedToken)
        } else {
          // Token is invalid or expired, clear it
          localStorage.removeItem(AUTH_TOKEN_KEY)
          setToken(null)
          setUserId(null)
        }
      }
      
      setIsValidated(true)
      setIsLoading(false)
    }

    loadAndValidateToken()
  }, [])

  const login = async (credentials) => {
    try {
      const result = await apiLogin(credentials)
      const newToken = result.token
      setToken(newToken)
      localStorage.setItem(AUTH_TOKEN_KEY, newToken)
      extractUserId(newToken)
      setIsValidated(true) // Token is fresh from backend, so it's valid
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
      setIsValidated(true) // Token is fresh from backend, so it's valid
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
    setIsValidated(false) // Reset validation state on logout
    localStorage.removeItem(AUTH_TOKEN_KEY)
    
    // NOTE: We do NOT delete userWorkflows from localStorage on logout
    // This allows workflows to persist across login sessions
  }

  const getUserId = () => {
    return userId
  }

  // Only consider authenticated if token exists AND has been validated
  const isAuthenticated = !!token && isValidated

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

