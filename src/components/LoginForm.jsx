import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext.jsx'
import { AlertCircle, Loader2, LogIn, UserPlus, CheckCircle } from 'lucide-react'

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
  const { login, register } = useAuth()
  const [isRegisterMode, setIsRegisterMode] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [error, setError] = useState(null)
  const [passwordErrors, setPasswordErrors] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [registrationSuccess, setRegistrationSuccess] = useState(false)
  const [registeredEmail, setRegisteredEmail] = useState('')

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

