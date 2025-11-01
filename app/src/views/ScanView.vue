<script setup lang="ts">
import { api } from '../api/mockApi'
import { useUser } from '../store/user'
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Camera } from '@capacitor/camera'
import { 
  IonPage, 
  IonHeader, 
  IonToolbar, 
  IonTitle, 
  IonContent, 
  IonButton, 
  IonText, 
  IonNote,
  IonIcon,
  IonModal,
  IonSegment,
  IonSegmentButton,
  IonLabel,
  IonCard,
  IonCardHeader,
  IonCardTitle,
  IonCardContent,
  IonList,
  IonItem,
  IonLabel as IonItemLabel,
  IonBadge,
  IonAlert,
  IonToast
} from '@ionic/vue'

let jsQR: any = null

const user = useUser(); 
const router = useRouter();
const msg = ref(''); 
const scanning = ref(false)
const showCameraModal = ref(false)
const cameraStream = ref<MediaStream | null>(null)
const videoElement = ref<HTMLVideoElement | null>(null)
const canvasElement = ref<HTMLCanvasElement | null>(null)
const isCameraActive = ref(false)
const isProcessing = ref(false)
const currentBalance = ref(0)

// 新增：令牌解析相关
const showTokenModal = ref(false)
const parsedToken = ref<any>(null)
const tokenError = ref('')

const toast = (t:string) => { 
  msg.value = t; 
  setTimeout(() => msg.value = '', 3000) 
}

// 修改：支持新的二维码格式解析
const extract = (s:string) => { 
  // 支持两种格式：
  // 1. 完整URL: https://classmint.local/claim?token=CM1.xxx.xxx
  // 2. 纯令牌: CM1.xxx.xxx
  
  console.log('Extracting token from:', s);
  
  if (s.startsWith('https://classmint.local/claim?token=')) {
    // 从URL中提取令牌
    const m = s.match(/[?&]token=([^&]+)/); 
    const result = m ? decodeURIComponent(m[1]) : null;
    console.log('URL extraction result:', result);
    return result;
  } else if (s.startsWith('CM1.')) {
    // 直接是令牌格式
    console.log('Direct token format:', s);
    return s;
  } else if (s && s.length > 3) {
    // 兼容旧格式
    console.log('Legacy format:', s);
    return s;
  }
  console.log('No valid format found');
  return null;
}

// 新增：验证ClassMint令牌签名
const verifyTokenSignature = (token: string): boolean => {
  try {
    const parts = token.split('.');
    if (parts.length !== 3 || parts[0] !== 'CM1') {
      return false;
    }

    const [version, payload_b64, signature_b64] = parts;
    
    // 解码payload
    const payload_bytes = atob(payload_b64 + '=='.slice((4 - payload_b64.length % 4) % 4));
    
    // 解码签名
    const signature_bytes = atob(signature_b64 + '=='.slice((4 - signature_b64.length % 4) % 4));
    
    // 注意：这里需要后端提供验证API，因为前端无法安全存储HMAC密钥
    // 暂时返回true，实际验证应该在后端进行
    console.warn('前端无法验证HMAC签名，需要在后端验证');
    return true;
  } catch (error) {
    console.error('Signature verification failed:', error);
    return false;
  }
}

// 新增：解析ClassMint令牌
const parseClassMintToken = (token: string) => {
  try {
    const parts = token.split('.');
    if (parts.length !== 3 || parts[0] !== 'CM1') {
      throw new Error(`Invalid token format: expected CM1.xxx.xxx, got ${parts.length} parts starting with ${parts[0]}`);
    }

    const [version, payload_b64, signature] = parts;
    
    // 解码载荷数据
    const payload_bytes = atob(payload_b64 + '=='.slice((4 - payload_b64.length % 4) % 4));
    const payload = JSON.parse(payload_bytes);
    
    // 验证必要字段
    if (!payload.amount || !payload.exp || !payload.nonce) {
      throw new Error(`Incomplete token data: missing ${!payload.amount ? 'amount' : ''} ${!payload.exp ? 'exp' : ''} ${!payload.nonce ? 'nonce' : ''}`);
    }
    
    // 检查过期时间
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp < now) {
      const expiredMinutes = Math.floor((now - payload.exp) / 60);
      throw new Error(`Token expired ${expiredMinutes} minutes ago. Please ask teacher to generate a new token.`);
    }
    
    // 注意：签名验证在后端进行，前端只做基本格式检查
    // 移除前端签名验证，避免不必要的错误
    
    return {
      version,
      payload,
      signature,
      originalToken: token, // 保存原始令牌字符串
      amount_yuan: payload.amount / 100,
      expires_at: new Date(payload.exp * 1000).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }),
      is_expired: payload.exp < now,
      description: payload.desc || 'No description'
    };
  } catch (error: any) {
    console.error('Token parsing failed:', error);
    throw new Error(`Invalid token format: ${error.message}`);
  }
}

// 新增：处理扫描到的二维码
const handleScannedQR = async (qrData: string) => {
  try {
    isProcessing.value = true;
    
    // 显示扫描到的原始数据
    msg.value = `Scanned: ${qrData.substring(0, 50)}...`;
    
    // 提取令牌
    const token = extract(qrData);
    console.log('Extracted token:', token);
    
    if (!token) {
      msg.value = `Error: Cannot extract token from: ${qrData.substring(0, 30)}...`;
      throw new Error('Unrecognized QR code format');
    }
    
    msg.value = `Token extracted: ${token.substring(0, 30)}...`;
    
    // 解析令牌
    const parsed = parseClassMintToken(token);
    parsedToken.value = parsed;
    
    // 清除之前的错误消息
    tokenError.value = '';
    
    // 显示令牌信息（不自动领取）
    showTokenModal.value = true;
    
  } catch (error: any) {
    console.error('QR processing error:', error);
    // 显示详细的错误信息
    msg.value = `Error: ${error.message}`;
    // 仅当它是真正的错误时才设置错误消息
    tokenError.value = error.message || 'QR code parsing failed';
    showTokenModal.value = true;
  } finally {
    isProcessing.value = false;
  }
}

// 新增：确认令牌领取
const confirmClaim = async () => {
  try {
    if (!parsedToken.value) {
      throw new Error('Invalid token data');
    }
    
    // 重新构建完整的令牌字符串
    const tokenStr = extractTokenFromParsed(parsedToken.value);
    if (!tokenStr) {
      throw new Error('Cannot reconstruct token');
    }
    
    // 调用API领取
    const result = await api.claim(tokenStr, user.user_id);
    
    // 更新余额
    await getCurrentBalance();
    
    // 强制刷新界面显示
    msg.value = `Claim successful! Received ¥${parsedToken.value.amount_yuan.toFixed(2)}`;
    
    // 显示成功消息，包含Transaction ID
    const txId = result.tx_id || 'Unknown';
    toast(`Claim successful! Received ¥${parsedToken.value.amount_yuan.toFixed(2)} (Transaction ID: ${txId})`);
    
    // 更新消息显示Transaction ID
    msg.value = `Claim successful! Received ¥${parsedToken.value.amount_yuan.toFixed(2)} (Transaction ID: ${txId})`;
    
    // 关闭令牌信息模态框
    showTokenModal.value = false;
    
    // 关闭相机（如果正在扫描）
    if (showCameraModal.value) {
      closeCameraModal();
    }
    
    // 导航到我的页面
    setTimeout(() => {
      router.push('/me');
    }, 1500);
    
  } catch (error: any) {
    // 显示错误消息
    if (error.message.includes('already been used')) {
      toast('This token has already been claimed, cannot claim again');
    } else if (error.message.includes('expired')) {
      toast('This token has expired, cannot claim');
    } else {
      toast(error.message || 'Claim failed');
    }
    
    // 关闭令牌信息模态框
    showTokenModal.value = false;
    
    // 关闭相机（如果正在扫描）
    if (showCameraModal.value) {
      closeCameraModal();
    }
  }
}

// 新增：从解析的令牌数据中提取原始令牌字符串
const extractTokenFromParsed = (parsed: any): string | null => {
  try {
    // 如果parsed包含原始令牌字符串，直接返回
    if (parsed.originalToken) {
      return parsed.originalToken;
    }
    
    // 如果没有原始令牌，返回null
    console.warn('No original token found in parsed data');
    return null;
  } catch (error) {
    console.error('Error extracting token:', error);
    return null;
  }
}

const getCurrentBalance = async () => {
  try {
    const result = await api.balance(user.user_id)
    currentBalance.value = result.balance
    // 同时更新全局状态
    user.updateBalance(result.balance, result.recent)
    return result.balance
  } catch (error) {
    console.error('Failed to get balance:', error)
    return 0
  }
}

const initBalance = async () => {
  await getCurrentBalance()
}

// 使用计算属性从全局状态获取余额
const displayBalance = computed(() => user.balance || currentBalance.value)

const loadJsQR = async () => {
  if (jsQR) return jsQR
  
  try {
    if (typeof window !== 'undefined' && !(window as any).jsQR) {
      const script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js'
      script.onload = () => {
        jsQR = (window as any).jsQR
        console.log('jsQR library loaded successfully')
      }
      script.onerror = () => {
        console.error('jsQR library loading failed')
        toast('Failed to load QR code recognition library')
      }
      document.head.appendChild(script)
      
      return new Promise((resolve) => {
        script.onload = () => {
          jsQR = (window as any).jsQR
          console.log('jsQR library loaded successfully')
          resolve(jsQR)
        }
      })
    } else if ((window as any).jsQR) {
      jsQR = (window as any).jsQR
      return jsQR
    }
    
    return jsQR
  } catch (error) {
    console.error('Failed to load jsQR library:', error)
    toast('Failed to load QR code recognition library')
    return null
  }
}

const startCameraScan = async () => {
  try {
    msg.value = 'Starting camera...'
    
    // 首先请求摄像头权限
    const permissions = await Camera.requestPermissions()
    if (permissions.camera !== 'granted') {
      toast('Camera permission is required')
      msg.value = 'Camera permission is required, please allow the app to use your camera in settings'
      return
    }
    
    // 检查存储权限（Android需要）
    if (permissions.photos !== 'granted') {
      console.warn('Storage permission not granted, but continuing with camera access')
    }
    
    const qrLibrary = await loadJsQR()
    if (!qrLibrary) {
      toast('Failed to load QR code recognition library')
      return
    }
    
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: { 
        facingMode: 'environment',
        width: { ideal: 1280 },
        height: { ideal: 720 }
      } 
    })
    
    cameraStream.value = stream
    showCameraModal.value = true
    
    setTimeout(() => {
      if (videoElement.value) {
        videoElement.value.srcObject = stream
        videoElement.value.play()
        isCameraActive.value = true
        msg.value = 'Camera started, please align the QR code with the screen'
        
        startScanningLoop()
      }
    }, 100)
    
  } catch (error: any) {
    console.error('Failed to start camera:', error)
    if (error.name === 'NotAllowedError') {
      toast('Camera permission is required')
      msg.value = 'Camera permission is required, please allow the app to use your camera in settings'
    } else if (error.name === 'NotFoundError') {
      toast('Camera device not found')
      msg.value = 'Camera device not found, please check if your device camera is working'
    } else {
      toast('Failed to start camera')
      msg.value = `Failed to start camera: ${error.message}`
    }
  }
}

const startScanningLoop = () => {
  if (!isCameraActive.value || !videoElement.value || !canvasElement.value) return
  
  console.log('Starting scanning loop')
  
  const scanFrame = () => {
    if (!isCameraActive.value || isProcessing.value) {
      if (isCameraActive.value && !isProcessing.value) {
        setTimeout(() => {
          startScanningLoop()
        }, 100)
      }
      return
    }
    
    try {
      const video = videoElement.value!
      const canvas = canvasElement.value!
      const ctx = canvas.getContext('2d')!
      
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      
      if (jsQR) {
        let code = null
        
        code = jsQR(imageData.data, imageData.width, imageData.height, {
          inversionAttempts: "attemptBoth",
          maxAttempts: 3,
        })
        
        if (!code) {
          const centerX = Math.floor(imageData.width / 2)
          const centerY = Math.floor(imageData.height / 2)
          const scanSize = Math.min(imageData.width, imageData.height) * 0.6
          
          const startX = Math.max(0, centerX - scanSize / 2)
          const startY = Math.max(0, centerY - scanSize / 2)
          const endX = Math.min(imageData.width, startX + scanSize)
          const endY = Math.min(imageData.height, startY + scanSize)
          
          const centerImageData = ctx.getImageData(startX, startY, endX - startX, endY - startY)
          
          code = jsQR(centerImageData.data, centerImageData.width, centerImageData.height, {
            inversionAttempts: "attemptBoth",
            maxAttempts: 2,
          })
        }
        
        if (!code) {
          const enhancedData = new Uint8ClampedArray(imageData.data)
          for (let i = 0; i < enhancedData.length; i += 4) {
            const gray = (enhancedData[i] + enhancedData[i + 1] + enhancedData[i + 2]) / 3
            const enhanced = Math.min(255, gray * 1.2)
            enhancedData[i] = enhancedData[i + 1] = enhancedData[i + 2] = enhanced
          }
          
          code = jsQR(enhancedData, imageData.width, imageData.height, {
            inversionAttempts: "attemptBoth",
            maxAttempts: 2,
          })
        }
        
        if (code) {
          console.log('QR code detected:', code.data)
          handleScannedQR(code.data)
          return
        }
      }
      
      setTimeout(() => {
        if (isCameraActive.value && !isProcessing.value) {
          requestAnimationFrame(scanFrame)
        }
      }, 20)
      
    } catch (error) {
      console.error('Scanning frame processing failed:', error)
      setTimeout(() => {
        if (isCameraActive.value && !isProcessing.value) {
          requestAnimationFrame(scanFrame)
        }
      }, 100)
    }
  }
  
  scanFrame()
}

const stopCamera = () => {
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach(track => track.stop())
    cameraStream.value = null
  }
  isCameraActive.value = false
  showCameraModal.value = false
  isProcessing.value = false
}

const closeCameraModal = () => {
  stopCamera()
}

onMounted(() => {
  initBalance()
})
</script>

<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>Scan & Claim</ion-title>
      </ion-toolbar>
    </ion-header>
    
    <ion-content class="ion-padding">
      <div class="scan-container">
        <div class="scan-hero">
          <div class="scan-icon">📱</div>
          <h2>Scan QR Code</h2>
          <p>Scan QR codes to claim rewards quickly</p>
          <div class="balance-display">
            <ion-icon name="wallet-outline"></ion-icon>
            <span class="balance-text">Current Balance: {{ (displayBalance/100).toFixed(2) }} yuan</span>
          </div>
        </div>
        
        <div class="scan-section">
          <ion-button 
            expand="block" 
            @click="startCameraScan()" 
            color="primary"
            class="scan-btn"
            size="large"
          >
            <ion-icon name="scan-outline" slot="start"></ion-icon>
            Start Live Scanning
          </ion-button>
          
          <div class="scan-status" v-if="msg">
            <ion-icon 
              :name="msg.includes('success') ? 'checkmark-circle' : 
                     msg.includes('failed') ? 'close-circle' : 'information-circle'" 
              :color="msg.includes('success') ? 'success' : 
                      msg.includes('failed') ? 'danger' : 'medium'"
            ></ion-icon>
            <span>{{ msg }}</span>
          </div>
        </div>
      </div>
    </ion-content>
    
    <ion-modal :is-open="showCameraModal" @did-dismiss="closeCameraModal">
      <ion-header>
        <ion-toolbar>
          <ion-title>Scan & Claim</ion-title>
          <ion-buttons slot="end">
            <ion-button @click="closeCameraModal">
              <ion-icon name="close"></ion-icon>
            </ion-button>
          </ion-buttons>
        </ion-toolbar>
      </ion-header>
      
      <ion-content class="ion-padding">
        <div class="camera-container">
          <div class="camera-preview">
            <video 
              ref="videoElement"
              class="camera-video"
              autoplay
              playsinline
              muted
            ></video>
            
            <div class="scan-frame">
              <div class="scan-corner top-left"></div>
              <div class="scan-corner top-right"></div>
              <div class="scan-corner bottom-left"></div>
              <div class="scan-corner bottom-right"></div>
            </div>
            
            <div class="scan-hint">
              <ion-icon name="scan-outline"></ion-icon>
              <p>Align QR code with scan frame</p>
              <div class="scan-indicator" v-if="isCameraActive && !isProcessing">
                <div class="scan-dots">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </div>
                <p class="scan-text">Scanning...</p>
              </div>
            </div>
          </div>
          
          <canvas 
            ref="canvasElement" 
            style="display: none;"
            width="1280"
            height="720"
          ></canvas>
          
          <div class="camera-controls">
            <ion-button 
              expand="block" 
              @click="closeCameraModal" 
              color="danger"
              fill="outline"
              class="control-btn"
            >
              <ion-icon name="close-outline" slot="start"></ion-icon>
              Close Camera
            </ion-button>
          </div>
          
          <div class="camera-status" v-if="msg">
            <ion-icon 
              :name="msg.includes('success') ? 'checkmark-circle' : 'information-circle'" 
              :color="msg.includes('success') ? 'success' : 'medium'"
            ></ion-icon>
            <span>{{ msg }}</span>
          </div>
        </div>
      </ion-content>
    </ion-modal>

    <!-- Token Info Modal -->
    <ion-modal :is-open="showTokenModal" @did-dismiss="showTokenModal = false">
      <ion-header>
        <ion-toolbar>
          <ion-title>Claim Reward</ion-title>
          <ion-buttons slot="end">
            <ion-button @click="showTokenModal = false">
              <ion-icon name="close"></ion-icon>
            </ion-button>
          </ion-buttons>
        </ion-toolbar>
      </ion-header>
      <ion-content class="ion-padding">
        <ion-card v-if="parsedToken">
          <ion-card-header>
            <ion-card-title>Reward Details</ion-card-title>
          </ion-card-header>
          <ion-card-content>
            <ion-list>
              <ion-item>
                <ion-item-label>Reward Amount</ion-item-label>
                <ion-badge color="success">{{ parsedToken.amount_yuan }} yuan</ion-badge>
              </ion-item>
              <ion-item>
                <ion-item-label>Expiry Time</ion-item-label>
                <ion-badge color="danger">{{ parsedToken.expires_at }}</ion-badge>
              </ion-item>
              <ion-item>
                <ion-item-label>Description</ion-item-label>
                <ion-badge color="info">{{ parsedToken.description }}</ion-badge>
              </ion-item>
            </ion-list>
            <ion-button expand="block" color="primary" @click="confirmClaim">
              Confirm Claim
            </ion-button>
          </ion-card-content>
        </ion-card>
        <!-- Only show error alert when there's an error -->
        <ion-alert
          v-if="tokenError"
          :is-open="showTokenModal && tokenError"
          header="Claim Failed"
          :message="tokenError"
          buttons="Dismiss"
          @did-dismiss="tokenError = ''"
        ></ion-alert>
      </ion-content>
    </ion-modal>
  </ion-page>
</template>

<style scoped>
.scan-container {
  padding: 20px;
  padding-bottom: 100px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100%;
}

.scan-hero {
  text-align: center;
  margin-bottom: 60px;
}

.scan-icon {
  font-size: 80px;
  margin-bottom: 20px;
}

.scan-hero h2 {
  color: #3880ff;
  font-size: 28px;
  font-weight: bold;
  margin: 0 0 15px 0;
}

.scan-hero p {
  color: #666;
  font-size: 16px;
  margin: 0;
}

.balance-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 20px;
  color: #666;
  font-size: 14px;
}

.balance-display ion-icon {
  font-size: 20px;
}

.balance-text {
  font-weight: 500;
}

.scan-section {
  width: 100%;
  max-width: 400px;
}

.scan-btn {
  --border-radius: 16px;
  --padding-top: 20px;
  --padding-bottom: 20px;
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
}

.scan-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 12px;
  margin-top: 20px;
}

.scan-status ion-icon {
  font-size: 20px;
}

.scan-status span {
  color: #666;
  font-size: 14px;
}

.camera-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.camera-preview {
  position: relative;
  flex: 1;
  background: #000;
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 20px;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.scan-frame {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 250px;
  height: 250px;
  border: 2px solid rgba(255, 255, 255, 0.8);
  border-radius: 16px;
}

.scan-corner {
  position: absolute;
  width: 20px;
  height: 20px;
  border: 3px solid #3880ff;
}

.scan-corner.top-left {
  top: -3px;
  left: -3px;
  border-right: none;
  border-bottom: none;
  border-top-left-radius: 8px;
}

.scan-corner.top-right {
  top: -3px;
  right: -3px;
  border-left: none;
  border-bottom: none;
  border-top-right-radius: 8px;
}

.scan-corner.bottom-left {
  bottom: -3px;
  left: -3px;
  border-right: none;
  border-top: none;
  border-bottom-left-radius: 8px;
}

.scan-corner.bottom-right {
  bottom: -3px;
  right: -3px;
  border-left: none;
  border-top: none;
  border-bottom-right-radius: 8px;
}

.scan-hint {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
  color: white;
  background: rgba(0, 0, 0, 0.7);
  padding: 10px 20px;
  border-radius: 20px;
}

.scan-hint ion-icon {
  font-size: 24px;
  margin-bottom: 5px;
  display: block;
}

.scan-hint p {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
}

.scan-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.scan-dots {
  display: flex;
  gap: 5px;
}

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  background-color: #3880ff;
  border-radius: 50%;
  animation: pulse 1.5s infinite ease-in-out;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
.dot:nth-child(3) { animation-delay: 0s; }

@keyframes pulse {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.7; }
  40% { transform: translateY(-10px); opacity: 1; }
}

.scan-text {
  margin: 0;
  font-size: 14px;
  color: white;
  font-weight: 500;
}

.camera-controls {
  margin-bottom: 20px;
}

.control-btn {
  --border-radius: 12px;
  --padding-top: 16px;
  --padding-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
}

.camera-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 12px;
  margin-top: 20px;
}

.camera-status ion-icon {
  font-size: 20px;
}

.camera-status span {
  color: #666;
  font-size: 14px;
}
</style>