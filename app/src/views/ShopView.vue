<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useUser } from '../store/user'
import { api } from '../api/mockApi'
import { 
  IonPage, 
  IonHeader, 
  IonToolbar, 
  IonTitle, 
  IonContent, 
  IonCard, 
  IonCardHeader, 
  IonCardContent, 
  IonCardTitle,
  IonButton,
  IonIcon,
  IonBadge,
  IonSpinner,
  IonAlert,
  IonToast,
  IonGrid,
  IonRow,
  IonCol,
  IonChip,
  IonText
} from '@ionic/vue'

// 定义类型接口
interface ShopItem {
  id: number
  name: string
  description: string
  price: number
  category: string
  image_url?: string
  stock: number
  status: string
  created_at: number
}

const user = useUser()
const items = ref<ShopItem[]>([])
const loading = ref(false)
const showAlert = ref(false)
const alertMessage = ref('')
const showToast = ref(false)
const toastMessage = ref('')

// 按分类分组商品
const groupedItems = computed(() => {
  const groups: Record<string, ShopItem[]> = {}
  items.value.forEach(item => {
    if (!groups[item.category]) {
      groups[item.category] = []
    }
    groups[item.category].push(item)
  })
  return groups
})

// 加载商品列表
const loadItems = async () => {
  loading.value = true
  try {
    const data = await api.shopItems()
    
    if (data.ok) {
      items.value = data.items
    } else {
      alertMessage.value = 'Failed to load items: ' + data.error
      showAlert.value = true
    }
  } catch (error) {
    console.error('Error loading items:', error)
    alertMessage.value = 'Network error. Please try again.'
    showAlert.value = true
  } finally {
    loading.value = false
  }
}

// 购买商品
const purchaseItem = async (item: ShopItem, quantity: number = 1) => {
  try {
    const data = await api.purchaseItem(item.id, quantity, user.user_id)
    
    if (data.ok) {
      const txId = data.purchase_id || 'Unknown';
      toastMessage.value = `Successfully purchased ${item.name}! (Transaction ID: ${txId})`
      showToast.value = true
      
      // 更新用户余额
      user.balance = data.new_balance
      
      // 重新加载商品列表（更新库存）
      loadItems()
    } else {
      alertMessage.value = data.message || 'Purchase failed'
      showAlert.value = true
    }
  } catch (error) {
    console.error('Error purchasing item:', error)
    alertMessage.value = 'Network error. Please try again.'
    showAlert.value = true
  }
}

// 确认购买
const confirmPurchase = (item: ShopItem) => {
  const totalPrice = item.price * 1
  
  if (user.balance < totalPrice) {
    alertMessage.value = 'Insufficient balance!'
    showAlert.value = true
    return
  }
  
  if (item.stock !== -1 && item.stock < 1) {
    alertMessage.value = 'Item out of stock!'
    showAlert.value = true
    return
  }
  
  purchaseItem(item, 1)
}

// 格式化价格
const formatPrice = (price: number) => {
  return (price / 100).toFixed(2)
}

// 获取分类图标
const getCategoryIcon = (category: string) => {
  const icons: Record<string, string> = {
    food: 'restaurant-outline',
    education: 'book-outline',
    entertainment: 'game-controller-outline',
    reward: 'trophy-outline',
    general: 'gift-outline'
  }
  return icons[category] || 'gift-outline'
}

// 获取分类颜色
const getCategoryColor = (category: string) => {
  const colors: Record<string, string> = {
    food: 'success',
    education: 'primary',
    entertainment: 'warning',
    reward: 'danger',
    general: 'medium'
  }
  return colors[category] || 'medium'
}

onMounted(() => {
  loadItems()
})
</script>

<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>
          <ion-icon name="storefront-outline" class="me-2"></ion-icon>
          Shop
        </ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content class="ion-padding">
      <div class="shop-container">
        <!-- 余额显示 -->
        <ion-card class="balance-card">
          <ion-card-content>
            <div class="balance-display">
              <ion-icon name="wallet-outline" class="balance-icon"></ion-icon>
              <div class="balance-info">
                <h3>Current Balance</h3>
                <div class="balance-amount">
                  <span class="currency">¥</span>
                  <span class="amount">{{ formatPrice(user.balance) }}</span>
                </div>
              </div>
            </div>
          </ion-card-content>
        </ion-card>

        <!-- 加载状态 -->
        <div v-if="loading" class="loading-container">
          <ion-spinner name="crescent"></ion-spinner>
          <p>Loading items...</p>
        </div>

        <!-- 商品列表 -->
        <div v-else>
          <div v-for="(categoryItems, category) in groupedItems" :key="category" class="category-section">
            <div class="category-header">
              <ion-chip :color="getCategoryColor(category)">
                <ion-icon :name="getCategoryIcon(category)"></ion-icon>
                <ion-label>{{ category.charAt(0).toUpperCase() + category.slice(1) }}</ion-label>
              </ion-chip>
            </div>

            <ion-grid>
              <ion-row>
                <ion-col size="6" v-for="item in categoryItems" :key="item.id">
                  <ion-card class="item-card">
                    <ion-card-header>
                      <ion-card-title class="item-title">{{ item.name }}</ion-card-title>
                    </ion-card-header>
                    
                    <ion-card-content>
                      <div class="item-description">
                        <p>{{ item.description || 'No description available' }}</p>
                      </div>
                      
                      <div class="item-price">
                        <ion-text color="primary">
                          <h2>¥{{ formatPrice(item.price) }}</h2>
                        </ion-text>
                      </div>
                      
                      <div class="item-stock" v-if="item.stock !== -1">
                        <ion-badge :color="item.stock > 0 ? 'success' : 'danger'">
                          {{ item.stock > 0 ? `${item.stock} left` : 'Out of stock' }}
                        </ion-badge>
                      </div>
                      
                      <div class="item-actions">
                        <ion-button 
                          expand="block" 
                          :disabled="user.balance < item.price || (item.stock !== -1 && item.stock <= 0)"
                          @click="confirmPurchase(item)"
                          class="purchase-btn"
                        >
                          <ion-icon name="cart-outline" slot="start"></ion-icon>
                          {{ user.balance < item.price ? 'Insufficient Balance' : 'Buy Now' }}
                        </ion-button>
                      </div>
                    </ion-card-content>
                  </ion-card>
                </ion-col>
              </ion-row>
            </ion-grid>
          </div>

          <!-- 空状态 -->
          <div v-if="items.length === 0" class="empty-state">
            <ion-icon name="storefront-outline" class="empty-icon"></ion-icon>
            <h3>No items available</h3>
            <p>Check back later for new items!</p>
          </div>
        </div>
      </div>

      <!-- 警告对话框 -->
      <ion-alert
        :is-open="showAlert"
        :message="alertMessage"
        :buttons="['OK']"
        @didDismiss="showAlert = false"
      ></ion-alert>

      <!-- 成功提示 -->
      <ion-toast
        :is-open="showToast"
        :message="toastMessage"
        :duration="3000"
        @didDismiss="showToast = false"
      ></ion-toast>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.shop-container {
  max-width: 100%;
}

.balance-card {
  margin-bottom: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.balance-display {
  display: flex;
  align-items: center;
  gap: 15px;
}

.balance-icon {
  font-size: 2.5rem;
  opacity: 0.8;
}

.balance-info h3 {
  margin: 0 0 5px 0;
  font-size: 1rem;
  opacity: 0.9;
}

.balance-amount {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.currency {
  font-size: 1.2rem;
  font-weight: 500;
}

.amount {
  font-size: 2rem;
  font-weight: 700;
}

.loading-container {
  text-align: center;
  padding: 40px 20px;
}

.loading-container ion-spinner {
  margin-bottom: 15px;
}

.category-section {
  margin-bottom: 30px;
}

.category-header {
  margin-bottom: 15px;
}

.item-card {
  height: 100%;
  transition: all 0.3s ease;
}

.item-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0,0,0,0.15);
}

.item-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 8px;
}

.item-description {
  margin-bottom: 15px;
}

.item-description p {
  margin: 0;
  font-size: 0.9rem;
  color: #666;
  line-height: 1.4;
}

.item-price {
  margin-bottom: 10px;
}

.item-price h2 {
  margin: 0;
  font-weight: 700;
}

.item-stock {
  margin-bottom: 15px;
}

.purchase-btn {
  --border-radius: 10px;
  font-weight: 600;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 4rem;
  color: #ccc;
  margin-bottom: 20px;
}

.empty-state h3 {
  color: #666;
  margin-bottom: 10px;
}

.empty-state p {
  color: #999;
  margin: 0;
}
</style>
