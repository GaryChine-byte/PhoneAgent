<template>
  <div class="devices-page">
    <!-- 统一导航栏 -->
    <TopNavigation />

    <!-- 统一页面头部 -->
    <PageHeader title="设备管理" subtitle="管理和监控所有连接的设备">
      <template #actions>
        <el-button @click="refresh" :icon="Refresh" circle :loading="deviceStore.loading" />
      </template>
    </PageHeader>

    <div class="page-container">
      <!-- 统计卡片 -->
      <el-row :gutter="16" class="stats-section">
      <el-col :span="8">
        <el-card class="stat-card-unified online" shadow="never">
          <div class="stat-value">{{ deviceStore.onlineDevices?.length || 0 }}</div>
          <div class="stat-label">在线</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card-unified busy" shadow="never">
          <div class="stat-value">{{ deviceStore.busyDevices?.length || 0 }}</div>
          <div class="stat-label">忙碌</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card-unified offline" shadow="never">
          <div class="stat-value">{{ deviceStore.offlineDevices?.length || 0 }}</div>
          <div class="stat-label">离线</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 设备列表 -->
    <div class="devices-list" v-loading="deviceStore.loading">
      <el-empty
        v-if="devices.length === 0 && !deviceStore.loading"
        description="暂无设备"
      />

      <el-card
        v-for="device in devices"
        :key="device.device_id"
        class="device-card unified-card"
        shadow="never"
        @click="showDeviceDetail(device)"
      >
        <!-- 设备头部 -->
        <div class="device-header">
          <div class="device-info">
            <el-icon class="device-icon" :class="getStatusClass(device.status)">
              <Monitor v-if="device.device_type === 'pc'" />
              <Cellphone v-else />
            </el-icon>
            <div class="device-name-section">
              <h3 class="device-name">
                {{ device.device_name }}
                <el-tag 
                  v-if="device.device_type" 
                  size="small" 
                  :type="device.device_type === 'pc' ? 'warning' : 'primary'"
                  style="margin-left: 8px;"
                >
                  {{ device.device_type === 'pc' ? '电脑' : '手机' }}
                </el-tag>
              </h3>
              <span class="device-id">{{ device.device_id }}</span>
            </div>
          </div>
          <div class="device-status-tags">
            <el-tag :type="getDeviceStatusType(device)" size="large">
              {{ getDeviceStatusText(device) }}
            </el-tag>
            <div v-if="device.frp_connected || device.ws_connected" class="device-connection-tags">
              <el-tag v-if="device.frp_connected" type="success" size="small">FRP</el-tag>
              <el-tag v-if="device.ws_connected" type="success" size="small">WS</el-tag>
              <el-tag v-if="device.frp_connected && !device.ws_connected" type="info" size="small">可控制</el-tag>
            </div>
          </div>
        </div>

        <!-- 连接状态 -->
        <div class="connection-status">
          <!-- 手机设备显示 FRP + WebSocket -->
          <template v-if="device.device_type !== 'pc'">
            <div class="connection-item">
              <el-icon :style="{color: device.frp_connected ? 'var(--success-color)' : 'var(--text-tertiary)'}">
                <Connection />
              </el-icon>
              <span>FRP {{ device.frp_connected ? '已连接' : '未连接' }}</span>
            </div>
            <div class="connection-item">
              <el-icon :style="{color: device.ws_connected ? 'var(--success-color)' : 'var(--text-tertiary)'}">
                <Link />
              </el-icon>
              <span>WebSocket {{ device.ws_connected ? '已连接' : '未连接' }}</span>
            </div>
          </template>
          
          <!-- PC 设备：显示 FRP + WebSocket（与手机统一） -->
          <template v-else>
            <div class="connection-item">
              <el-icon :style="{color: device.frp_connected ? 'var(--success-color)' : 'var(--text-tertiary)'}">
                <Connection />
              </el-icon>
              <span>FRP {{ device.frp_connected ? '已连接' : '未连接' }}</span>
            </div>
            <div class="connection-item">
              <el-icon :style="{color: device.ws_connected ? 'var(--success-color)' : 'var(--text-tertiary)'}">
                <Link />
              </el-icon>
              <span>WebSocket {{ device.ws_connected ? '已连接' : '未连接' }}</span>
            </div>
          </template>
          
          <div class="connection-item" v-if="device.method">
            <el-tag size="small" :type="device.method === 'port_scanning' ? 'success' : 'info'">
              {{ device.method === 'port_scanning' ? '端口扫描' : 'WebSocket注册' }}
            </el-tag>
          </div>
        </div>

        <!-- 设备信息（根据设备类型显示不同字段） -->
        <div class="device-details">
          <!-- 手机设备字段 -->
          <template v-if="device.device_type !== 'pc'">
            <div class="detail-item" v-if="device.model">
              <el-icon><Monitor /></el-icon>
              <span>{{ device.model }}</span>
            </div>
            <div class="detail-item" v-if="device.android_version">
              <el-icon><Platform /></el-icon>
              <span>Android {{ device.android_version }}</span>
            </div>
          </template>
          
          <!-- PC 设备字段 -->
          <template v-if="device.device_type === 'pc'">
            <div class="detail-item" v-if="device.os_info">
              <el-icon><Platform /></el-icon>
              <span>{{ device.os_info.platform }} {{ device.os_info.version }}</span>
            </div>
            <div class="detail-item" v-if="device.model">
              <el-icon><Monitor /></el-icon>
              <span>{{ device.model }}</span>
            </div>
          </template>
          
          <!-- 通用字段 -->
          <div class="detail-item" v-if="device.screen_resolution">
            <el-icon><Odometer /></el-icon>
            <span>{{ device.screen_resolution }}</span>
          </div>
          <div class="detail-item" v-if="device.memory_total">
            <el-icon><Odometer /></el-icon>
            <span>内存: {{ device.memory_available || '?' }} / {{ device.memory_total }}</span>
          </div>
        </div>

        <!-- 设备指标（根据设备类型区分） -->
        <el-row :gutter="12" class="device-metrics">
          <!-- 手机设备：显示电池和端口 -->
          <template v-if="device.device_type !== 'pc'">
            <el-col :span="12" v-if="device.battery !== null && device.battery !== undefined">
              <div class="metric-item">
                <el-icon><Odometer /></el-icon>
                <span>电量</span>
                <el-progress
                  :percentage="device.battery"
                  :color="getBatteryColor(device.battery)"
                  :stroke-width="8"
                  :show-text="true"
                />
              </div>
            </el-col>
            <el-col :span="device.battery !== null && device.battery !== undefined ? 12 : 24">
              <div class="metric-item">
                <el-icon><Connection /></el-icon>
                <span>FRP端口</span>
                <div class="port-value">{{ device.frp_port }}</div>
              </div>
            </el-col>
          </template>
          
          <!-- PC 设备：显示端口和系统信息 -->
          <template v-if="device.device_type === 'pc'">
            <el-col :span="12" v-if="device.frp_port">
              <div class="metric-item">
                <el-icon><Connection /></el-icon>
                <span>FRP端口</span>
                <div class="port-value">{{ device.frp_port }}</div>
              </div>
            </el-col>
            <el-col :span="12" v-if="device.os_info && device.os_info.machine">
              <div class="metric-item">
                <el-icon><Monitor /></el-icon>
                <span>架构</span>
                <div class="port-value">{{ device.os_info.machine }}</div>
              </div>
            </el-col>
          </template>
        </el-row>

        <!-- 任务统计 -->
        <el-divider />
        <div class="task-stats">
          <div class="task-stat-item">
            <div class="task-stat-value">{{ device.total_tasks }}</div>
            <div class="task-stat-label">总任务</div>
          </div>
          <div class="task-stat-item">
            <div class="task-stat-value success">{{ device.success_tasks }}</div>
            <div class="task-stat-label">成功</div>
          </div>
          <div class="task-stat-item">
            <div class="task-stat-value failed">{{ device.failed_tasks }}</div>
            <div class="task-stat-label">失败</div>
          </div>
          <div class="task-stat-item">
            <div class="task-stat-value">{{ device.success_rate.toFixed(0) }}%</div>
            <div class="task-stat-label">成功率</div>
          </div>
        </div>

        <!-- 当前任务 -->
        <div v-if="device.current_task" class="current-task">
          <el-alert type="warning" :closable="false">
            <template #title>
              <el-icon><Loading /></el-icon>
              正在执行任务: {{ device.current_task }}
            </template>
          </el-alert>
        </div>
      </el-card>
    </div>
    </div>

    <!-- 设备详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="设备详情"
      width="90%"
      :fullscreen="isMobile"
    >
      <el-descriptions v-if="selectedDevice" :column="1" border>
        <!-- 基本信息（通用） -->
        <el-descriptions-item label="设备ID">
          {{ selectedDevice.device_id }}
        </el-descriptions-item>
        <el-descriptions-item label="设备名称">
          {{ selectedDevice.device_name }}
        </el-descriptions-item>
        <el-descriptions-item label="设备类型">
          <el-tag :type="selectedDevice.device_type === 'pc' ? 'warning' : 'primary'">
            {{ selectedDevice.device_type === 'pc' ? '电脑' : '手机' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <div style="display: flex; gap: 8px; align-items: center;">
            <el-tag :type="getDeviceStatusType(selectedDevice)">
              {{ getDeviceStatusText(selectedDevice) }}
            </el-tag>
            <div v-if="selectedDevice.frp_connected || selectedDevice.ws_connected" style="display: flex; gap: 4px;">
              <el-tag v-if="selectedDevice.frp_connected" type="success" size="small">FRP连接</el-tag>
              <el-tag v-if="selectedDevice.ws_connected" type="success" size="small">WebSocket连接</el-tag>
            </div>
          </div>
        </el-descriptions-item>
        
        <!-- 手机设备专属字段 -->
        <template v-if="selectedDevice.device_type !== 'pc'">
          <el-descriptions-item label="FRP 端口">
            {{ selectedDevice.frp_port }}
          </el-descriptions-item>
          <el-descriptions-item label="ADB 地址">
            {{ selectedDevice.adb_address }}
          </el-descriptions-item>
          <el-descriptions-item label="型号" v-if="selectedDevice.model">
            {{ selectedDevice.model }}
          </el-descriptions-item>
          <el-descriptions-item label="Android 版本" v-if="selectedDevice.android_version">
            {{ selectedDevice.android_version }}
          </el-descriptions-item>
          <el-descriptions-item label="电池电量" v-if="selectedDevice.battery !== null && selectedDevice.battery !== undefined">
            {{ selectedDevice.battery }}%
          </el-descriptions-item>
          <el-descriptions-item label="FRP 连接">
            <el-tag :type="selectedDevice.frp_connected ? 'success' : 'info'">
              {{ selectedDevice.frp_connected ? '已连接' : '未连接' }}
            </el-tag>
          </el-descriptions-item>
        </template>
        
        <!-- PC 设备专属字段 -->
        <template v-if="selectedDevice.device_type === 'pc'">
          <el-descriptions-item label="FRP 端口">
            {{ selectedDevice.frp_port }}
          </el-descriptions-item>
          <el-descriptions-item label="FRP 连接">
            <el-tag :type="selectedDevice.frp_connected ? 'success' : 'info'">
              {{ selectedDevice.frp_connected ? '已连接' : '未连接' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="操作系统" v-if="selectedDevice.os_info">
            {{ selectedDevice.os_info.system }} {{ selectedDevice.os_info.release }}
          </el-descriptions-item>
          <el-descriptions-item label="系统架构" v-if="selectedDevice.os_info && selectedDevice.os_info.machine">
            {{ selectedDevice.os_info.machine }}
          </el-descriptions-item>
          <el-descriptions-item label="处理器" v-if="selectedDevice.os_info && selectedDevice.os_info.processor">
            {{ selectedDevice.os_info.processor }}
          </el-descriptions-item>
          <el-descriptions-item label="主机名" v-if="selectedDevice.model">
            {{ selectedDevice.model }}
          </el-descriptions-item>
        </template>
        
        <!-- 通用字段 -->
        <el-descriptions-item label="屏幕分辨率" v-if="selectedDevice.screen_resolution && selectedDevice.screen_resolution !== 'unknown'">
          {{ selectedDevice.screen_resolution }}
        </el-descriptions-item>
        <el-descriptions-item label="内存" v-if="selectedDevice.memory_total">
          {{ selectedDevice.memory_available || '?' }} / {{ selectedDevice.memory_total }}
        </el-descriptions-item>
        <el-descriptions-item label="存储" v-if="selectedDevice.storage_total">
          {{ selectedDevice.storage_available || '?' }} / {{ selectedDevice.storage_total }}
        </el-descriptions-item>
        <el-descriptions-item label="WebSocket 连接">
          <el-tag :type="selectedDevice.ws_connected ? 'success' : 'info'">
            {{ selectedDevice.ws_connected ? '已连接' : '未连接' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="总任务数">
          {{ selectedDevice.total_tasks }}
        </el-descriptions-item>
        <el-descriptions-item label="成功任务数">
          {{ selectedDevice.success_tasks }}
        </el-descriptions-item>
        <el-descriptions-item label="失败任务数">
          {{ selectedDevice.failed_tasks }}
        </el-descriptions-item>
        <el-descriptions-item label="成功率">
          {{ selectedDevice.success_rate ? selectedDevice.success_rate.toFixed(2) : 0 }}%
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">
          {{ new Date(selectedDevice.registered_at).toLocaleString('zh-CN') }}
        </el-descriptions-item>
        <el-descriptions-item label="最后活跃">
          {{ new Date(selectedDevice.last_active).toLocaleString('zh-CN') }}
        </el-descriptions-item>
        <el-descriptions-item label="当前任务" v-if="selectedDevice.current_task">
          {{ selectedDevice.current_task }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Refresh,
  Cellphone,
  Connection,
  Link,
  Monitor,
  Platform,
  Odometer,
  Loading,
  Picture,
  Cpu
} from '@element-plus/icons-vue'
import { useDeviceStore } from '@/stores/device'
import { ElMessage, ElMessageBox } from 'element-plus'
import TopNavigation from '@/components/TopNavigation.vue'
import PageHeader from '@/components/PageHeader.vue'

const router = useRouter()
const deviceStore = useDeviceStore()

const detailDialogVisible = ref(false)
const selectedDevice = ref(null)

// API基础URL
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''

const devices = computed(() => deviceStore.devices)
const isMobile = computed(() => window.innerWidth < 768)

// 刷新列表
async function refresh() {
  try {
    await deviceStore.fetchDevices()
  } catch (error) {
    console.error('Failed to fetch devices:', error)
    ElMessage.warning('无法连接到后端服务，请确保后端已启动')
  }
}

// 显示设备详情
function showDeviceDetail(device) {
  selectedDevice.value = device
  detailDialogVisible.value = true
}

// 状态类名
function getStatusClass(status) {
  return `status-${status}`
}

// 状态标签类型
function getStatusTagType(status) {
  const typeMap = {
    online: 'success',
    offline: 'info',
    busy: 'warning',
    error: 'danger'
  }
  return typeMap[status] || 'info'
}

// 状态文本
function getStatusText(status) {
  const textMap = {
    online: '在线',
    offline: '离线',
    busy: '忙碌',
    error: '错误'
  }
  return textMap[status] || status
}

// 设备状态判断函数
function getDeviceStatusType(device) {
  if (device.status !== 'online') return 'info'
  
  // PC 设备：只看 WebSocket
  if (device.device_type === 'pc') {
    return device.ws_connected ? 'success' : 'info'
  }
  
  // 手机设备：看双连接
  if (device.frp_connected && device.ws_connected) return 'success'
  if (device.frp_connected && !device.ws_connected) return 'success' // FRP连接就是可用状态
  return 'info'
}

function getDeviceStatusText(device) {
  if (device.status !== 'online') return '离线'
  
  // PC 设备：只看 WebSocket
  if (device.device_type === 'pc') {
    return device.ws_connected ? '在线' : '离线'
  }
  
  // 手机设备：看双连接
  if (device.frp_connected && device.ws_connected) return '完全连接'
  if (device.frp_connected && !device.ws_connected) return '已连接'
  return '离线'
}

// 电池颜色
function getBatteryColor(battery) {
  if (battery > 60) return '#67C23A'
  if (battery > 20) return '#E6A23C'
  return '#F56C6C'
}

// 生命周期
onMounted(() => {
  refresh()
})
</script>

<style scoped>
.devices-page {
  min-height: 100vh;
  background: var(--bg-tertiary);
}

.page-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 var(--space-lg) var(--space-xl);
}



/* 统计卡片 */
.stats-section {
  margin-bottom: var(--space-lg);
}

.device-status-tags {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.device-connection-tags {
  display: flex;
  gap: var(--space-xs);
}

/* 统一统计卡片样式 - 遵循设计哲学：简洁、克制 */
.stat-card-unified {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-base);
  box-shadow: none;
  transition: all 0.3s ease;
  text-align: center;
  padding: var(--space-md);
}

.stat-card-unified:hover {
  border-color: var(--primary-color);
  box-shadow: var(--shadow-light);
}

.stat-card-unified.online:hover {
  border-color: var(--success-color);
}

.stat-card-unified.busy:hover {
  border-color: var(--warning-color);
}

.stat-card-unified.offline:hover {
  border-color: var(--text-tertiary);
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: var(--space-xs);
}

.stat-card-unified.online .stat-value {
  color: var(--success-color);
}

.stat-card-unified.busy .stat-value {
  color: var(--warning-color);
}

.stat-card-unified.offline .stat-value {
  color: var(--text-tertiary);
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
}

/* 设备列表 */
.devices-list {
  padding: 0 16px;
}

.device-card {
  margin-bottom: var(--space-md);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-large);
  box-shadow: var(--shadow-light);
}

.device-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-base);
}

/* 设备头部 */
.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.device-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.device-icon {
  font-size: 40px;
  padding: 10px;
  border-radius: var(--radius-large);
  background: var(--primary-color);
  color: white;
}

.device-icon.status-offline {
  background: var(--text-tertiary);
}

.device-icon.status-busy {
  background: var(--warning-color);
}

.device-name-section {
  display: flex;
  flex-direction: column;
}

.device-name {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.device-id {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

/* 连接状态 */
.connection-status {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.connection-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

/* 设备详情 */
.device-details {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  font-size: 13px;
}

/* 设备指标 */
.device-metrics {
  margin-bottom: 16px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-item span {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.port-value {
  font-size: 20px;
  font-weight: bold;
  color: var(--el-color-primary);
}

/* 任务统计 */
.task-stats {
  display: flex;
  justify-content: space-around;
  padding: 8px 0;
}

.task-stat-item {
  text-align: center;
}

.task-stat-value {
  font-size: 24px;
  font-weight: bold;
  color: var(--el-text-color-primary);
}

.task-stat-value.success {
  color: var(--el-color-success);
}

.task-stat-value.failed {
  color: var(--el-color-danger);
}

.task-stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

/* 当前任务 */
.current-task {
  margin-top: 12px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .page-header h2 {
    font-size: 16px;
  }
  
  .device-name {
    font-size: 16px;
  }
  
  .device-icon {
    font-size: 32px;
    padding: 8px;
  }
  
  .connection-status {
    flex-direction: column;
    gap: 8px;
  }
  
  .task-stat-value {
    font-size: 20px;
  }
}
</style>

