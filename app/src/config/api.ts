// API configuration file
// Support configuring different API server addresses via environment variables

export const API_CONFIG = {
  // Hardcoded API address to ensure Android app can access correctly
  BASE_URL: 'http://10.80.109.73:5051',
  
  // API timeout settings
  TIMEOUT: 10000,
  
  // API endpoints
  ENDPOINTS: {
    LOGIN: '/api/auth/login',
    BALANCE: '/api/user/balance',
    CLAIM: '/api/claim',
    VERIFY: '/api/ledger/verify',
    STUDENTS: '/api/students',
    SHOP_ITEMS: '/api/shop/items',
    SHOP_PURCHASE: '/api/shop/purchase',
    LEADERBOARD: '/api/leaderboard'
  }
}

// Get complete API URL
export const getApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`
}

// Print current API configuration (development environment)
if (import.meta.env.DEV) {
  console.log('API Configuration:', API_CONFIG)
}
