// API配置文件
// 支持通过环境变量配置不同的API服务器地址

export const API_CONFIG = {
  // 硬编码API地址，确保Android应用能正确访问
  BASE_URL: 'http://10.80.109.73:5051',
  
  // API超时设置
  TIMEOUT: 10000,
  
  // API端点
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

// 获取完整的API URL
export const getApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`
}

// 打印当前API配置（开发环境）
if (import.meta.env.DEV) {
  console.log('API Configuration:', API_CONFIG)
}
