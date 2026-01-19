<template>
  <div class="task-real-time-preview">
    <!-- Ask User 问答弹窗 -->
    <el-dialog
      v-model="showQuestionDialog"
      title="需要您的帮助"
      width="600px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
      class="question-dialog"
    >
      <div class="question-content">
        <div class="question-icon">
          <el-icon :size="48" color="var(--warning-color)">
            <QuestionFilled />
          </el-icon>
        </div>
        
        <p class="question-text">{{ pendingQuestion?.question }}</p>
        
        <!-- 有选项时显示单选 -->
        <el-radio-group
          v-if="pendingQuestion?.options && pendingQuestion.options.length > 0"
          v-model="userSelection"
          class="options-group"
        >
          <el-radio
            v-for="(option, index) in pendingQuestion.options"
            :key="index"
            :label="option"
            class="option-item"
            border
          >
            {{ option }}
          </el-radio>
        </el-radio-group>
        
        <!-- 无选项时显示文本输入 -->
        <el-input
          v-else
          v-model="userInput"
          type="textarea"
          :rows="4"
          placeholder="请输入您的回答"
          maxlength="500"
          show-word-limit
          class="answer-input"
        />
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="cancelTask" :loading="isSubmitting">
            取消任务
          </el-button>
          <el-button
            type="primary"
            @click="submitAnswer"
            :loading="isSubmitting"
            :disabled="!canSubmit"
          >
            {{ isSubmitting ? '提交中...' : '提交答案' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-card v-if="currentTask" shadow="never" class="unified-card">
      <template #header>
        <div class="card-header-unified">
          <div class="card-title-content">
            <el-icon><Document /></el-icon>
            <span class="card-title-text">任务详情</span>
          </div>
          <div class="card-actions">
            <el-tag :type="getStatusType(currentTask.status)">
              {{ getStatusText(currentTask.status) }}
            </el-tag>
            <el-button
              v-if="currentTask.status === 'running'"
              type="warning"
              size="small"
              @click="cancelTask"
              :loading="isCancelling"
            >
              取消任务
            </el-button>
          </div>
        </div>
      </template>

      <!-- 标签页 -->
      <el-tabs v-model="activeTab" type="border-card" class="fixed-height-tabs">
        <!-- 步骤详情标签页 -->
        <el-tab-pane label="步骤详情" name="steps">
          <div class="steps-content scrollable-content">
            <el-timeline v-if="steps.length > 0">
              <el-timeline-item
                v-for="(step, index) in steps"
                :key="index"
                :timestamp="formatTime(step.timestamp)"
                :color="getStepColor(step)"
                placement="top"
              >
                <el-card shadow="never" class="step-card" :class="{ 'step-animating': step.isNew, 'answer-step': isAnswerAction(step) }">
                  
                  <!-- Answer 动作特殊显示 -->
                  <el-alert
                    v-if="isAnswerAction(step)"
                    title="AI 回答"
                    type="success"
                    :closable="false"
                    class="answer-alert"
                  >
                    <div class="answer-content">
                      <p>{{ getAnswerText(step) }}</p>
                    </div>
                  </el-alert>
                  
                  <!-- 普通步骤 -->
                  <div v-else>
                    <!-- 思考过程 -->
                    <div v-if="step.thinking" class="step-section step-thinking">
                      <div class="section-title">
                        <el-icon><ChatDotRound /></el-icon>
                        <strong>思考</strong>
                      </div>
                      <div class="section-content">{{ getTruncatedThinking(step.thinking) }}</div>
                    </div>

                    <!-- 执行动作 -->
                    <div v-if="step.action" class="step-section step-action">
                      <div class="section-title">
                        <el-icon><VideoPlay /></el-icon>
                        <strong>动作</strong>
                      </div>
                      <div class="section-content">{{ formatAction(step.action) }}</div>
                    </div>

                    <!-- 观察结果 -->
                    <div v-if="step.observation" class="step-section step-observation">
                      <div class="section-title">
                        <el-icon><View /></el-icon>
                        <strong>观察</strong>
                      </div>
                      <div class="section-content">{{ step.observation }}</div>
                    </div>

                    <!-- 截图 -->
                    <div v-if="step.screenshot" class="step-screenshot">
                      <el-image
                        :src="getScreenshotUrl(step.screenshot)"
                        fit="contain"
                        class="screenshot-thumbnail"
                        :preview-src-list="[getScreenshotUrl(step.screenshot)]"
                      />
                    </div>

                    <!-- 步骤状态 -->
                    <div class="step-footer">
                      <el-tag 
                        :type="getStepStatusType(step)" 
                        size="small"
                      >
                        {{ getStepStatusText(step) }}
                      </el-tag>
                      <span v-if="step.duration_ms" class="step-meta">
                        耗时: {{ (step.duration_ms / 1000).toFixed(2) }}s
                      </span>
                      <span v-if="step.tokens_used" class="step-meta">
                        Token: {{ step.tokens_used.total_tokens || 0 }}
                      </span>
                    </div>
                  </div>
                </el-card>
              </el-timeline-item>

              <!-- 加载中指示器 -->
              <el-timeline-item v-if="currentTask.status === 'running'" color="var(--primary-color)">
                <div class="loading-indicator">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>执行中...</span>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无步骤记录">
              <template #image>
                <el-icon :size="80" color="var(--text-tertiary)">
                  <Document />
                </el-icon>
              </template>
            </el-empty>
          </div>
        </el-tab-pane>        
        <!-- 任务统计标签页 -->
        <el-tab-pane label="任务统计" name="stats">
          <div class="content-section scrollable-content">
            <div class="task-stats">
              <el-statistic title="已执行步骤" :value="steps.length" />
              <el-statistic title="总Token消耗" :value="totalTokens" />
              <el-statistic 
                v-if="currentTask.started_at" 
                title="已用时" 
                :value="elapsedTime" 
                suffix="秒"
              />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 空状态 -->
    <el-empty v-else description="暂无正在执行的任务">
      <template #image>
        <el-icon :size="80" color="var(--text-tertiary)">
          <Document />
        </el-icon>
      </template>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document,
  Collection,
  Checked,
  QuestionFilled,
  ChatDotRound,
  VideoPlay,
  View,
  Loading
} from '@element-plus/icons-vue'
import { taskApi } from '@/api'
import { marked } from 'marked'

const props = defineProps({
  taskId: {
    type: String,
    default: null
  }
})

// 响应式数据
const activeTab = ref('steps')
const currentTask = ref(null)
const steps = ref([])
const isCancelling = ref(false)
const isSubmitting = ref(false)
const elapsedTime = ref(0)
const pollingTimer = ref(null)
const pollingInterval = 1000

// Ask User 相关
const showQuestionDialog = ref(false)
const pendingQuestion = ref(null)
const userSelection = ref('')
const userInput = ref('')

// API基础URL
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''

// 计算总Token
const totalTokens = computed(() => {
  return steps.value.reduce((sum, step) => {
    return sum + (step.tokens_used?.total_tokens || 0)
  }, 0)
})

// Markdown渲染
const renderedTodos = computed(() => {
  if (!currentTask.value?.todos) return ''
  return marked(currentTask.value.todos, {
    breaks: true,
    gfm: true
  })
})

// 检查是否可以提交
const canSubmit = computed(() => {
  if (pendingQuestion.value?.options && pendingQuestion.value.options.length > 0) {
    return userSelection.value !== ''
  } else {
    return userInput.value.trim() !== ''
  }
})

let elapsedTimer = null

// 获取截图URL
function getScreenshotUrl(path, size = 'small') {
  if (!path) return ''
  
  console.log('[TaskRealTimePreview] Building screenshot URL:', { path, size, apiBaseUrl })
  
  // 如果是完整URL，直接返回
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  
  // 处理路径格式
  let cleanPath = path
  
  // 移除可能的 "data/screenshots/" 前缀
  if (cleanPath.startsWith('data/screenshots/')) {
    cleanPath = cleanPath.replace('data/screenshots/', '')
  }
  // 移除可能的 "data/" 前缀
  else if (cleanPath.startsWith('data/')) {
    cleanPath = cleanPath.replace('data/', '')
  }
  // 移除可能的 "screenshots/" 前缀
  else if (cleanPath.startsWith('screenshots/')) {
    cleanPath = cleanPath.replace('screenshots/', '')
  }
  
  console.log('[TaskRealTimePreview] Clean path:', cleanPath)
  
  // 路径格式：tasks/{task_id}/steps/step_001_medium.jpg
  // 需要替换尺寸：medium -> small/medium/ai/original
  
  // 提取基础路径和原始尺寸
  const match = cleanPath.match(/^(.+)_(small|medium|ai|thumbnail|original)\.(jpg|png|jpeg)$/i)
  
  if (match) {
    const [, basePath, currentSize, ext] = match
    // basePath: "tasks/abc123/steps/step_001"
    
    // 如果请求的尺寸与当前尺寸相同，直接使用
    let targetSize = size
    if (size === 'medium' && currentSize === 'ai') {
      // 预览大图时使用 medium，如果当前是 ai，则保持 ai
      targetSize = 'ai'
    }
    
    // 构建新URL
    const finalUrl = `${apiBaseUrl}/api/v1/screenshots/${basePath}_${targetSize}.${ext}`
    console.log('[TaskRealTimePreview] Output:', finalUrl)
    return finalUrl
  }
  
  // 如果路径格式不符合预期，尝试直接拼接（兜底）
  console.warn('[TaskRealTimePreview] Path format unexpected, using fallback:', cleanPath)
  
  // 检查是否已经包含尺寸后缀
  if (/_(?:small|medium|ai|thumbnail|original)\.(jpg|png|jpeg)$/i.test(cleanPath)) {
    // 已有尺寸后缀，直接使用
    return `${apiBaseUrl}/api/v1/screenshots/${cleanPath}`
  }
  
  // 没有尺寸后缀，添加一个
  const fallbackUrl = `${apiBaseUrl}/api/v1/screenshots/${cleanPath.replace(/\.(jpg|png|jpeg)$/i, `_${size}.$1`)}`
  console.log('[TaskRealTimePreview] Fallback output:', fallbackUrl)
  return fallbackUrl
}

// 截断思考内容
function getTruncatedThinking(thinking) {
  if (!thinking) return ''
  const maxLength = 200
  if (thinking.length <= maxLength) {
    return thinking
  }
  return thinking.substring(0, maxLength) + '...'
}

// 检查是否是 answer 动作
function isAnswerAction(step) {
  if (typeof step.action === 'object' && step.action.action === 'answer') {
    return true
  }
  if (typeof step.action === 'string') {
    try {
      const parsed = JSON.parse(step.action)
      return parsed.action === 'answer'
    } catch {
      return false
    }
  }
  return false
}

// 提取 answer 文本
function getAnswerText(step) {
  if (typeof step.action === 'object') {
    return step.action.answer || step.observation || '（无回答内容）'
  }
  if (typeof step.action === 'string') {
    try {
      const parsed = JSON.parse(step.action)
      return parsed.answer || step.observation || '（无回答内容）'
    } catch {
      return step.observation || '（解析失败）'
    }
  }
  return '（未知格式）'
}

// 格式化动作显示
function formatAction(action) {
  if (!action) return ''
  
  if (typeof action === 'string') {
    return action
  }
  
  if (typeof action === 'object') {
    try {
      const actionType = action.action || action.type || 'Unknown'
      const details = []
      
      for (const [key, value] of Object.entries(action)) {
        if (key !== 'action' && key !== 'type' && key !== '_metadata') {
          details.push(`${key}: ${JSON.stringify(value)}`)
        }
      }
      
      if (details.length > 0) {
        return `${actionType} - ${details.join(', ')}`
      }
      return actionType
    } catch (e) {
      return JSON.stringify(action, null, 2)
    }
  }
  
  return String(action)
}

// 分类颜色映射
function getCategoryColor(category) {
  const colorMap = {
    'financial': 'danger',
    'personal': 'success',
    'product': 'warning',
    'general': 'info'
  }
  return colorMap[category] || 'info'
}

// 格式化时间
function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN')
}

// 格式化时间戳（带日期）
function formatTimestamp(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 获取状态类型
function getStatusType(status) {
  const types = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
    waiting_for_user: 'warning'
  }
  return types[status] || 'info'
}

// 获取状态文本
function getStatusText(status) {
  const texts = {
    pending: '等待中',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    waiting_for_user: '等待回答'
  }
  return texts[status] || status
}

// 获取步骤颜色
function getStepColor(step) {
  // 根据步骤状态返回颜色
  if (step.status === 'running') return 'var(--primary-color)'
  if (step.status === 'completed' || step.success === true) return 'var(--success-color)'
  if (step.status === 'failed' || step.success === false) return 'var(--error-color)'
  // 默认返回主色（进行中）
  return 'var(--primary-color)'
}

// 获取步骤状态类型
function getStepStatusType(step) {
  // 根据步骤状态返回Element Plus标签类型
  if (step.status === 'running') return 'warning'
  if (step.status === 'completed' || step.success === true) return 'success'
  if (step.status === 'failed' || step.success === false) return 'danger'
  // 默认返回warning（进行中）
  return 'warning'
}

// 获取步骤状态文本
function getStepStatusText(step) {
  // 优先使用status字段，其次使用success字段
  if (step.status === 'running') return '⏳ 执行中'
  if (step.status === 'completed' || step.success === true) return '✓ 成功'
  if (step.status === 'failed' || step.success === false) return '✗ 失败'
  // 默认显示为执行中
  return '⏳ 执行中'
}

// 加载任务
async function loadTask() {
  if (!props.taskId) {
    console.log('[TaskRealTimePreview] No taskId provided')
    return
  }
  
  try {
    console.log('[TaskRealTimePreview] Loading task:', props.taskId)
    currentTask.value = await taskApi.get(props.taskId)
 console.log(' [TaskRealTimePreview] Task loaded:', currentTask.value)     
    const stepsData = await taskApi.getSteps(props.taskId)
 console.log(' [TaskRealTimePreview] Steps loaded:', stepsData)     
    if (stepsData.steps && Array.isArray(stepsData.steps)) {
      steps.value = stepsData.steps
 console.log(' [TaskRealTimePreview] Steps set:', steps.value.length)     }
  } catch (error) {
 console.error(' [TaskRealTimePreview] Failed to load task:', error)   }
}

// 取消任务
async function cancelTask() {
  if (!currentTask.value) return
  
  isCancelling.value = true
  try {
    await taskApi.cancel(currentTask.value.task_id)
    ElMessage.success('任务已取消')
    currentTask.value.status = 'cancelled'
    showQuestionDialog.value = false
  } catch (error) {
    ElMessage.error('取消任务失败: ' + error.message)
  } finally {
    isCancelling.value = false
  }
}

// 提交答案
async function submitAnswer() {
  const answer = userSelection.value || userInput.value.trim()
  if (!answer) {
    ElMessage.warning('请输入或选择一个答案')
    return
  }
  
  isSubmitting.value = true
  try {
    await taskApi.submitAnswer(props.taskId, answer)
    ElMessage.success('答案已提交')
    showQuestionDialog.value = false
    
    // 刷新任务状态
    await loadTask()
  } catch (error) {
    ElMessage.error('提交答案失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSubmitting.value = false
  }
}

// 启动计时器
function startElapsedTimer() {
  if (elapsedTimer) return
  
  elapsedTimer = setInterval(() => {
    if (currentTask.value?.started_at && currentTask.value.status === 'running') {
      const start = new Date(currentTask.value.started_at)
      const now = new Date()
      elapsedTime.value = ((now - start) / 1000).toFixed(0)
    }
  }, 1000)
}

// 停止计时器
function stopElapsedTimer() {
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
}

// 启动轮询
function startPolling() {
  if (pollingTimer.value) return
  
 console.log(' [TaskRealTimePreview] Starting polling for task:', props.taskId)   
  pollingTimer.value = setInterval(async () => {
    if (!props.taskId) {
      stopPolling()
      return
    }
    
    try {
      const task = await taskApi.get(props.taskId)
      
      if (currentTask.value) {
        currentTask.value.status = task.status
        currentTask.value.result = task.result
        currentTask.value.error = task.error
        currentTask.value.important_content = task.important_content
        currentTask.value.todos = task.todos
        currentTask.value.pending_question = task.pending_question
      }
      
      const stepsData = await taskApi.getSteps(props.taskId)
      if (stepsData.steps && Array.isArray(stepsData.steps)) {
        if (stepsData.steps.length > steps.value.length) {
 console.log(` [TaskRealTimePreview] New steps detected: ${stepsData.steps.length - steps.value.length}`)           
          const newSteps = stepsData.steps.slice(steps.value.length)
          newSteps.forEach(step => {
            step.isNew = true
            setTimeout(() => {
              step.isNew = false
            }, 1000)
          })
          
          steps.value = stepsData.steps
        }
      }
      
      if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
        console.log('[TaskRealTimePreview] Task finished, stopping polling')
        stopPolling()
        stopElapsedTimer()
      }
    } catch (error) {
 console.error(' [TaskRealTimePreview] Polling error:', error)     }
  }, pollingInterval)
}

// 停止轮询
function stopPolling() {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
 console.log(' [TaskRealTimePreview] Polling stopped')   }
}

// 监听任务状态变化
watch(() => currentTask.value?.status, (newStatus, oldStatus) => {
  if (newStatus === 'waiting_for_user' && currentTask.value?.pending_question) {
    pendingQuestion.value = currentTask.value.pending_question
    showQuestionDialog.value = true
    userSelection.value = ''
    userInput.value = ''
  }
  
  if (oldStatus === 'waiting_for_user' && newStatus === 'running') {
    showQuestionDialog.value = false
    ElMessage.success('答案已提交，任务继续执行')
  }
})

// 监听 taskId 变化，自动重新加载任务
watch(() => props.taskId, async (newTaskId, oldTaskId) => {
 console.log(' [TaskRealTimePreview] taskId changed:', oldTaskId, '→', newTaskId)   
  stopPolling()
  
  if (newTaskId && newTaskId !== oldTaskId) {
    steps.value = []
    elapsedTime.value = 0
    await loadTask()
    stopElapsedTimer()
    startElapsedTimer()
    
    if (currentTask.value && currentTask.value.status === 'running') {
      startPolling()
    }
  }
}, { immediate: false })

onMounted(async () => {
  console.log('[TaskRealTimePreview] Component mounted, taskId:', props.taskId)
  await loadTask()
  
  if (currentTask.value && currentTask.value.status === 'running') {
    startPolling()
  }
  
  startElapsedTimer()
})

onUnmounted(() => {
  stopPolling()
  stopElapsedTimer()
})
</script>

<style scoped>
/* ============================================
   设计系统规范样式
   ============================================ */

.task-real-time-preview {
  height: 100%;
  overflow-y: auto;
  padding: 0;
}

/* 统一卡片样式（必需）*/
.unified-card {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-large);
  box-shadow: var(--shadow-light);
  transition: all 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.unified-card:hover {
  box-shadow: var(--shadow-base);
}

.unified-card :deep(.el-card__header) {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-light);
  padding: var(--space-lg);
  border-radius: var(--radius-large) var(--radius-large) 0 0;
  flex-shrink: 0;
}

.unified-card :deep(.el-card__body) {
  padding: 0;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 卡片头部 */
.card-header-unified {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: var(--space-md);
}

.card-title-content {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.card-title-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-actions {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
}

/* 标签页 */
.fixed-height-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.fixed-height-tabs :deep(.el-tabs__content) {
  flex: 1;
 overflow: visible; /* 让子元素自己处理滚动 */   padding: 0;
}

.fixed-height-tabs :deep(.el-tab-pane) {
 height: auto; /* 自动高度,让内部的 steps-content 控制滚动 */   overflow: visible;
}

/* 可滚动内容区域 */
.scrollable-content {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--space-lg);
 /* 确保滚动条样式美观 */   scrollbar-width: thin;
  scrollbar-color: var(--border-base) transparent;
}

.scrollable-content::-webkit-scrollbar {
  width: 6px;
}

.scrollable-content::-webkit-scrollbar-track {
  background: transparent;
}

.scrollable-content::-webkit-scrollbar-thumb {
  background-color: var(--border-base);
  border-radius: 3px;
}

.scrollable-content::-webkit-scrollbar-thumb:hover {
  background-color: var(--border-dark);
}

.unified-card :deep(.el-tabs) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.tab-badge {
  margin-left: var(--space-xs);
}

/* 内容区域 */
.steps-content {
 max-height: 600px; /* 恢复旧版本的简单方案 */   overflow-y: auto;
  overflow-x: hidden;
  padding: var(--space-lg);
}

.content-section {
  padding: var(--space-lg);
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 步骤卡片样式 */
.step-card {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-base);
  box-shadow: none;
  transition: all 0.3s ease;
  padding: var(--space-md);
}

.step-card:hover {
  border-color: var(--border-base);
}

/* Answer 步骤高亮 */
.answer-step {
  border-color: var(--success-color);
  background: var(--success-bg);
}

.answer-alert {
  margin: 0;
}

.answer-content {
  padding: var(--space-sm) 0;
}

.answer-content p {
  margin: 0;
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
  font-weight: 500;
}

/* 步骤区块 */
.step-section {
  margin-bottom: var(--space-md);
  padding: var(--space-md);
  border-radius: var(--radius-base);
  border-left: 3px solid;
}

.step-section:last-child {
  margin-bottom: 0;
}

.step-thinking {
  background: var(--info-bg);
  border-left-color: var(--primary-color);
}

.step-action {
  background: var(--success-bg);
  border-left-color: var(--success-color);
}

.step-observation {
  background: var(--error-bg);
  border-left-color: var(--error-color);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: var(--space-sm);
}

.section-content {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 截图 */
.step-screenshot {
  margin-top: var(--space-md);
  text-align: center;
}

.screenshot-thumbnail {
  width: 100%;
  max-width: 300px;
  border-radius: var(--radius-base);
  border: 1px solid var(--border-light);
}

/* 步骤页脚 */
.step-footer {
  margin-top: var(--space-md);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 12px;
  color: var(--text-tertiary);
}

.step-meta {
  padding: 2px var(--space-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-small);
  border: 1px solid var(--border-light);
}

/* 加载指示器 */
.loading-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 14px;
  color: var(--primary-color);
}

/* 步骤动画 */
.step-animating {
  animation: slideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 记录卡片 */
.record-card {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-base);
  box-shadow: none;
  padding: var(--space-md);
}

.record-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.record-reason {
  font-size: 12px;
  color: var(--text-tertiary);
}

.record-content {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
}

/* TODO列表 */
.todos-content {
  padding: var(--space-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-base);
}

.markdown-content {
  line-height: 1.8;
  color: var(--text-primary);
}

.markdown-content :deep(ul) {
  list-style: none;
  padding-left: 0;
}

.markdown-content :deep(li) {
  padding: var(--space-sm) 0;
  border-bottom: 1px solid var(--border-light);
}

.markdown-content :deep(li:last-child) {
  border-bottom: none;
}

.markdown-content :deep(input[type="checkbox"]) {
  margin-right: var(--space-sm);
  transform: scale(1.2);
  cursor: pointer;
}

.markdown-content :deep(li:has(input[checked])) {
  color: var(--text-tertiary);
  text-decoration: line-through;
}

/* 任务统计 */
.task-stats {
  display: flex;
  justify-content: space-around;
  gap: var(--space-lg);
  flex-wrap: wrap;
  padding: var(--space-lg);
}

/* 问答弹窗 */
.question-dialog :deep(.el-dialog__header) {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-light);
  padding: var(--space-lg);
}

.question-dialog :deep(.el-dialog__body) {
  padding: var(--space-xl);
}

.question-dialog :deep(.el-dialog__footer) {
  border-top: 1px solid var(--border-light);
  padding: var(--space-lg);
}

.question-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-lg);
}

.question-icon {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.question-text {
  font-size: 16px;
  line-height: 1.8;
  text-align: center;
  color: var(--text-primary);
  margin: 0;
  max-width: 480px;
}

.options-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  width: 100%;
}

.option-item {
  padding: var(--space-md);
  transition: all 0.3s ease;
}

.option-item:hover {
  border-color: var(--primary-color);
  background-color: var(--bg-tertiary);
}

.option-item :deep(.el-radio__label) {
  font-size: 14px;
  line-height: 1.6;
}

.answer-input {
  width: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
}

/* 空状态 */
:deep(.el-empty) {
  padding: var(--space-xl) 0;
}

:deep(.el-empty__description) {
  font-size: 14px;
  color: var(--text-secondary);
}

/* 响应式 */
@media (max-width: 768px) {
  .card-header-unified {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .card-actions {
    width: 100%;
    justify-content: space-between;
  }
  
  .task-stats {
    flex-direction: column;
  }
  
  .steps-content {
 max-height: 400px; /* 移动端降低最大高度 */   }
}
</style>