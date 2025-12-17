import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext.jsx'
import { AlertCircle, Loader2, LogIn, UserPlus, CheckCircle } from 'lucide-react'
import { initiateGoogleOAuth, checkGoogleOAuthStatus } from '../utils/apiClient.js'

// Password validation function
const validatePassword = (password) => {
  const errors = []
  
  if (password.length < 8) {
    errors.push('Password must be at least 8 characters long')
  }
  
  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter')
  }
  
  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    errors.push('Password must contain at least one special character')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

export default function LoginForm({ onSuccess }) {
  const { login, register, loginWithGoogle, isAuthenticated } = useAuth()
  const [isRegisterMode, setIsRegisterMode] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [error, setError] = useState(null)
  const [passwordErrors, setPasswordErrors] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isGoogleLoading, setIsGoogleLoading] = useState(false)
  const [registrationSuccess, setRegistrationSuccess] = useState(false)
  const [registeredEmail, setRegisteredEmail] = useState('')

  // Clear Google loading state when authentication succeeds
  useEffect(() => {
    if (isAuthenticated) {
      setIsGoogleLoading(false)
      if (onSuccess) {
        onSuccess()
      }
    }
  }, [isAuthenticated, onSuccess])
  
  // Also clear loading state when component mounts if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      setIsGoogleLoading(false)
    }
  }, [])

  // Listen for OAuth callback events (use capture phase to catch events early)
  useEffect(() => {
    const handleOAuthCallback = (event) => {
      console.log('LoginForm received OAuth callback event:', event.detail)
      if (event.detail && event.detail.type === 'google-oauth-success') {
        console.log('OAuth success, clearing loading state')
        setIsGoogleLoading(false)
      } else if (event.detail && event.detail.type === 'google-oauth-error') {
        console.log('OAuth error, clearing loading state')
        setIsGoogleLoading(false)
        setError(event.detail.message || 'Google sign-in failed')
      }
    }

    // Use capture phase to ensure we catch the event
    window.addEventListener('google-oauth-callback', handleOAuthCallback, true)
    return () => {
      window.removeEventListener('google-oauth-callback', handleOAuthCallback, true)
    }
  }, [])

  // Clear loading state if we navigate away from login (e.g., to OAuth callback page)
  useEffect(() => {
    const checkLocation = () => {
      if (window.location.pathname === '/google-oauth-callback') {
        setIsGoogleLoading(false)
      }
    }
    
    checkLocation()
    const interval = setInterval(checkLocation, 500)
    return () => clearInterval(interval)
  }, [])

  // Check if all registration requirements are met
  const isRegistrationValid = () => {
    if (!isRegisterMode) return true
    
    const passwordValidation = validatePassword(password)
    const passwordsMatch = password === passwordConfirmation && passwordConfirmation.length > 0
    
    return passwordValidation.isValid && passwordsMatch
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setRegistrationSuccess(false)
    setIsLoading(true)

    try {
      let result
      if (isRegisterMode) {
        // Validate password strength
        const passwordValidation = validatePassword(password)
        if (!passwordValidation.isValid) {
          setPasswordErrors(passwordValidation.errors)
          setError(passwordValidation.errors.join('\n'))
          setIsLoading(false)
          return
        }
        
        // Validate password confirmation
        if (password !== passwordConfirmation) {
          setError('Passwords do not match')
          setPasswordErrors([])
          setIsLoading(false)
          return
        }
        
        // Clear password errors if validation passes
        setPasswordErrors([])
        
        // Server expects email and password for registration
        result = await register({
          email,
          password,
        })
        
        if (result.success) {
          setRegisteredEmail(email) // Store email before clearing
          setRegistrationSuccess(true)
          // Clear form
          setEmail('')
          setPassword('')
          setPasswordConfirmation('')
        } else {
          setError(result.error || 'Registration failed')
        }
      } else {
        // Server expects email and password for login
        result = await login({
          email,
          password,
        })

        if (result.success) {
          if (onSuccess) {
            onSuccess()
          }
        } else {
          setError(result.error || 'Authentication failed')
        }
      }
    } catch (err) {
      console.error('Authentication error:', err)
      
      // Build detailed error message
      let errorMessage = err.message || 'An unexpected error occurred'
      
      if (err.status) {
        errorMessage += ` (Status: ${err.status} ${err.statusText || ''})`
      }
      
      if (err.responseBody) {
        // Format validation errors from FastAPI
        if (Array.isArray(err.responseBody.detail)) {
          const validationErrors = err.responseBody.detail.map(e => {
            if (e.loc && e.msg) {
              return `${e.loc.join('.')}: ${e.msg}`
            }
            return e.msg || JSON.stringify(e)
          }).join('\n')
          errorMessage += `\n\nValidation Errors:\n${validationErrors}`
        } else if (err.responseBody.detail) {
          errorMessage += `\n\nDetails: ${typeof err.responseBody.detail === 'string' ? err.responseBody.detail : JSON.stringify(err.responseBody.detail, null, 2)}`
        }
        
        // Add full response body for debugging
        errorMessage += `\n\nFull Response:\n${JSON.stringify(err.responseBody, null, 2)}`
      }
      
      if (err.requestBody) {
        errorMessage += `\n\nRequest Body:\n${JSON.stringify(err.requestBody, null, 2)}`
      }
      
      if (err.requestUrl) {
        errorMessage += `\n\nRequest URL: ${err.requestUrl}`
      }
      
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleSignIn = async () => {
    setError(null)
    setIsGoogleLoading(true)
    
    try {
      // Get the OAuth URL and state from backend
      const result = await initiateGoogleOAuth()
      const { auth_url, state } = result
      
      if (!state) {
        throw new Error('No state token received from server')
      }
      
      // Open the URL in external browser using Electron's shell.openExternal
      if (window.electronAPI && window.electronAPI.openExternal) {
        await window.electronAPI.openExternal(auth_url)
        
        // Start polling for OAuth completion
        const pollInterval = setInterval(async () => {
          try {
            const statusResult = await checkGoogleOAuthStatus(state)
            console.log('OAuth status check:', statusResult)
            
            if (statusResult.status === 'success' && statusResult.token) {
              // Success! Complete the login
              clearInterval(pollInterval)
              const loginResult = await loginWithGoogle(`brousla://google-oauth-callback?status=success&token=${encodeURIComponent(statusResult.token)}`)
              
              if (loginResult.success) {
                setIsGoogleLoading(false)
                // Notify other components
                window.dispatchEvent(new CustomEvent('google-oauth-callback', {
                  detail: { type: 'google-oauth-success', token: statusResult.token }
                }))
                if (onSuccess) {
                  onSuccess()
                }
              } else {
                setIsGoogleLoading(false)
                setError(loginResult.error || 'Failed to complete Google sign-in')
                window.dispatchEvent(new CustomEvent('google-oauth-callback', {
                  detail: { type: 'google-oauth-error', message: loginResult.error }
                }))
              }
            } else if (statusResult.status === 'error') {
              // Error occurred
              clearInterval(pollInterval)
              setIsGoogleLoading(false)
              setError(statusResult.message || 'Google sign-in failed')
              window.dispatchEvent(new CustomEvent('google-oauth-callback', {
                detail: { type: 'google-oauth-error', message: statusResult.message }
              }))
            }
            // If status is 'pending', continue polling
          } catch (pollError) {
            console.error('Error polling OAuth status:', pollError)
            // Don't stop polling on network errors, but stop after max attempts
          }
        }, 2000) // Poll every 2 seconds
        
        // Set a timeout to stop polling after 5 minutes
        const maxPollTime = 300000 // 5 minutes
        const timeoutId = setTimeout(() => {
          clearInterval(pollInterval)
          setIsGoogleLoading((prev) => {
            // Only clear if still loading and not authenticated
            if (prev && !isAuthenticated) {
              setError('Google sign-in timed out. Please try again.')
              return false
            }
            return prev
          })
        }, maxPollTime)
        
        // Cleanup function
        return () => {
          clearInterval(pollInterval)
          clearTimeout(timeoutId)
        }
      } else {
        // Fallback for non-Electron environments (web)
        window.open(auth_url, '_blank')
        setIsGoogleLoading(false)
      }
    } catch (err) {
      console.error('Google OAuth initiation error:', err)
      setError(err.message || 'Failed to initiate Google sign-in')
      setIsGoogleLoading(false)
    }
  }

  return (
    <div className="w-full max-w-md mx-auto p-6 bg-gray-900 border border-gray-800 rounded-xl">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-200 mb-2">
          {isRegisterMode ? 'Create Account' : 'Sign In'}
        </h2>
        <p className="text-sm text-gray-400">
          {isRegisterMode
            ? 'Create a new account to get started'
            : 'Sign in to your account to continue'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            placeholder="email@example.com"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value)
              // Clear errors when user starts typing
              if (passwordErrors.length > 0) {
                setPasswordErrors([])
                setError(null)
              }
            }}
            required
            className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:border-transparent ${
              passwordErrors.length > 0 && isRegisterMode
                ? 'border-red-600 focus:ring-red-600'
                : 'border-gray-700 focus:ring-blue-600'
            }`}
            placeholder="••••••••"
          />
          {isRegisterMode && (password || passwordConfirmation) && (
            <div className="mt-1 text-xs text-gray-400">
              <p>Password must:</p>
              <ul className="list-disc list-inside ml-2 space-y-0.5">
                <li className={password.length >= 8 ? 'text-green-400' : ''}>
                  Be at least 8 characters long
                </li>
                <li className={/[A-Z]/.test(password) ? 'text-green-400' : ''}>
                  Contain at least one uppercase letter
                </li>
                <li className={/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password) ? 'text-green-400' : ''}>
                  Contain at least one special character
                </li>
                <li className={password === passwordConfirmation && passwordConfirmation.length > 0 && password.length > 0 ? 'text-green-400' : ''}>
                  Passwords should be the same
                </li>
              </ul>
            </div>
          )}
        </div>

        {isRegisterMode && (
          <div>
            <label htmlFor="passwordConfirmation" className="block text-sm font-medium text-gray-300 mb-1">
              Confirm Password
            </label>
            <input
              id="passwordConfirmation"
              type="password"
              value={passwordConfirmation}
              onChange={(e) => {
                setPasswordConfirmation(e.target.value)
                // Clear errors when user starts typing
                if (error && error.includes('Passwords do not match')) {
                  setError(null)
                }
              }}
              required
              className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:border-transparent ${
                passwordConfirmation && password !== passwordConfirmation
                  ? 'border-red-600 focus:ring-red-600'
                  : 'border-gray-700 focus:ring-blue-600'
              }`}
              placeholder="••••••••"
            />
          </div>
        )}

        {registrationSuccess && (
          <div className="p-4 bg-green-900/20 border border-green-600/30 rounded-lg">
            <div className="flex items-start gap-2">
              <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-green-300 mb-1">Registration Successful</p>
                <p className="text-sm text-green-200">
                  A confirmation email has been sent to <strong>{registeredEmail}</strong>. Please check your inbox to complete registration.
                </p>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-900/20 border border-red-600/30 rounded-lg">
            <div className="flex items-start gap-2 mb-2">
              <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm font-semibold text-red-300">Authentication Error</p>
            </div>
            <pre className="text-xs text-red-200 whitespace-pre-wrap break-words overflow-auto max-h-96 bg-gray-900/50 p-3 rounded border border-gray-700">
              {error}
            </pre>
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading || (isRegisterMode && !isRegistrationValid())}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed text-gray-200 rounded-lg transition-colors font-medium"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              {isRegisterMode ? 'Creating Account...' : 'Signing In...'}
            </>
          ) : (
            <>
              {isRegisterMode ? (
                <>
                  <UserPlus className="h-4 w-4" />
                  Create Account
                </>
              ) : (
                <>
                  <LogIn className="h-4 w-4" />
                  Sign In
                </>
              )}
            </>
          )}
        </button>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-700"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-gray-900 text-gray-400">Or continue with</span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleGoogleSignIn}
          disabled={isGoogleLoading || isLoading}
          className="w-full flex items-center justify-center gap-3 px-4 py-2.5 bg-white hover:bg-gray-100 disabled:bg-gray-300 disabled:cursor-not-allowed text-gray-900 rounded-lg transition-colors font-medium border border-gray-300"
        >
          {isGoogleLoading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Connecting to Google...</span>
            </>
          ) : (
            <>
              <svg className="h-5 w-5" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              <span>Sign in with Google</span>
            </>
          )}
        </button>

        <div className="text-center">
          <button
            type="button"
            onClick={() => {
              setIsRegisterMode(!isRegisterMode)
              setError(null)
              setPasswordErrors([])
              setRegistrationSuccess(false)
              setPasswordConfirmation('')
              setRegisteredEmail('')
            }}
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            {isRegisterMode
              ? 'Already have an account? Sign in'
              : "Don't have an account? Register"}
          </button>
        </div>
      </form>
    </div>
  )
}

