<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="500px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    center
  >
    <!-- 确认类型 -->
    <div v-if="interventionType === 'confirm'" class="intervention-content">
      <div class="message-box">
        <el-icon class="warning-icon"><Warning /></el-icon>
        <p class="message-text">{{ message }}</p>
      </div>
      
      <div class="timeout-hint" v-if="remainingTime > 0">
        <el-icon><Timer /></el-icon>
        <span>{{ remainingTime }} 秒后自动取消</span>
      </div>
      
      <div class="button-group">
        <el-button
          v-for="(option, index) in options"
          :key="index"
          :type="index === 0 ? 'primary' : 'default'"
          size="large"
          @click="handleConfirm(option)"
        >
          {{ option }}
        </el-button>
      </div>
    </div>
    
    <!-- 输入类型 -->
    <div v-else-if="interventionType === 'input'" class="intervention-content">
      <div class="message-box">
        <el-icon class="info-icon"><Edit /></el-icon>
        <p class="message-text">{{ message }}</p>
      </div>
      
      <div class="timeout-hint" v-if="remainingTime > 0">
        <el-icon><Timer /></el-icon>
        <span>{{ remainingTime }} 秒后自动取消</span>
      </div>
      
      <el-input
        v-model="inputValue"
        :type="inputType"
        :placeholder="placeholder"
        size="large"
        clearable
        @keyup.enter="handleSubmit"
        ref="inputRef"
      />
      
      <div class="button-group">
        <el-button size="large" @click="handleCancel">取消</el-button>
        <el-button type="primary" size="large" @click="handleSubmit">
          提交
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { Warning, Timer, Edit } from '@element-plus/icons-vue'
import { useWebSocketStore } from '@/stores/websocket'

const wsStore = useWebSocketStore()

const visible = ref(false)
const interventionType = ref('') // 'confirm' | 'input'
const message = ref('')
const options = ref([])
const inputType = ref('text')
const placeholder = ref('')
const inputValue = ref('')
const timeout = ref(60)
const remainingTime = ref(0)
const requestId = ref('')
const taskId = ref('')
const inputRef = ref(null)

let countdownTimer = null

const dialogTitle = computed(() => {
 return interventionType.value === 'confirm' ? ' 需要确认' : ' 需要输入' })

// 监听 WebSocket 事件
if (typeof window !== 'undefined') {
  window.addEventListener('human-intervention-needed', handleInterventionRequest)
}

function handleInterventionRequest(event) {
  const data = event.detail
 console.log(' [HumanInterventionDialog] Received intervention request:', data)   
  interventionType.value = data.intervention_type
  message.value = data.message
  requestId.value = data.request_id
  taskId.value = data.task_id
  timeout.value = data.timeout || 60
  
  if (data.intervention_type === 'confirm') {
    options.value = data.options || ['确认', '取消']
  } else if (data.intervention_type === 'input') {
    inputType.value = data.input_type || 'text'
    placeholder.value = data.placeholder || '请输入...'
    inputValue.value = ''
  }
  
  visible.value = true
  remainingTime.value = timeout.value
  
  // 启动倒计时
  startCountdown()
  
  // 如果是输入框，自动聚焦
  if (data.intervention_type === 'input') {
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
}

function startCountdown() {
  stopCountdown()
  
  countdownTimer = setInterval(() => {
    remainingTime.value--
    
    if (remainingTime.value <= 0) {
      stopCountdown()
      handleTimeout()
    }
  }, 1000)
}

function stopCountdown() {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

function handleConfirm(selectedOption) {
  stopCountdown()
  
  // 发送响应给后端
  sendResponse({
    success: true,
    response_type: 'confirm',
    selected_option: selectedOption
  })
  
  visible.value = false
}

function handleSubmit() {
  if (!inputValue.value.trim()) {
    return
  }
  
  stopCountdown()
  
  // 发送响应给后端
  sendResponse({
    success: true,
    response_type: 'input',
    input_value: inputValue.value
  })
  
  visible.value = false
  inputValue.value = ''
}

function handleCancel() {
  stopCountdown()
  
  sendResponse({
    success: false,
    response_type: interventionType.value,
    error: 'User cancelled'
  })
  
  visible.value = false
  inputValue.value = ''
}

function handleTimeout() {
  sendResponse({
    success: false,
    response_type: interventionType.value,
    error: 'Timeout'
  })
  
  visible.value = false
  inputValue.value = ''
}

function sendResponse(response) {
  const message = {
    type: 'human_intervention_response',
    data: {
      request_id: requestId.value,
      task_id: taskId.value,
      ...response
    }
  }
  
  console.log('📤 [HumanInterventionDialog] Sending response:', message)
  wsStore.send(message)
}

// 组件卸载时清理
import { onUnmounted } from 'vue'
onUnmounted(() => {
  stopCountdown()
  if (typeof window !== 'undefined') {
    window.removeEventListener('human-intervention-needed', handleInterventionRequest)
  }
})
</script>

<style scoped>
.intervention-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background-color: var(--el-fill-color-light);
  border-radius: 8px;
}

.warning-icon {
  font-size: 24px;
  color: var(--el-color-warning);
  flex-shrink: 0;
  margin-top: 2px;
}

.info-icon {
  font-size: 24px;
  color: var(--el-color-primary);
  flex-shrink: 0;
  margin-top: 2px;
}

.message-text {
  margin: 0;
  font-size: 16px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  flex: 1;
  word-break: break-word;
}

.timeout-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  color: var(--el-color-info);
  font-size: 14px;
}

.button-group {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 8px;
}

.button-group .el-button {
  flex: 1;
  min-width: 100px;
}

:deep(.el-dialog__header) {
  padding: 20px 20px 10px;
  margin: 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

:deep(.el-dialog__body) {
  padding: 24px;
}

:deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
}
</style>

