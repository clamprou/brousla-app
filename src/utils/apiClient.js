import { BASE_API_URL } from '../config/api.js'

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
  
  console.log('Login Request:', {
    url: requestUrl,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: credentials
  })

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

  console.log('Login Response:', {
    status: response.status,
    statusText: response.statusText,
    headers: Object.fromEntries(response.headers.entries()),
    body: errorData
  })

  if (!response.ok) {
    const errorMessage = errorData.detail || errorData.message || `Login failed: ${response.status}`
    const error = new Error(errorMessage)
    error.status = response.status
    error.statusText = response.statusText
    error.responseBody = errorData
    error.requestBody = credentials
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
  
  console.log('Register Request:', {
    url: requestUrl,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: data
  })

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

  console.log('Register Response:', {
    status: response.status,
    statusText: response.statusText,
    headers: Object.fromEntries(response.headers.entries()),
    body: errorData
  })

  if (!response.ok) {
    const errorMessage = errorData.detail || errorData.message || `Registration failed: ${response.status}`
    const error = new Error(errorMessage)
    error.status = response.status
    error.statusText = response.statusText
    error.responseBody = errorData
    error.requestBody = data
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

