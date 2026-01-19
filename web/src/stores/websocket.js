import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useWebSocketStore = defineStore('websocket', () => {
  // 状态
  const ws = ref(null)
  const connected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 10
  const reconnectDelay = ref(1000)
  
  // 实时数据
  const deviceStats = ref(null)
  const taskStats = ref(null)
  const latestUpdate = ref(null)
  
  // 计算属性
  const isConnected = computed(() => connected.value)
  
  // 连接 WebSocket
  function connect() {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected')
      return
    }
    
    // 从环境变量获取 WebSocket 地址
    let wsUrl = import.meta.env.VITE_WS_URL
    
    // 如果环境变量未配置，使用当前域名构建（开发模式回退）
    if (!wsUrl) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      // 根据标准文档：前端域名反向代理方案使用 /ws 路径
      wsUrl = `${protocol}//${window.location.host}/ws`
      console.warn('VITE_WS_URL not configured, using fallback:', wsUrl)
    }
    
    console.log('Connecting to WebSocket:', wsUrl)
    
    try {
      ws.value = new WebSocket(wsUrl)
      
      ws.value.onopen = () => {
        console.log('WebSocket connected')
        connected.value = true
        reconnectAttempts.value = 0
        reconnectDelay.value = 1000
        
        // 订阅状态更新
        send({ type: 'subscribe' })
        
        // 启动心跳
        startHeartbeat()
      }
      
      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleMessage(data)
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }
      
      ws.value.onerror = (error) => {
 console.error(' WebSocket error:', error)       }
      
      ws.value.onclose = () => {
        console.log('🔌 WebSocket disconnected')
        connected.value = false
        stopHeartbeat()
        
        // 尝试重连
        if (reconnectAttempts.value < maxReconnectAttempts) {
          reconnectAttempts.value++
 console.log(` Reconnecting in ${reconnectDelay.value}ms (attempt ${reconnectAttempts.value}/${maxReconnectAttempts})`)           
          setTimeout(() => {
            connect()
          }, reconnectDelay.value)
          
          // 指数退避
          reconnectDelay.value = Math.min(reconnectDelay.value * 2, 30000)
        } else {
 console.error(' Max reconnect attempts reached')         }
      }
    } catch (e) {
      console.error('Failed to create WebSocket:', e)
    }
  }
  
  // 断开连接
  function disconnect() {
    stopHeartbeat()
    
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    
    connected.value = false
  }
  
  // 发送消息
  function send(data) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket not connected')
    }
  }
  
  // 处理消息
  function handleMessage(data) {
    latestUpdate.value = new Date()
    
    switch (data.type) {
      case 'pong':
        // 心跳响应
        break
        
      case 'initial_state':
        console.log('Initial state:', data.data)
        break
        
      case 'device_update':
        deviceStats.value = data.data
        break
        
      case 'task_update':
        taskStats.value = data.data
        break
        
      case 'task_step_update':
        // 任务步骤更新（实时推送）
        console.log('[WebSocket] Task step update received:', data.data)
        // 触发自定义事件，让其他组件监听
        window.dispatchEvent(new CustomEvent('task-step-update', { detail: data.data }))
        console.log('[WebSocket] Custom event dispatched: task-step-update')
        break
        
      case 'task_status_change':
        // 任务状态变化事件（新增）
        console.log('[WebSocket] Task status change received:', data.data)
        window.dispatchEvent(new CustomEvent('task-status-change', { detail: data.data }))
        console.log('[WebSocket] Custom event dispatched: task-status-change')
        break
        
      case 'task_cancelled':
        // 任务取消事件
        console.log('Task cancelled:', data.data)
        window.dispatchEvent(new CustomEvent('task-cancelled', { detail: data.data }))
        break
        
      case 'human_intervention_needed':
        // 人机协同：需要人工干预
        console.log('[WebSocket] Human intervention needed:', data.data)
        window.dispatchEvent(new CustomEvent('human-intervention-needed', { detail: data.data }))
        break
        
      default:
        console.log('Unknown message type:', data.type)
    }
  }
  
  // 心跳机制
  let heartbeatTimer = null
  
  function startHeartbeat() {
    stopHeartbeat()
    
    heartbeatTimer = setInterval(() => {
      send({ type: 'ping' })
    }, 30000) // 30秒心跳
  }
  
  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }
  
  return {
    // 状态
    connected,
    isConnected,
    deviceStats,
    taskStats,
    latestUpdate,
    
    // 方法
    connect,
    disconnect,
    send
  }
})

