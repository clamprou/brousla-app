/**
 * User utility functions for extracting user ID from JWT tokens and API calls
 */

/**
 * Decode JWT token to extract user ID
 * JWT tokens have the format: header.payload.signature
 * The payload contains the user ID in the 'sub' field
 * @param {string} token - JWT token
 * @returns {string|null} - User ID or null if invalid
 */
export function getUserIdFromToken(token) {
  if (!token) return null
  
  try {
    // JWT token has 3 parts separated by dots
    const parts = token.split('.')
    if (parts.length !== 3) return null
    
    // Decode the payload (second part)
    const payload = parts[1]
    // Add padding if needed for base64 decoding
    const paddedPayload = payload + '='.repeat((4 - payload.length % 4) % 4)
    const decodedPayload = JSON.parse(atob(paddedPayload))
    
    // Extract user ID from 'sub' field (standard JWT claim)
    return decodedPayload.sub || null
  } catch (error) {
    console.error('Error decoding JWT token:', error)
    return null
  }
}

/**
 * Get user ID from API endpoint
 * @param {string} token - JWT token for authentication
 * @returns {Promise<string|null>} - User ID or null if error
 */
export async function getUserIdAsync(token) {
  if (!token) return null
  
  try {
    const { BASE_API_URL } = await import('../config/api.js')
    const response = await fetch(`${BASE_API_URL}/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
    
    if (response.ok) {
      const data = await response.json()
      return data.id || null
    }
    return null
  } catch (error) {
    console.error('Error fetching user ID:', error)
    return null
  }
}

