import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { deviceApi, pcTaskApi } from '@/api'

export const useDeviceStore = defineStore('device', () => {
  // 状态
  const devices = ref([])
  const loading = ref(false)
  const currentDevice = ref(null)
  
  // 计算属性 - 保持原有逻辑不变
  const onlineDevices = computed(() => 
    devices.value.filter(d => d.status === 'online')
  )
  
  const busyDevices = computed(() => 
    devices.value.filter(d => d.status === 'busy')
  )
  
  const offlineDevices = computed(() => 
    devices.value.filter(d => d.status === 'offline')
  )
  
  const availableDevices = computed(() =>
    devices.value.filter(d => {
      // PC 设备：只要 WebSocket 连接即可（不依赖 FRP）
      if (d.device_type === 'pc') {
        return d.status === 'online' && d.ws_connected && !d.current_task
      }
      // 手机设备：需要 FRP + WebSocket 双连接
      return d.status === 'online' && d.frp_connected && d.ws_connected && !d.current_task
    })
  )
  
  // 新增: 按设备类型过滤
  const mobileDevices = computed(() =>
    devices.value.filter(d => d.device_type === 'mobile' || !d.device_type)
  )
  
  const pcDevices = computed(() =>
    devices.value.filter(d => d.device_type === 'pc')
  )
  
  // 获取设备列表 (统一接口，包含手机和 PC 设备)
  async function fetchDevices(status = null) {
    loading.value = true
    try {
      console.log('[DeviceStore] 🔍 开始获取设备列表...')
      
      // 使用统一的设备列表接口（已包含手机和 PC 设备）
      const deviceList = await deviceApi.list(status)
      
      console.log('[DeviceStore] 📱💻 设备列表响应:', deviceList)
      
      // 确保所有设备都有 device_type 字段
      devices.value = (deviceList || []).map(d => ({
        ...d,
        device_type: d.device_type || 'mobile'  // 默认为 mobile
      }))
      
      // 统计设备数量
      const mobileCount = devices.value.filter(d => d.device_type === 'mobile' || d.device_type === 'android').length
      const pcCount = devices.value.filter(d => d.device_type === 'pc').length
      
      console.log('[DeviceStore] ✅ 设备统计 - 手机:', mobileCount, 'PC:', pcCount, '总计:', devices.value.length)
      console.log('[DeviceStore] 🎯 最终设备列表:', devices.value)
      
      return devices.value
    } catch (error) {
      console.error('[DeviceStore] ❌ 获取设备失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  // 获取设备详情
  async function fetchDevice(deviceId) {
    loading.value = true
    try {
      currentDevice.value = await deviceApi.get(deviceId)
      return currentDevice.value
    } catch (error) {
      console.error('Failed to fetch device:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  return {
    // 状态
    devices,
    loading,
    currentDevice,
    
    // 计算属性 - 保持原有的
    onlineDevices,
    busyDevices,
    offlineDevices,
    availableDevices,
    
    // 新增: 按设备类型过滤
    mobileDevices,
    pcDevices,
    
    // 方法
    fetchDevices,
    fetchDevice
  }
})

