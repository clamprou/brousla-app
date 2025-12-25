import { BASE_API_URL } from '../config/api.js'

const DEBUG_API = import.meta.env.DEV || import.meta.env.VITE_DEBUG_API === 'true'
const debugLog = (...args) => {
  if (DEBUG_API) console.log(...args)
}

/**
 * API Client for backend communication
 * All AI-related calls go through the backend server
 */

/**
 * Login user and get JWT token
 * @param {Object} credentials - { email/username, password }
 * @returns {Promise<{token: string}>}
 */
export async function login(credentials) {
  const requestBody = JSON.stringify(credentials)
  const requestUrl = `${BASE_API_URL}/auth/login`
  
  const safeCredentialsForLog = {
    ...credentials,
    ...(credentials && typeof credentials === 'object' && 'password' in credentials
      ? { password: '[REDACTED]' }
      : null),
  }

  if (DEBUG_API) {
    debugLog('Login Request:', {
      url: requestUrl,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: safeCredentialsForLog
    })
  }

  const response = await fetch(requestUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: requestBody,
  })

  const responseText = await response.text()
  let errorData = null
  
  try {
    errorData = JSON.parse(responseText)
  } catch (e) {
    errorData = { detail: responseText, raw: responseText }
  }

  if (DEBUG_API) {
    debugLog('Login Response:', {
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
      body: errorData
    })
  }

  if (!response.ok) {
    const errorMessage = errorData.detail || errorData.message || `Login failed: ${response.status}`
    const error = new Error(errorMessage)
    error.status = response.status
    error.statusText = response.statusText
    error.responseBody = errorData
    error.requestBody = safeCredentialsForLog
    error.requestUrl = requestUrl
    throw error
  }

  const data = JSON.parse(responseText)
  return { token: data.access_token || data.token }
}

/**
 * Register new user (does not return token - email confirmation required)
 * @param {Object} data - Registration data (email, password)
 * @returns {Promise<{message: string}>}
 */
export async function register(data) {
  const requestBody = JSON.stringify(data)
  const requestUrl = `${BASE_API_URL}/auth/register`
  
  const safeRegistrationForLog = {
    ...data,
    ...(data && typeof data === 'object' && 'password' in data ? { password: '[REDACTED]' } : null),
  }

  if (DEBUG_API) {
    debugLog('Register Request:', {
      url: requestUrl,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: safeRegistrationForLog
    })
  }

  const response = await fetch(requestUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: requestBody,
  })

  const responseText = await response.text()
  let errorData = null
  
  try {
    errorData = JSON.parse(responseText)
  } catch (e) {
    errorData = { detail: responseText, raw: responseText }
  }

  if (DEBUG_API) {
    debugLog('Register Response:', {
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
      body: errorData
    })
  }

  if (!response.ok) {
    const errorMessage = errorData.detail || errorData.message || `Registration failed: ${response.status}`
    const error = new Error(errorMessage)
    error.status = response.status
    error.statusText = response.statusText
    error.responseBody = errorData
    error.requestBody = safeRegistrationForLog
    error.requestUrl = requestUrl
    throw error
  }

  const result = JSON.parse(responseText)
  return { message: result.message }
}

/**
 * Confirm email address using verification token
 * @param {string} token - Email verification token
 * @returns {Promise<{message: string}>}
 */
export async function confirmEmail(token) {
  const requestBody = JSON.stringify({ token })
  const requestUrl = `${BASE_API_URL}/auth/confirm-email`
  
  const response = await fetch(requestUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: requestBody,
  })

  const responseText = await response.text()
  let errorData = null
  
  try {
    errorData = JSON.parse(responseText)
  } catch (e) {
    errorData = { detail: responseText, raw: responseText }
  }

  if (!response.ok) {
    const errorMessage = errorData.detail || errorData.message || `Email confirmation failed: ${response.status}`
    const error = new Error(errorMessage)
    error.status = response.status
    error.statusText = response.statusText
    error.responseBody = errorData
    throw error
  }

  const result = JSON.parse(responseText)
  return { message: result.message }
}

/**
 * Resend confirmation email
 * @param {string} email - User email address
 * @returns {Promise<{message: string}>}
 */
export async function resendConfirmationEmail(email) {
  const requestBody = JSON.stringify({ email })
  const requestUrl = `${BASE_API_URL}/auth/resend-confirmation`
  
  const response = await fetch(requestUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: requestBody,
  })

  const responseText = await response.text()
  let errorData = null
  
  try {
    errorData = JSON.parse(responseText)
  } catch (e) {
    errorData = { detail: responseText, raw: responseText }
  }

  if (!response.ok) {
    const errorMessage = errorData.detail || errorData.message || `Resend confirmation failed: ${response.status}`
    const error = new Error(errorMessage)
    error.status = response.status
    error.statusText = response.statusText
    error.responseBody = errorData
    throw error
  }

  const result = JSON.parse(responseText)
  return { message: result.message }
}

/**
 * Initiate Google OAuth flow
 * Gets the OAuth URL from backend and opens it in external browser
 * @returns {Promise<{auth_url: string, state: string}>}
 */
export async function initiateGoogleOAuth() {
  const requestUrl = `${BASE_API_URL}/auth/google/login`
  
  const response = await fetch(requestUrl, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  const responseText = await response.text()
  let errorData = null
  
  try {
    errorData = JSON.parse(responseText)
  } catch (e) {
    errorData = { detail: responseText, raw: responseText }
  }

  if (!response.ok) {
    const errorMessage = errorData.detail || errorData.message || `OAuth initiation failed: ${response.status}`
    const error = new Error(errorMessage)
    error.status = response.status
    error.statusText = response.statusText
    error.responseBody = errorData
    throw error
  }

  const data = JSON.parse(responseText)
  return { auth_url: data.auth_url, state: data.state }
}

/**
 * Check Google OAuth status by polling the backend
 * @param {string} state - The OAuth state token
 * @returns {Promise<{status: 'pending' | 'success' | 'error', token?: string, message?: string}>}
 */
export async function checkGoogleOAuthStatus(state) {
  const requestUrl = `${BASE_API_URL}/auth/google/status/${state}`
  
  const response = await fetch(requestUrl, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  const responseText = await response.text()
  let errorData = null
  
  try {
    errorData = JSON.parse(responseText)
  } catch (e) {
    errorData = { detail: responseText, raw: responseText }
  }

  if (!response.ok) {
    const errorMessage = errorData.detail || errorData.message || `OAuth status check failed: ${response.status}`
    const error = new Error(errorMessage)
    error.status = response.status
    error.statusText = response.statusText
    error.responseBody = errorData
    throw error
  }

  const data = JSON.parse(responseText)
  return data
}

/**
 * Handle Google OAuth callback
 * Extracts token from callback URL parameters
 * @param {string} callbackUrl - The callback URL with token parameter
 * @returns {Promise<{token: string}>}
 */
export async function handleGoogleOAuthCallback(callbackUrl) {
  if (DEBUG_API) debugLog('handleGoogleOAuthCallback called with URL:', callbackUrl)
  try {
    const url = new URL(callbackUrl)
    const status = url.searchParams.get('status')
    const token = url.searchParams.get('token')
    const message = url.searchParams.get('message')
    
    if (DEBUG_API) debugLog('Parsed URL params - status:', status, 'token:', token ? 'present' : 'missing', 'message:', message)
    
    if (status === 'error') {
      const error = new Error(message || 'Google OAuth error')
      throw error
    }
    
    if (status === 'success' && token) {
      if (DEBUG_API) debugLog('Successfully extracted token from callback URL')
      return { token }
    }
    
    throw new Error('Invalid OAuth callback: missing token or status')
  } catch (error) {
    if (error instanceof TypeError) {
      if (DEBUG_API) debugLog('TypeError parsing URL, trying manual parsing (might be custom protocol)')
      // URL parsing error - might be custom protocol
      // Try to parse manually
      const match = callbackUrl.match(/[?&]status=([^&]+)/)
      const status = match ? decodeURIComponent(match[1]) : null
      
      const tokenMatch = callbackUrl.match(/[?&]token=([^&]+)/)
      const token = tokenMatch ? decodeURIComponent(tokenMatch[1]) : null
      
      const messageMatch = callbackUrl.match(/[?&]message=([^&]+)/)
      const message = messageMatch ? decodeURIComponent(messageMatch[1]) : null
      
      if (DEBUG_API) debugLog('Manually parsed - status:', status, 'token:', token ? 'present' : 'missing', 'message:', message)
      
      if (status === 'error') {
        throw new Error(message || 'Google OAuth error')
      }
      
      if (status === 'success' && token) {
        if (DEBUG_API) debugLog('Successfully extracted token from manual parsing')
        return { token }
      }
      
      throw new Error('Invalid OAuth callback: missing token or status')
    }
    console.error('Error in handleGoogleOAuthCallback:', error)
    throw error
  }
}

/**
 * Get subscription status for the current user
 * @returns {Promise<Object>} Subscription status information
 */
export async function getSubscriptionStatus(token) {
  const requestUrl = `${BASE_API_URL}/api/subscription/status`
  
  const response = await fetch(requestUrl, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const errorText = await response.text()
    let errorData = null
    try {
      errorData = JSON.parse(errorText)
    } catch (e) {
      errorData = { detail: errorText }
    }
    
    const error = new Error(errorData.detail || 'Failed to get subscription status')
    error.status = response.status
    throw error
  }

  return await response.json()
}

/**
 * Check if user can execute a workflow
 * @param {string} token - JWT token
 * @returns {Promise<{can_execute: boolean, message: string}>}
 */
export async function checkExecutionEligibility(token) {
  const requestUrl = `${BASE_API_URL}/api/subscription/check-execution`
  
  const response = await fetch(requestUrl, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const errorText = await response.text()
    let errorData = null
    try {
      errorData = JSON.parse(errorText)
    } catch (e) {
      errorData = { detail: errorText }
    }
    
    const error = new Error(errorData.detail || 'Failed to check execution eligibility')
    error.status = response.status
    throw error
  }

  return await response.json()
}

/**
 * Increment execution count after successful workflow execution
 * @param {string} token - JWT token
 * @returns {Promise<Object>} Updated subscription status
 */
export async function incrementExecutionCount(token) {
  const requestUrl = `${BASE_API_URL}/api/subscription/increment-execution`
  
  const response = await fetch(requestUrl, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const errorText = await response.text()
    let errorData = null
    try {
      errorData = JSON.parse(errorText)
    } catch (e) {
      errorData = { detail: errorText }
    }
    
    const error = new Error(errorData.detail || 'Failed to increment execution count')
    error.status = response.status
    throw error
  }

  return await response.json()
}

/**
 * Create Stripe checkout session for subscription
 * @param {string} token - JWT token
 * @param {string} plan - Subscription plan ('basic', 'plus', or 'pro')
 * @returns {Promise<{checkout_url: string, session_id: string}>}
 */
export async function createCheckoutSession(token, plan) {
  const requestUrl = `${BASE_API_URL}/api/subscription/create-checkout`
  
  const response = await fetch(requestUrl, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ plan }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    let errorData = null
    try {
      errorData = JSON.parse(errorText)
    } catch (e) {
      errorData = { detail: errorText }
    }
    
    const error = new Error(errorData.detail || 'Failed to create checkout session')
    error.status = response.status
    throw error
  }

  return await response.json()
}

/**
 * Cancel the current user's subscription
 * @param {string} token - JWT token
 * @returns {Promise<{success: boolean, message: string}>}
 */
export async function cancelSubscription(token) {
  const requestUrl = `${BASE_API_URL}/api/subscription/cancel`
  
  const response = await fetch(requestUrl, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const errorText = await response.text()
    let errorData = null
    try {
      errorData = JSON.parse(errorText)
    } catch (e) {
      errorData = { detail: errorText }
    }
    
    const error = new Error(errorData.detail || 'Failed to cancel subscription')
    error.status = response.status
    throw error
  }

  return await response.json()
}

/**
 * Completely cancel the current user's subscription and restore trial status
 * @param {string} token - JWT token
 * @returns {Promise<{success: boolean, message: string}>}
 */
export async function cancelSubscriptionCompletely(token) {
  const requestUrl = `${BASE_API_URL}/api/subscription/cancel-completely`
  
  const response = await fetch(requestUrl, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const errorText = await response.text()
    let errorData = null
    try {
      errorData = JSON.parse(errorText)
    } catch (e) {
      errorData = { detail: errorText }
    }
    
    const error = new Error(errorData.detail || 'Failed to cancel subscription completely')
    error.status = response.status
    throw error
  }

  return await response.json()
}

