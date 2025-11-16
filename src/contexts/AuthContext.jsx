import React, { createContext, useContext, useState, useEffect } from 'react'
import { login as apiLogin, register as apiRegister } from '../utils/apiClient.js'

const AuthContext = createContext(null)

const AUTH_TOKEN_KEY = 'authToken'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  // Load token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY)
    if (storedToken) {
      setToken(storedToken)
    }
    setIsLoading(false)
  }, [])

  const login = async (credentials) => {
    try {
      const result = await apiLogin(credentials)
      const newToken = result.token
      setToken(newToken)
      localStorage.setItem(AUTH_TOKEN_KEY, newToken)
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  const register = async (data) => {
    try {
      const result = await apiRegister(data)
      const newToken = result.token
      setToken(newToken)
      localStorage.setItem(AUTH_TOKEN_KEY, newToken)
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  const logout = () => {
    setToken(null)
    localStorage.removeItem(AUTH_TOKEN_KEY)
  }

  const isAuthenticated = !!token

  const value = {
    token,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
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

