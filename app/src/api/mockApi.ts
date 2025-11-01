import axios from 'axios'
import { API_CONFIG, getApiUrl } from '../config/api'

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.data)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const api = {
  // 学生登录
  login: async (username: string, password: string) => {
    try {
      const response = await apiClient.post(getApiUrl(API_CONFIG.ENDPOINTS.LOGIN), {
        username,
        password
      })
      
      if (response.data.ok) {
        return {
          ok: true,
          user_id: response.data.user_id,
          username: response.data.username
        }
      } else {
        throw new Error(response.data.message || 'Login failed')
      }
    } catch (error: any) {
      console.error('Login API Error:', error)
      throw new Error(error.response?.data?.message || error.message || 'Login failed')
    }
  },

  // 获取用户余额和交易记录
  balance: async (user_id: number) => {
    try {
      const response = await apiClient.get(getApiUrl(API_CONFIG.ENDPOINTS.BALANCE), {
        params: { user_id }
      })
      
      return {
        balance: response.data.balance || 0,
        recent: response.data.recent || []
      }
    } catch (error: any) {
      console.error('Balance API Error:', error)
      throw new Error(error.response?.data?.message || error.message || 'Failed to get balance')
    }
  },

  // 领取奖励
  claim: async (tokenData: any, user_id: number) => {
    try {
      // 如果是ClassMint令牌格式，需要重新构建令牌字符串
      let tokenStr: string
      
      if (tokenData && typeof tokenData === 'object') {
        // 这是ClassMint令牌的payload数据，需要重新构建完整令牌
        // 这里我们直接发送payload数据，后端会处理
        tokenStr = JSON.stringify(tokenData)
      } else {
        // 这是完整的令牌字符串
        tokenStr = tokenData
      }
      
      const response = await apiClient.post(getApiUrl(API_CONFIG.ENDPOINTS.CLAIM), {
        token: tokenStr,
        user_id
      })
      
      if (response.data.ok) {
        return {
          balance: response.data.balance,
          tx_id: response.data.tx_id,
          block_hash: response.data.block_hash
        }
      } else {
        throw new Error(response.data.detail || 'Claim failed')
      }
    } catch (error: any) {
      console.error('Claim API Error:', error)
      throw new Error(error.response?.data?.detail || error.message || 'Claim failed')
    }
  },

  // 验证区块链完整性
  verify: async () => {
    try {
      const response = await apiClient.get(getApiUrl(API_CONFIG.ENDPOINTS.VERIFY))
      
      return {
        ok: response.data.ok,
        length: response.data.length,
        broken_at: response.data.broken_at
      }
    } catch (error: any) {
      console.error('Verify API Error:', error)
      throw new Error(error.response?.data?.message || error.message || 'Verification failed')
    }
  },

  // 商店相关API
  shopItems: async () => {
    try {
      const response = await apiClient.get(getApiUrl(API_CONFIG.ENDPOINTS.SHOP_ITEMS))
      return response.data
    } catch (error) {
      console.error('Shop items API Error:', error)
      throw error
    }
  },

  purchaseItem: async (itemId: number, quantity: number = 1, userId: number) => {
    try {
      const response = await apiClient.post(getApiUrl(API_CONFIG.ENDPOINTS.SHOP_PURCHASE), {
        user_id: userId,
        item_id: itemId,
        quantity: quantity
      })
      return response.data
    } catch (error) {
      console.error('Purchase API Error:', error)
      throw error
    }
  },

  // 排行榜API
  getLeaderboard: async () => {
    try {
      const response = await apiClient.get(getApiUrl(API_CONFIG.ENDPOINTS.LEADERBOARD))
      return response.data
    } catch (error) {
      console.error('Leaderboard API Error:', error)
      throw error
    }
  }
}