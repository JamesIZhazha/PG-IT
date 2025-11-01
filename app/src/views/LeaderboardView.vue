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
  IonCardContent,
  IonList,
  IonItem,
  IonLabel,
  IonIcon,
  IonSpinner,
  IonAlert,
  IonChip,
  IonText,
  IonBadge
} from '@ionic/vue'

// 定义类型接口
interface Student {
  rank: number
  user_id: number
  username: string
  balance: number
}

const user = useUser()
const students = ref<Student[]>([])
const loading = ref(false)
const showAlert = ref(false)
const alertMessage = ref('')

// 当前用户的排名
const currentUserRank = computed(() => {
  return students.value.findIndex(s => s.user_id === user.user_id) + 1
})

// 当前用户信息
const currentUserInfo = computed((): Student | undefined => {
  return students.value.find(s => s.user_id === user.user_id)
})

// 加载排行榜
const loadLeaderboard = async () => {
  loading.value = true
  try {
    const data = await api.getLeaderboard()
    
    if (data.ok) {
      students.value = data.students
    } else {
      alertMessage.value = 'Failed to load leaderboard: ' + data.error
      showAlert.value = true
    }
  } catch (error) {
    console.error('Error loading leaderboard:', error)
    alertMessage.value = 'Network error. Please try again.'
    showAlert.value = true
  } finally {
    loading.value = false
  }
}

// 格式化价格
const formatPrice = (price: number) => {
  return (price / 100).toFixed(2)
}

// 获取排名图标
const getRankIcon = (rank: number) => {
  if (rank === 1) return 'trophy'
  if (rank === 2) return 'medal'
  if (rank === 3) return 'medal'
  return 'ribbon'
}

// 获取排名颜色
const getRankColor = (rank: number) => {
  if (rank === 1) return 'warning'
  if (rank === 2) return 'medium'
  if (rank === 3) return 'tertiary'
  return 'primary'
}

// 获取排名徽章颜色
const getRankBadgeColor = (rank: number) => {
  if (rank === 1) return 'warning'
  if (rank === 2) return 'medium'
  if (rank === 3) return 'tertiary'
  return 'primary'
}

onMounted(() => {
  loadLeaderboard()
})
</script>

<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>
          <ion-icon name="trophy-outline" class="me-2"></ion-icon>
          Leaderboard
        </ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content class="ion-padding">
      <div class="leaderboard-container">
        <!-- 当前用户排名卡片 -->
        <ion-card v-if="currentUserInfo" class="current-user-card">
          <ion-card-content>
            <div class="current-user-info">
              <div class="user-rank">
                <ion-badge :color="getRankBadgeColor(currentUserRank)" class="rank-badge">
                  <ion-icon :name="getRankIcon(currentUserRank)"></ion-icon>
                  #{{ currentUserRank }}
                </ion-badge>
              </div>
              <div class="user-details">
                <h3>{{ currentUserInfo.username }}</h3>
                <p class="user-balance">¥{{ formatPrice(currentUserInfo.balance) }}</p>
              </div>
              <div class="user-status">
                <ion-chip :color="currentUserRank <= 3 ? 'success' : 'medium'">
                  <ion-icon :name="currentUserRank <= 3 ? 'star' : 'person'"></ion-icon>
                  <ion-label>{{ currentUserRank <= 3 ? 'Top Player' : 'Player' }}</ion-label>
                </ion-chip>
              </div>
            </div>
          </ion-card-content>
        </ion-card>

        <!-- 加载状态 -->
        <div v-if="loading" class="loading-container">
          <ion-spinner name="crescent"></ion-spinner>
          <p>Loading leaderboard...</p>
        </div>

        <!-- 排行榜列表 -->
        <div v-else>
          <ion-card>
            <ion-card-content>
              <div class="leaderboard-header">
                <h2>
                  <ion-icon name="trophy-outline" class="me-2"></ion-icon>
                  Balance Rankings
                </h2>
                <p class="leaderboard-subtitle">Students ranked by current balance</p>
              </div>

              <ion-list>
                <ion-item 
                  v-for="(student, index) in students" 
                  :key="student.user_id"
                  :class="{ 'current-user-item': student.user_id === user.user_id }"
                  class="leaderboard-item"
                >
                  <div slot="start" class="rank-display">
                    <ion-badge 
                      :color="getRankBadgeColor(student.rank)" 
                      class="rank-badge-large"
                    >
                      <ion-icon :name="getRankIcon(student.rank)"></ion-icon>
                      {{ student.rank }}
                    </ion-badge>
                  </div>

                  <ion-label>
                    <div class="student-info">
                      <h3 class="student-name">{{ student.username }}</h3>
                      <p class="student-id">ID: {{ student.user_id }}</p>
                    </div>
                  </ion-label>

                  <div slot="end" class="balance-display">
                    <ion-text :color="student.user_id === user.user_id ? 'primary' : 'dark'">
                      <h2 class="balance-amount">¥{{ formatPrice(student.balance) }}</h2>
                    </ion-text>
                    <p class="balance-label">Balance</p>
                  </div>
                </ion-item>
              </ion-list>
            </ion-card-content>
          </ion-card>

          <!-- 空状态 -->
          <div v-if="students.length === 0" class="empty-state">
            <ion-icon name="trophy-outline" class="empty-icon"></ion-icon>
            <h3>No rankings available</h3>
            <p>Start earning rewards to appear on the leaderboard!</p>
          </div>
        </div>

        <!-- 刷新按钮 -->
        <div class="refresh-section">
          <ion-button 
            expand="block" 
            fill="outline" 
            @click="loadLeaderboard"
            :disabled="loading"
          >
            <ion-icon name="refresh-outline" slot="start"></ion-icon>
            {{ loading ? 'Refreshing...' : 'Refresh Rankings' }}
          </ion-button>
        </div>
      </div>

      <!-- 警告对话框 -->
      <ion-alert
        :is-open="showAlert"
        :message="alertMessage"
        :buttons="['OK']"
        @didDismiss="showAlert = false"
      ></ion-alert>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.leaderboard-container {
  max-width: 100%;
}

.current-user-card {
  margin-bottom: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.current-user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.user-rank .rank-badge {
  font-size: 1.2rem;
  padding: 8px 12px;
}

.user-details h3 {
  margin: 0 0 5px 0;
  font-size: 1.3rem;
  font-weight: 600;
}

.user-balance {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 700;
  opacity: 0.9;
}

.user-status {
  margin-left: auto;
}

.loading-container {
  text-align: center;
  padding: 40px 20px;
}

.loading-container ion-spinner {
  margin-bottom: 15px;
}

.leaderboard-header {
  text-align: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #f0f0f0;
}

.leaderboard-header h2 {
  margin: 0 0 5px 0;
  color: #333;
  font-weight: 600;
}

.leaderboard-subtitle {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.leaderboard-item {
  --padding-start: 16px;
  --padding-end: 16px;
  --padding-top: 12px;
  --padding-bottom: 12px;
  margin-bottom: 8px;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.leaderboard-item:hover {
  background: #f8f9fa;
  transform: translateX(5px);
}

.current-user-item {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border: 2px solid #667eea;
}

.rank-display {
  display: flex;
  align-items: center;
  margin-right: 15px;
}

.rank-badge-large {
  font-size: 1rem;
  padding: 8px 12px;
  min-width: 50px;
  text-align: center;
}

.student-info {
  flex: 1;
}

.student-name {
  margin: 0 0 4px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
}

.student-id {
  margin: 0;
  font-size: 0.85rem;
  color: #666;
}

.balance-display {
  text-align: right;
}

.balance-amount {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 700;
}

.balance-label {
  margin: 0;
  font-size: 0.8rem;
  color: #666;
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

.refresh-section {
  margin-top: 20px;
  padding: 0 10px;
}

.refresh-section ion-button {
  --border-radius: 12px;
  font-weight: 600;
}
</style>
