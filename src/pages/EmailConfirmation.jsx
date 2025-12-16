import React, { useState, useEffect } from 'react'
import { confirmEmail, resendConfirmationEmail } from '../utils/apiClient.js'
import { AlertCircle, CheckCircle, Loader2, Mail, Clock } from 'lucide-react'

export default function EmailConfirmation() {
  const [status, setStatus] = useState('loading') // 'loading', 'success', 'error', 'resend'
  const [message, setMessage] = useState('')
  const [email, setEmail] = useState('')
  const [cooldownSeconds, setCooldownSeconds] = useState(0)
  const [isResending, setIsResending] = useState(false)

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
      token: params.get('token'),
      status: params.get('status'),
      message: params.get('message')
    }
  }

  const urlParams = getParamsFromURL()

  // Check localStorage for resend cooldown
  useEffect(() => {
    const checkCooldown = () => {
      const lastResendKey = 'lastConfirmationEmailResend'
      const lastResend = localStorage.getItem(lastResendKey)
      
      if (lastResend) {
        const lastResendTime = parseInt(lastResend, 10)
        const now = Date.now()
        const elapsed = Math.floor((now - lastResendTime) / 1000)
        const remaining = Math.max(0, 300 - elapsed) // 5 minutes = 300 seconds
        
        if (remaining > 0) {
          setCooldownSeconds(remaining)
        }
      }
    }

    checkCooldown()
    const interval = setInterval(() => {
      checkCooldown()
      const lastResend = localStorage.getItem('lastConfirmationEmailResend')
      if (lastResend) {
        const lastResendTime = parseInt(lastResend, 10)
        const now = Date.now()
        const elapsed = Math.floor((now - lastResendTime) / 1000)
        const remaining = Math.max(0, 300 - elapsed)
        
        if (remaining > 0) {
          setCooldownSeconds(remaining)
        } else {
          setCooldownSeconds(0)
        }
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  // Handle email confirmation on mount
  useEffect(() => {
    // If status and message are in URL (redirected from backend), use those
    if (urlParams.status && urlParams.message) {
      const decodedMessage = decodeURIComponent(urlParams.message)
      if (urlParams.status === 'success') {
        setStatus('success')
        setMessage(decodedMessage)
        // Redirect to login after 3 seconds
        setTimeout(() => {
          window.history.replaceState({}, '', window.location.pathname)
          window.location.reload()
        }, 3000)
      } else {
        setStatus('error')
        setMessage(decodedMessage)
      }
    } 
    // If token is present but no status (direct access), call API
    else if (urlParams.token) {
      handleConfirmEmail(urlParams.token)
    } 
    // No token or status - show error
    else {
      setStatus('error')
      setMessage('No confirmation token provided. Please check your email for the confirmation link.')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleConfirmEmail = async (confirmationToken) => {
    try {
      const result = await confirmEmail(confirmationToken)
      setStatus('success')
      setMessage(result.message || 'Email confirmed successfully!')
      
      // Redirect to login after 3 seconds
      setTimeout(() => {
        // Clear the URL and trigger navigation to login
        window.history.replaceState({}, '', window.location.pathname)
        const ev = new CustomEvent('navigate', { detail: 'login' })
        window.dispatchEvent(ev)
        // Reload to show login form
        window.location.reload()
      }, 3000)
    } catch (error) {
      setStatus('error')
      setMessage(error.message || 'Failed to confirm email. The token may be invalid or expired.')
    }
  }

  const handleResendEmail = async () => {
    if (cooldownSeconds > 0 || isResending) {
      return
    }

    if (!email) {
      setStatus('resend')
      setMessage('Please enter your email address to resend the confirmation email.')
      return
    }

    setIsResending(true)
    setMessage('')

    try {
      const result = await resendConfirmationEmail(email)
      setStatus('resend')
      setMessage(result.message || 'Confirmation email sent successfully!')
      
      // Store timestamp in localStorage
      localStorage.setItem('lastConfirmationEmailResend', Date.now().toString())
      setCooldownSeconds(300) // 5 minutes
    } catch (error) {
      setStatus('resend')
      setMessage(error.message || 'Failed to resend confirmation email. Please try again later.')
    } finally {
      setIsResending(false)
    }
  }

  const formatCooldown = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 p-4">
      <div className="w-full max-w-md p-6 bg-gray-900 border border-gray-800 rounded-xl">
        <div className="mb-6 text-center">
          <h2 className="text-2xl font-semibold text-gray-200 mb-2">
            Email Confirmation
          </h2>
        </div>

        {status === 'loading' && (
          <div className="text-center py-8">
            <Loader2 className="h-12 w-12 text-blue-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-300">Confirming your email address...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="text-center py-8">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <p className="text-lg font-semibold text-green-300 mb-2">Email Confirmed!</p>
            <p className="text-sm text-gray-400 mb-4">{message}</p>
            <p className="text-xs text-gray-500">Redirecting to login...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4">
            <div className="p-4 bg-red-900/20 border border-red-600/30 rounded-lg">
              <div className="flex items-start gap-2 mb-2">
                <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm font-semibold text-red-300">Confirmation Failed</p>
              </div>
              <p className="text-sm text-red-200">{message}</p>
            </div>

            <div className="border-t border-gray-700 pt-4">
              <p className="text-sm text-gray-400 mb-3">Didn't receive the email or link expired?</p>
              <div className="space-y-3">
                <div>
                  <label htmlFor="resendEmail" className="block text-sm font-medium text-gray-300 mb-1">
                    Email Address
                  </label>
                  <input
                    id="resendEmail"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                  />
                </div>
                <button
                  onClick={handleResendEmail}
                  disabled={cooldownSeconds > 0 || isResending}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 text-gray-200 rounded-lg transition-colors font-medium"
                >
                  {isResending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Sending...
                    </>
                  ) : cooldownSeconds > 0 ? (
                    <>
                      <Clock className="h-4 w-4" />
                      Resend available in {formatCooldown(cooldownSeconds)}
                    </>
                  ) : (
                    <>
                      <Mail className="h-4 w-4" />
                      Resend Confirmation Email
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {status === 'resend' && (
          <div className="space-y-4">
            {message && (
              <div className={`p-4 rounded-lg ${
                message.includes('successfully') || message.includes('sent')
                  ? 'bg-green-900/20 border border-green-600/30'
                  : 'bg-blue-900/20 border border-blue-600/30'
              }`}>
                <p className={`text-sm ${
                  message.includes('successfully') || message.includes('sent')
                    ? 'text-green-200'
                    : 'text-blue-200'
                }`}>
                  {message}
                </p>
              </div>
            )}

            <div className="border-t border-gray-700 pt-4">
              <p className="text-sm text-gray-400 mb-3">Need another confirmation email?</p>
              <div className="space-y-3">
                <div>
                  <label htmlFor="resendEmail2" className="block text-sm font-medium text-gray-300 mb-1">
                    Email Address
                  </label>
                  <input
                    id="resendEmail2"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                  />
                </div>
                <button
                  onClick={handleResendEmail}
                  disabled={cooldownSeconds > 0 || isResending}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 text-gray-200 rounded-lg transition-colors font-medium"
                >
                  {isResending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Sending...
                    </>
                  ) : cooldownSeconds > 0 ? (
                    <>
                      <Clock className="h-4 w-4" />
                      Resend available in {formatCooldown(cooldownSeconds)}
                    </>
                  ) : (
                    <>
                      <Mail className="h-4 w-4" />
                      Resend Confirmation Email
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="mt-6 text-center">
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
    </div>
  )
}

