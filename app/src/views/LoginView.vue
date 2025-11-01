<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/mockApi'
import { useRouter } from 'vue-router'
import { useUser } from '../store/user'
import { 
  IonPage, 
  IonHeader, 
  IonToolbar, 
  IonTitle, 
  IonContent, 
  IonItem, 
  IonInput, 
  IonButton, 
  IonText, 
  IonNote,
  IonSpinner,
  IonIcon,
  IonLabel
} from '@ionic/vue'

const router = useRouter()
const user = useUser()
const username = ref('')
const password = ref('')
const msg = ref('')
const isLoading = ref(false)

async function doLogin() {
  if (isLoading.value) return
  
  try {
    isLoading.value = true
    msg.value = ''
    
    console.log('Starting login, username:', username.value, 'password:', password.value)
    const result = await api.login(username.value, password.value)
    console.log('Login API returned result:', result)
    
    if (result.ok) {
      console.log('Login successful, user ID:', result.user_id)
      user.set({ user_id: result.user_id, username: username.value })
      
      // 登录成功后初始化余额和交易记录
      try {
        console.log('Starting to get balance, user ID:', result.user_id)
        const balanceResult = await api.balance(result.user_id)
        console.log('Balance API returned result:', balanceResult)
        user.updateBalance(balanceResult.balance, balanceResult.recent)
        console.log('Balance updated successfully')
      } catch (error) {
        console.error('Failed to initialize balance:', error)
      }
      
      msg.value = 'Login successful!'
      
      setTimeout(() => {
        router.replace('/scan')
      }, 1000)
    } else {
      console.log('Login failed, result:', result)
      msg.value = 'Incorrect username or password'
    }
  } catch (error: any) {
    console.error('Error occurred during login:', error)
    msg.value = error.message || 'Login failed'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>Login</ion-title>
      </ion-toolbar>
    </ion-header>
    
    <ion-content class="ion-padding">
      <div class="login-container">
        <div class="logo-section">
          <div class="logo">🎯</div>
          <h1>ClassMint</h1>
          <p>QR Code Reward System</p>
        </div>
        
        <div class="form-section">
          <ion-item class="form-item">
            <ion-label position="stacked">Username</ion-label>
            <ion-input 
              v-model="username" 
              placeholder="Please enter username" 
              class="custom-input"
            />
          </ion-item>
          
          <ion-item class="form-item">
            <ion-label position="stacked">Password</ion-label>
            <ion-input 
              v-model="password" 
              type="password" 
              placeholder="Please enter password" 
              class="custom-input"
            />
          </ion-item>
          
          <ion-button 
            expand="block" 
            @click="doLogin" 
            color="primary"
            class="login-btn"
            :disabled="isLoading"
          >
            <ion-spinner v-if="isLoading" name="crescent"></ion-spinner>
            {{ isLoading ? 'Logging in...' : 'Login' }}
          </ion-button>
          
          <ion-text color="danger" v-if="msg" class="error-msg">
            {{ msg }}
          </ion-text>
          
          <div class="demo-info">
            <ion-note>
              <ion-icon name="information-circle-outline"></ion-icon>
              Please contact your teacher for account credentials
            </ion-note>
          </div>
        </div>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.login-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
}

.logo-section {
  text-align: center;
  margin: 40px 0 60px 0;
}

.logo {
  font-size: 80px;
  margin-bottom: 20px;
}

.logo-section h1 {
  color: #3880ff;
  font-size: 32px;
  font-weight: bold;
  margin: 0 0 10px 0;
}

.logo-section p {
  color: #666;
  font-size: 16px;
  margin: 0;
}

.form-section {
  flex: 1;
}

.form-item {
  margin-bottom: 20px;
  --border-radius: 12px;
  --background: #f8f9fa;
  --border-color: transparent;
}

.form-item:focus-within {
  --background: #ffffff;
  --border-color: #3880ff;
  --border-width: 2px;
}

.custom-input {
  --padding-start: 16px;
  --padding-end: 16px;
  --padding-top: 12px;
  --padding-bottom: 12px;
  font-size: 16px;
}

.login-btn {
  margin: 30px 0 20px 0;
  --border-radius: 12px;
  --padding-top: 16px;
  --padding-bottom: 16px;
  font-size: 18px;
  font-weight: 600;
}

.error-msg {
  display: block;
  text-align: center;
  margin: 20px 0;
  font-size: 14px;
}

.demo-info {
  text-align: center;
  margin-top: 30px;
}

.demo-info ion-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
}

.demo-info ion-icon {
  font-size: 16px;
  color: #3880ff;
}
</style>