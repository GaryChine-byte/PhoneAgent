<template>
  <div class="live-preview-container">
    <!-- 顶部标题栏 - 重新设计 -->
    <div class="preview-header">
      <div class="header-title">
        <span class="card-title">设备预览</span>
        <el-tag v-if="isPreviewActive" type="success" size="small">
          {{ previewMode === 'screenshot' ? '截图模式' : '实时模式' }}
        </el-tag>
        <el-tag v-else type="info" size="small">未开启</el-tag>
      </div>
      
      <div class="header-actions">
        <!-- 开关 -->
        <el-switch
          v-model="isPreviewActive"
          size="large"
          inline-prompt
          active-text="开启"
          inactive-text="关闭"
          @change="togglePreview"
          :loading="isStarting || isStopping"
          :disabled="!selectedDeviceId"
        />
        
        <!-- 观看/控制模式切换 -->
        <el-switch 
          v-model="enableControl" 
          size="large"
          inline-prompt
          active-text="控制"
          inactive-text="观看"
          style="--el-switch-on-color: var(--primary-color);"
          :disabled="!isPreviewActive"
        />
      </div>
    </div>

    <!-- 功能控制栏 - 精简版 -->
    <div class="preview-controls">
      <!-- 设备选择 -->
      <el-select 
        v-model="selectedDeviceId" 
        placeholder="选择设备"
        size="small"
        class="device-select"
        @change="handleDeviceChange"
        :disabled="isPreviewActive"
      >
        <el-option
          v-for="device in devices"
          :key="device.device_id"
          :label="device.name || device.device_id"
          :value="device.device_id"
        >
          <div class="device-option-row">
            <span>{{ device.name || device.device_id }}</span>
            <el-tag :type="getDeviceStatusType(device)" size="small">
              {{ getDeviceStatusText(device) }}
            </el-tag>
          </div>
        </el-option>
      </el-select>
      
      <!-- 设置按钮 -->
      <el-button 
        size="small"
        @click="showSettings"
        :icon="Setting"
        :disabled="!isPreviewActive"
      >
        设置
      </el-button>
      
      <!-- 任务控制 -->
      <el-button 
        size="small" 
        type="danger" 
        plain
        @click="interruptTask" 
        :disabled="!isPreviewActive"
        :icon="CloseBold"
      >
        中断任务
      </el-button>
    </div>

    <!-- 预览区域 - 只包含手机预览 -->
    <div class="preview-content" :class="{ 'active': isPreviewActive }">
      <div v-if="!isPreviewActive" class="preview-placeholder">
        <el-empty description="请选择设备并开启预览">
          <template #image>
            <el-icon :size="80" color="#909399"><Monitor /></el-icon>
          </template>
        </el-empty>
      </div>
      
      <div v-else class="preview-screen-container">
        <div class="preview-screen" :style="phoneScreenStyle">
          <!-- H.264 视频流（替换 MJPEG） -->
          <LivePreviewH264 
            v-if="selectedDeviceId"
            :device-id="selectedDeviceId" 
            :enable-control="enableControl"
            class="h264-video"
          />
          
          <!-- 加载提示 -->
          <div v-if="isLoading" class="loading-overlay">
            <el-icon class="is-loading" :size="40"><Loading /></el-icon>
            <p>正在加载视频流...</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 系统按键区域 - 始终可见 -->
    <div class="system-controls-section">
      <!-- 系统按键 -->
      <div class="system-controls">
        <el-button-group>
          <el-tooltip content="返回键" placement="top">
            <el-button size="large" @click="sendKey('BACK')" :disabled="!enableControl">
              <el-icon><Back /></el-icon>
              <span>返回</span>
            </el-button>
          </el-tooltip>
          <el-tooltip content="Home键" placement="top">
            <el-button size="large" @click="sendKey('HOME')" :disabled="!enableControl">
              <el-icon><HomeFilled /></el-icon>
              <span>主页</span>
            </el-button>
          </el-tooltip>
          <el-tooltip content="多任务" placement="top">
            <el-button size="large" @click="sendKey('RECENTS')" :disabled="!enableControl">
              <el-icon><Menu /></el-icon>
              <span>多任务</span>
            </el-button>
          </el-tooltip>
        </el-button-group>
      </div>
    </div>

    <!-- 底部信息栏 - 简化 -->
    <div class="preview-footer" v-if="isPreviewActive">
      <div class="footer-info">
        <span>{{ selectedDeviceId }}</span>
        <el-divider direction="vertical" />
        <span>1280p · 30fps</span>
        <el-divider direction="vertical" />
        <span :class="latencyClass">{{ latency }}ms</span>
      </div>
    </div>

    <!-- 设置对话框 -->
    <el-dialog v-model="settingsVisible" title="预览设置" width="400px">
      <el-form label-width="80px">
        <el-form-item label="分辨率">
          <el-select v-model="settings.maxSize">
            <el-option label="1920p (高清)" :value="1920" />
            <el-option label="1280p (推荐)" :value="1280" />
            <el-option label="854p (流畅)" :value="854" />
          </el-select>
        </el-form-item>
        <el-form-item label="帧率">
          <el-select v-model="settings.framerate">
            <el-option label="60 FPS" :value="60" />
            <el-option label="30 FPS" :value="30" />
            <el-option label="15 FPS" :value="15" />
          </el-select>
        </el-form-item>
        <el-form-item label="码率">
          <el-input-number v-model="settings.bitrate" :min="1" :max="10" :step="1" />
          <span class="unit-text">Mbps</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" @click="applySettings">应用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  VideoCamera, Monitor, Close, Loading, Back, HomeFilled, 
  Menu, CloseBold, Setting 
} from '@element-plus/icons-vue'
import { request, deviceApi } from '@/api/index'
import LivePreviewH264 from './LivePreviewH264.vue'

// 数据
const devices = ref([])
const selectedDeviceId = ref('')
const selectedDevice = ref(null) // 当前选中的设备完整信息
const isPreviewActive = ref(false)
const enableControl = ref(false)
const isStarting = ref(false)
const isStopping = ref(false)
const isLoading = ref(false)
const streamUrl = ref('')
const latency = ref(0)
const settingsVisible = ref(false)
const deviceScreenResolution = ref(null) // 设备实际屏幕分辨率

// API基础URL
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''

const settings = ref({
  maxSize: 1280,
  framerate: 30,
  bitrate: 4
})

const videoStream = ref(null)

// 计算属性
const latencyClass = computed(() => {
  if (latency.value < 100) return 'latency-good'
  if (latency.value < 300) return 'latency-medium'
  return 'latency-bad'
})

// 动态预览高度 - 根据分辨率调整
const dynamicPreviewHeight = computed(() => {
  const baseHeight = 600
  const resolutionMultiplier = settings.value.maxSize / 1280
  return Math.max(baseHeight, baseHeight * resolutionMultiplier)
})

// 手机屏幕样式 - 根据设备实际分辨率动态调整
const phoneScreenStyle = computed(() => {
  let aspectRatio = 9 / 19.5 // 默认现代手机比例
  
  // 如果有设备实际分辨率，使用实际比例
  if (deviceScreenResolution.value) {
    const [width, height] = deviceScreenResolution.value.split('x').map(Number)
    if (width && height) {
      aspectRatio = width / height
    }
  }
  
  // 基于容器宽度和实际比例计算
  const maxWidth = 380 // 最大宽度限制，保持中右卡片宽度不变
  const baseWidth = 300 // 基础宽度
  
  return {
    width: `${baseWidth}px`,
    maxWidth: `${maxWidth}px`,
    aspectRatio: `${aspectRatio}`
  }
})

// 设备状态判断函数
const getDeviceStatusType = (device) => {
  if (device.status !== 'online') return 'info'
  if (device.frp_connected && device.ws_connected) return 'success'
  if (device.frp_connected && !device.ws_connected) return 'warning'
  return 'info'
}

const getDeviceStatusText = (device) => {
  if (device.status !== 'online') return '离线'
  if (device.frp_connected && device.ws_connected) return '完全连接'
  if (device.frp_connected && !device.ws_connected) return 'FRP连接'
  return '离线'
}

// 加载设备列表
const loadDevices = async () => {
  try {
    const allDevices = await deviceApi.list()
    devices.value = allDevices.filter(d => 
      d.status === 'online' && d.frp_connected && d.ws_connected
    )
    
    // 自动选择第一个在线设备
    if (devices.value.length > 0 && !selectedDeviceId.value) {
      selectedDeviceId.value = devices.value[0].device_id
      // 触发设备切换以加载分辨率信息
      await handleDeviceChange()
    }
  } catch (error) {
    console.error('加载设备列表失败:', error)
  }
}

// 设备切换
const handleDeviceChange = async () => {
  if (isPreviewActive.value) {
    stopPreview()
  }
  
  // 获取选中设备的详细信息
  if (selectedDeviceId.value) {
    try {
      const device = devices.value.find(d => d.device_id === selectedDeviceId.value)
      selectedDevice.value = device
      
      // 获取设备屏幕分辨率
      if (device && device.screen_resolution) {
        deviceScreenResolution.value = device.screen_resolution
        console.log('设备屏幕分辨率:', device.screen_resolution)
      } else {
        // 如果设备信息中没有分辨率，尝试从API获取
        const deviceDetail = await deviceApi.get(selectedDeviceId.value)
        if (deviceDetail && deviceDetail.screen_resolution) {
          deviceScreenResolution.value = deviceDetail.screen_resolution
          console.log('从API获取设备屏幕分辨率:', deviceDetail.screen_resolution)
        }
      }
    } catch (error) {
      console.error('获取设备信息失败:', error)
    }
  }
}

// 切换预览状态
const togglePreview = () => {
  if (isPreviewActive.value) {
    startPreview()
  } else {
    stopPreview()
  }
}

// 开启预览（改用 H.264 API）
const startPreview = async () => {
  if (!selectedDeviceId.value) {
    ElMessage.warning('请先选择设备')
    return
  }
  
  isStarting.value = true
  isLoading.value = true
  
  try {
    // 调用 H.264 API
    await request.post(`/scrcpy/start/${selectedDeviceId.value}`, {
      bitrate: settings.value.bitrate * 1000000,
      max_size: settings.value.maxSize,
      framerate: settings.value.framerate
    })
    
    // 等待更长时间让session完全初始化（避免弹出session错误）
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    isPreviewActive.value = true
    ElMessage.success('H.264 视频流已开启')
    
    // H.264 方案不需要单独的延迟监控（组件内部已实现）
    
  } catch (error) {
    console.error('开启预览失败:', error)
    ElMessage.error('开启预览失败: ' + (error.response?.data?.detail || error.message))
    isLoading.value = false
  } finally {
    isStarting.value = false
    isLoading.value = false  // H.264 组件会自己处理加载状态
  }
}

// 关闭预览（改用 H.264 API）
const stopPreview = async () => {
  isStopping.value = true
  
  try {
 // 调用新的 H.264 停止 API     await request.post(`/scrcpy/stop/${selectedDeviceId.value}`)
    
    isPreviewActive.value = false
    enableControl.value = false
    isLoading.value = false
    
    ElMessage.info('预览已关闭')
  } catch (error) {
    console.error('关闭预览失败:', error)
    ElMessage.error('关闭预览失败')
  } finally {
    isStopping.value = false
  }
}

// 移除 MJPEG 相关的处理函数（H.264 组件内部处理） // 视频流加载、错误、点击等都由 LivePreviewH264.vue 组件处理

// 发送按键
const sendKey = async (key) => {
  const keycodes = {
    'BACK': 4,
    'HOME': 3,
    'RECENTS': 187
  }
  
  try {
    await request.post(`/scrcpy/control/${selectedDeviceId.value}/key`, {
      keycode: keycodes[key],
      action: 'press'
    })
  } catch (error) {
    console.error('发送按键失败:', error)
  }
}

// 中断任务
const interruptTask = async () => {
  try {
    const result = await ElMessageBox.confirm(
      '确定要中断当前任务吗？',
      '确认中断',
      {
        type: 'warning',
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }
    )
    
    if (result) {
      // 获取当前设备的运行中任务
      try {
        const tasksResponse = await request.get('/tasks')
        // API 可能返回数组或 {tasks: [...]} 格式
        const tasksList = Array.isArray(tasksResponse) ? tasksResponse : 
                         (tasksResponse.tasks || tasksResponse.data?.tasks || [])
        const runningTask = tasksList.find(
          t => t.device_id === selectedDeviceId.value && 
               (t.status === 'running' || t.status === 'pending')
        )
        
        if (runningTask) {
          // 调用取消任务 API
          await request.post(`/tasks/${runningTask.task_id}/cancel`)
          ElMessage.success('任务已中断')
        } else {
          ElMessage.info('当前没有运行中的任务')
        }
      } catch (error) {
        console.error('中断任务失败:', error)
        ElMessage.error('中断任务失败: ' + (error.response?.data?.detail || error.message))
      }
    }
  } catch {
    // 用户取消
  }
}

// 延迟监控由 H.264 组件内部实现，这里不需要了 
// 显示设置
const showSettings = () => {
  settingsVisible.value = true
}

// 应用设置
const applySettings = async () => {
  settingsVisible.value = false
  
  if (isPreviewActive.value) {
    ElMessage.info('设置将在下次开启预览时生效')
  }
}

// 分辨率变化处理
// 分辨率调整已移至设置对话框中

// 生命周期
onMounted(() => {
  loadDevices()
  
  // 定期刷新设备列表
  const refreshTimer = setInterval(loadDevices, 10000)
  
  onUnmounted(() => {
    clearInterval(refreshTimer)
    
    // 组件卸载时关闭预览
    if (isPreviewActive.value) {
      stopPreview()
    }
  })
})
</script>

<style scoped>
.live-preview-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 700px; /* 与右侧卡片高度保持一致 */
  background: var(--bg-primary);
  border-radius: var(--radius-large);
  overflow: hidden;
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-light);
  position: relative;
}

/* 顶部标题栏 - 恢复简洁设计 */
.preview-header {
  padding: 14px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-secondary);
  border-radius: var(--radius-large) var(--radius-large) 0 0;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

/* 功能控制栏 - 简洁单行布局 */
.preview-controls {
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-primary);
  flex-wrap: nowrap;
  min-height: 48px;
}

.preview-controls .device-select {
  flex: 1;
  max-width: 200px;
}

/* 预览区域 - 设置合适的最小高度 */
.preview-content {
  flex: 1;
  position: relative;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  padding: 12px;
  margin: 8px;
  border-radius: var(--radius-large);
  overflow: visible;
  min-height: 400px; /* 减少最小高度 */
}

.preview-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 手机预览容器 */
.preview-screen-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  max-width: 100%;
  margin: 0 auto;
}

/* 手机外壳设计 - 优化间隙和圆角 */
.preview-screen {
  width: 100%;
  max-width: 380px;  /* 保持固定宽度，不压缩右侧卡片 */
  /* aspect-ratio 通过 phoneScreenStyle 动态设置 */
  position: relative;
  background: var(--text-primary);
  border-radius: 32px;  /* 现代手机圆角 */
  padding: 16px;
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.15),
    0 8px 16px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  
  /* 手机边框细节 */
  border: 2px solid var(--border-dark);
}

/* 手机屏幕 */
.preview-screen::before {
  content: '';
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 4px;
  background: var(--border-dark);
  border-radius: 2px;
  /* 听筒 */
}

.preview-screen::after {
  content: '';
  position: absolute;
  top: 12px;
  right: 20px;
  width: 8px;
  height: 8px;
  background: var(--text-primary);
  border-radius: 50%;
  /* 前置摄像头 */
}

/* H.264 视频组件样式 */
.h264-video {
  width: 100%;
  height: 100%;
  border-radius: 24px;
  overflow: hidden;
}

.loading-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #fff;
}

.loading-overlay p {
  margin-top: 12px;
  font-size: 14px;
}

/* 系统按键区域 - 独立区域确保可见 */
.system-controls-section {
  background: var(--bg-primary);
  border-top: 1px solid var(--border-light);
  padding: 8px 16px;
}

/* 系统按键 - 去掉外围框，直接显示按钮 */
.system-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0;
  background: transparent;
  margin-top: 0;
}

.system-controls .el-button-group {
  display: flex;
  gap: 16px;
}

.system-controls .el-button {
  min-width: 100px;
  height: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 14px;
  transition: all 0.3s ease;
  background: var(--bg-primary);
  border: 2px solid var(--border-base);
  border-radius: var(--radius-large) !important;
  box-shadow: var(--shadow-light);
}

.system-controls :deep(.el-button) {
  border-radius: var(--radius-large) !important;
}

.system-controls .el-button .el-icon {
  font-size: 24px;
}

.system-controls .el-button span {
  font-size: 13px;
  font-weight: 600;
}

.system-controls .el-button:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: var(--shadow-base);
  border-color: var(--primary-color);
  color: var(--primary-color);
  background: var(--info-bg);
}

.system-controls .el-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: var(--bg-tertiary);
  color: var(--text-disabled);
  border-color: var(--border-base);
}



/* 底部信息栏 - 简化 */
.preview-footer {
  padding: 12px 16px; /* 增加内边距 */
  display: flex;
  justify-content: center;
  align-items: center;
  border-top: 1px solid var(--border-light);
  background: var(--bg-secondary);
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: auto; /* 确保在底部 */
  border-radius: 0 0 var(--radius-large) var(--radius-large);
}

.footer-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.latency-good {
  color: var(--success-color);
}

.latency-medium {
  color: var(--warning-color);
}

.latency-bad {
  color: var(--error-color);
}

/* 新增CSS类 */
.device-option-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.device-select {
  width: 180px;
}

.resolution-select {
  width: 120px;
}

.unit-text {
  margin-left: var(--space-sm);
}

/* 点击反馈动画 */
.click-feedback {
  position: fixed;
  width: 40px;
  height: 40px;
  margin: -20px 0 0 -20px;
  border: 2px solid var(--primary-color);
  border-radius: 50%;
  pointer-events: none;
  animation: click-ripple 0.5s ease-out;
}

@keyframes click-ripple {
  0% {
    transform: scale(0.5);
    opacity: 1;
  }
  100% {
    transform: scale(1.5);
    opacity: 0;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .preview-controls {
    flex-wrap: wrap;
    gap: 12px;
    padding: var(--space-sm) var(--space-md);
  }
  
  .preview-controls .el-select {
    width: 140px !important;
  }
  
  .preview-screen-container {
    max-width: 300px;
  }
  
  .system-controls .el-button {
    min-width: 70px;
    height: 44px;
  }
  
  .system-controls .el-button .el-icon {
    font-size: 18px;
  }
  
  .system-controls .el-button span {
    font-size: 11px;
  }
  
  .system-controls .el-button-group {
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .preview-controls {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .preview-controls > * {
    width: 100% !important;
  }
  
  .preview-screen-container {
    max-width: 280px;
  }
  
  .system-controls .el-button {
    min-width: 60px;
    height: 40px;
  }
  
  .system-controls .el-button .el-icon {
    font-size: 16px;
  }
  
  .system-controls .el-button span {
    font-size: 10px;
  }
  
  .system-controls .el-button-group {
    gap: 8px;
  }
}
</style>

