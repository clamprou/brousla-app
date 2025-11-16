import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext.jsx'
import { LogOut, User, Mail, Shield } from 'lucide-react'
import { BASE_API_URL } from '../config/api.js'

export default function Profile() {
  const { token, logout } = useAuth()
  const [userInfo, setUserInfo] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchUserInfo = async () => {
      if (!token) {
        setIsLoading(false)
        return
      }

      try {
        console.log('Fetching user info with token:', token.substring(0, 20) + '...')
        
        const response = await fetch(`${BASE_API_URL}/auth/me`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        })

        console.log('User info response status:', response.status)

        if (response.ok) {
          const data = await response.json()
          setUserInfo(data)
        } else {
          const errorText = await response.text()
          let errorData = null
          try {
            errorData = JSON.parse(errorText)
          } catch (e) {
            errorData = { detail: errorText }
          }
          
          console.error('Failed to load user info:', {
            status: response.status,
            statusText: response.statusText,
            body: errorData
          })
          
          if (response.status === 401) {
            setError('Authentication failed. Please log in again.')
            // Token might be invalid, logout user
            logout()
          } else {
            setError(errorData.detail || 'Failed to load user information')
          }
        }
      } catch (err) {
        console.error('Error fetching user info:', err)
        setError('Error loading user information: ' + err.message)
      } finally {
        setIsLoading(false)
      }
    }

    fetchUserInfo()
  }, [token, logout])

  const handleLogout = () => {
    logout()
    // Navigation will be handled by ProtectedRoute showing login form
  }

  return (
    <div className="h-full p-6 bg-gray-950">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-200 mb-2">Profile</h1>
          <p className="text-sm text-gray-400">Manage your account settings</p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-gray-400">Loading...</div>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-900/20 border border-red-600/30 rounded-lg">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        ) : userInfo ? (
          <div className="space-y-6">
            {/* User Info Card */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center">
                  <User className="h-8 w-8 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-200">Account Information</h2>
                  <p className="text-sm text-gray-400">Your account details</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
                  <Mail className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-xs text-gray-500 mb-1">Email</p>
                    <p className="text-sm text-gray-200">{userInfo.email}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
                  <Shield className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-xs text-gray-500 mb-1">User ID</p>
                    <p className="text-sm text-gray-200 font-mono">{userInfo.id}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Logout Section */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-200 mb-2">Account Actions</h3>
              <p className="text-sm text-gray-400 mb-4">
                Sign out of your account. You'll need to log in again to access the application.
              </p>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-700 hover:bg-red-600 text-gray-200 rounded-lg transition-colors font-medium"
              >
                <LogOut className="h-5 w-5" />
                Log Out
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}

