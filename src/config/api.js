// API Configuration
// Reads BASE_API_URL from environment variable or falls back to default

const BASE_API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

export { BASE_API_URL }

