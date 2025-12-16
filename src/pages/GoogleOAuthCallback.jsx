import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext.jsx'
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-react'

export default function GoogleOAuthCallback() {
  const { loginWithGoogle, isAuthenticated } = useAuth()
  const [status, setStatus] = useState('loading') // 'loading', 'success', 'error'
  const [message, setMessage] = useState('')

  // Get parameters from URL query (supports both search params and hash-based routing)
  const getParamsFromURL = () => {
    // Check both window.location.search (dev mode) and hash (production mode)
    let params = new URLSearchParams(window.location.search)
    
    // If hash contains query params (production mode with hash routing)
    if (window.location.hash && window.location.hash.includes('?')) {
      const hashQuery = window.location.hash.split('?')[1]
      const hashParams = new URLSearchParams(hashQuery)
      // Merge hash params, with hash params taking precedence
      params = new URLSearchParams({
        ...Object.fromEntries(params),
        ...Object.fromEntries(hashParams)
      })
    }
    
    return {
      status: params.get('status'),
      token: params.get('token'),
      message: params.get('message')
    }
  }

  // Handle OAuth callback on mount
  useEffect(() => {
    console.log('GoogleOAuthCallback mounted, URL:', window.location.href)
    const urlParams = getParamsFromURL()
    const fullUrl = window.location.href
    
    console.log('URL params:', urlParams)
    
    // If already authenticated, redirect immediately
    if (isAuthenticated) {
      console.log('Already authenticated, redirecting...')
      setTimeout(() => {
        window.history.replaceState({}, '', '/')
        window.location.href = '/'
      }, 100)
      return
    }
    
    // If status and token are in URL (redirected from backend), handle it
    if (urlParams.status === 'success' && urlParams.token) {
      console.log('Found success status and token, processing...')
      handleOAuthSuccess(urlParams.token)
    } else if (urlParams.status === 'error') {
      console.log('Found error status')
      setStatus('error')
      const decodedMessage = urlParams.message ? decodeURIComponent(urlParams.message) : 'Google OAuth error occurred'
      setMessage(decodedMessage)
      // Notify other components that OAuth failed
      window.dispatchEvent(new CustomEvent('google-oauth-callback', {
        detail: { type: 'google-oauth-error', message: decodedMessage }
      }))
    } else {
      console.log('No status/token in URL, trying to parse full URL')
      // Try to parse the full URL (might be custom protocol)
      handleOAuthCallback(fullUrl)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated])

  const handleOAuthCallback = async (callbackUrl) => {
    try {
      const result = await loginWithGoogle(callbackUrl)
      if (result.success) {
        setStatus('success')
        setMessage('Successfully signed in with Google!')
        
        // Notify other components that OAuth succeeded
        window.dispatchEvent(new CustomEvent('google-oauth-callback', {
          detail: { type: 'google-oauth-success' }
        }))
        
        // Redirect to app after 1 second
        setTimeout(() => {
          window.history.replaceState({}, '', window.location.pathname)
          window.location.href = '/'
        }, 1000)
      } else {
        setStatus('error')
        setMessage(result.error || 'Failed to sign in with Google')
        
        // Notify other components that OAuth failed
        window.dispatchEvent(new CustomEvent('google-oauth-callback', {
          detail: { type: 'google-oauth-error', message: result.error }
        }))
      }
    } catch (error) {
      setStatus('error')
      setMessage(error.message || 'Failed to process Google OAuth callback')
      
      // Notify other components that OAuth failed
      window.dispatchEvent(new CustomEvent('google-oauth-callback', {
        detail: { type: 'google-oauth-error', message: error.message }
      }))
    }
  }

  const handleOAuthSuccess = async (token) => {
    console.log('handleOAuthSuccess called with token:', token ? 'token present' : 'no token')
    if (!token) {
      console.error('No token provided to handleOAuthSuccess')
      setStatus('error')
      setMessage('No authentication token received')
      window.dispatchEvent(new CustomEvent('google-oauth-callback', {
        detail: { type: 'google-oauth-error', message: 'No authentication token received' }
      }))
      return
    }
    
    try {
      // Token is already extracted from URL, construct callback URL for loginWithGoogle
      const callbackUrl = `brousla://google-oauth-callback?status=success&token=${encodeURIComponent(token)}`
      console.log('Calling loginWithGoogle with callback URL')
      const result = await loginWithGoogle(callbackUrl)
      console.log('loginWithGoogle result:', result)
      
      if (result.success) {
        setStatus('success')
        setMessage('Successfully signed in with Google!')
        
        // Notify other components that OAuth succeeded
        window.dispatchEvent(new CustomEvent('google-oauth-callback', {
          detail: { type: 'google-oauth-success', token }
        }))
        
        // Redirect to app immediately - the auth state is already set
        // Use a small delay to ensure token is stored and state is updated
        setTimeout(() => {
          console.log('Redirecting to app root...')
          // Clear URL params and navigate to root
          window.history.replaceState({}, '', '/')
          // Force navigation to root to ensure ProtectedRoute re-evaluates
          window.location.href = '/'
        }, 500)
      } else {
        console.error('loginWithGoogle failed:', result.error)
        setStatus('error')
        setMessage(result.error || 'Failed to sign in with Google')
        
        // Notify other components that OAuth failed
        window.dispatchEvent(new CustomEvent('google-oauth-callback', {
          detail: { type: 'google-oauth-error', message: result.error }
        }))
      }
    } catch (error) {
      console.error('Error in handleOAuthSuccess:', error)
      setStatus('error')
      setMessage(error.message || 'Failed to process Google OAuth callback')
      
      // Notify other components that OAuth failed
      window.dispatchEvent(new CustomEvent('google-oauth-callback', {
        detail: { type: 'google-oauth-error', message: error.message }
      }))
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 p-4">
      <div className="w-full max-w-md p-6 bg-gray-900 border border-gray-800 rounded-xl">
        <div className="mb-6 text-center">
          <h2 className="text-2xl font-semibold text-gray-200 mb-2">
            Google Sign-In
          </h2>
        </div>

        {status === 'loading' && (
          <div className="text-center py-8">
            <Loader2 className="h-12 w-12 text-blue-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-300">Completing sign-in...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="text-center py-8">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <p className="text-lg font-semibold text-green-300 mb-2">Sign-In Successful!</p>
            <p className="text-sm text-gray-400 mb-4">{message}</p>
            <p className="text-xs text-gray-500">Redirecting to app...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4">
            <div className="p-4 bg-red-900/20 border border-red-600/30 rounded-lg">
              <div className="flex items-start gap-2 mb-2">
                <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm font-semibold text-red-300">Sign-In Failed</p>
              </div>
              <p className="text-sm text-red-200">{message}</p>
            </div>

            <div className="text-center">
              <button
                onClick={() => {
                  window.history.replaceState({}, '', window.location.pathname)
                  window.location.reload()
                }}
                className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                Back to Login
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

