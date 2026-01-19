<template>
  <div class="model-stats-page">
    <!-- 统一导航栏 -->
    <TopNavigation />
    
    <!-- 页面头部 -->
    <PageHeader 
      title="模型调用统计" 
      subtitle="跨任务聚合分析AI模型使用情况，追踪Token消耗、成本和性能指标"
    >
      <template #actions>
        <el-select v-model="selectedDays" size="default" style="width: 120px" @change="loadStats">
          <el-option label="最近7天" :value="7" />
          <el-option label="最近30天" :value="30" />
          <el-option label="最近90天" :value="90" />
        </el-select>
        <el-button @click="loadStats" :icon="Refresh" circle :loading="loading" />
      </template>
    </PageHeader>
    
    <!-- 页面容器 -->
    <div class="page-container">

      <!-- 摘要信息卡片 -->
      <div class="summary-section">
        <el-row :gutter="24">
          <el-col :span="6">
            <el-card shadow="never" class="stat-card-unified">
              <div class="stat-card-content">
                <div class="stat-info">
                  <div class="stat-value">{{ formatNumber(stats.total_calls || 0) }}</div>
                  <div class="stat-label">总调用次数</div>
                </div>
              </div>
            </el-card>
          </el-col>
          
          <el-col :span="6">
            <el-card shadow="never" class="stat-card-unified">
              <div class="stat-card-content">
                <div class="stat-info">
                  <div class="stat-value">{{ formatNumber(stats.total_tokens || 0) }}</div>
                  <div class="stat-label">总Token消耗</div>
                </div>
              </div>
            </el-card>
          </el-col>
          
          <el-col :span="6">
            <el-card shadow="never" class="stat-card-unified">
              <div class="stat-card-content">
                <div class="stat-info">
                  <div class="stat-value">${{ (stats.total_cost_usd || 0).toFixed(4) }}</div>
                  <div class="stat-label">总成本</div>
                </div>
              </div>
            </el-card>
          </el-col>
          
          <el-col :span="6">
            <el-card shadow="never" class="stat-card-unified">
              <div class="stat-card-content">
                <div class="stat-info">
                  <div class="stat-value">{{ stats.avg_latency_ms || 0 }}ms</div>
                  <div class="stat-label">平均延迟</div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

    <!-- 按内核模式分布 -->
    <el-card class="unified-card distribution-card" shadow="never" v-if="stats.by_kernel && Object.keys(stats.by_kernel).length > 0">
      <template #header>
        <div class="card-header-unified">
          <span class="card-title-text">按内核模式分布</span>
        </div>
      </template>
      
      <div class="kernel-distribution">
        <div 
          v-for="(data, kernel) in stats.by_kernel" 
          :key="kernel"
          class="kernel-item"
        >
          <div class="kernel-header">
            <span class="kernel-name">{{ getKernelName(kernel) }}</span>
            <el-tag :type="getKernelTagType(kernel)" size="small">
              {{ data.calls }} 次
            </el-tag>
          </div>
          
          <div class="kernel-stats">
            <div class="stat-detail">
              <span class="stat-label">Token:</span>
              <span class="stat-value">{{ formatNumber(data.tokens) }}</span>
            </div>
            <div class="stat-detail">
              <span class="stat-label">成本:</span>
              <span class="stat-value">${{ data.cost.toFixed(4) }}</span>
            </div>
            <div class="stat-detail">
              <span class="stat-label">占比:</span>
              <span class="stat-value">{{ getPercentage(data.calls, stats.total_calls) }}%</span>
            </div>
          </div>
          
          <el-progress 
            :percentage="getPercentage(data.calls, stats.total_calls)" 
            :color="getKernelColor(kernel)"
            :show-text="false"
          />
        </div>
      </div>
    </el-card>

    <!-- 按提供商分布 -->
    <el-card class="unified-card distribution-card" shadow="never" v-if="stats.by_provider && Object.keys(stats.by_provider).length > 0">
      <template #header>
        <div class="card-header-unified">
          <span class="card-title-text">按提供商分布</span>
        </div>
      </template>
      
      <div class="provider-distribution">
        <div 
          v-for="(data, provider) in stats.by_provider" 
          :key="provider"
          class="provider-item"
        >
          <div class="provider-header">
            <span class="provider-name">{{ getProviderName(provider) }}</span>
            <el-tag type="primary" size="small">{{ data.calls }} 次</el-tag>
          </div>
          
          <div class="provider-stats">
            <span>Token: {{ formatNumber(data.tokens) }}</span>
            <span>成本: ${{ data.cost.toFixed(4) }}</span>
          </div>
          
          <el-progress 
            :percentage="100" 
            color="var(--primary-color)"
            :show-text="false"
          />
        </div>
      </div>
    </el-card>

      <!-- 空状态 -->
      <el-empty 
        v-if="!loading && stats.total_calls === 0"
        description="暂无统计数据"
        :image-size="200"
      >
        <template #image>
          <el-icon :size="100" color="var(--text-tertiary)"><DataAnalysis /></el-icon>
        </template>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Refresh, DataAnalysis
} from '@element-plus/icons-vue'
import { request } from '@/api'
import TopNavigation from '@/components/TopNavigation.vue'
import PageHeader from '@/components/PageHeader.vue'

// 状态
const loading = ref(false)
const selectedDays = ref(7)
const stats = ref({
  total_calls: 0,
  total_tokens: 0,
  total_cost_usd: 0,
  avg_latency_ms: 0,
  success_rate: 0,
  by_kernel: {},
  by_provider: {}
})

// 加载统计数据
const loadStats = async () => {
  loading.value = true
  try {
    const res = await request.get(`/model-calls/stats?days=${selectedDays.value}`)
    stats.value = res
  } catch (error) {
    console.error('Failed to load model stats:', error)
    ElMessage.error('加载统计数据失败')
  } finally {
    loading.value = false
  }
}

// 格式化数字
const formatNumber = (num) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

// 计算百分比
const getPercentage = (value, total) => {
  if (total === 0) return 0
  return Math.round((value / total) * 100)
}

// 获取内核名称
const getKernelName = (kernel) => {
  const names = {
    'xml': 'XML内核',
    'vision': 'Vision内核',
    'auto': '自动模式',
    'planning': '规划模式'
  }
  return names[kernel] || kernel
}

// 获取内核标签类型
const getKernelTagType = (kernel) => {
  const types = {
    'xml': 'success',
    'vision': 'warning',
    'auto': 'info',
    'planning': 'primary'
  }
  return types[kernel] || 'info'
}

// 获取内核颜色
const getKernelColor = (kernel) => {
  const colors = {
    'xml': '#67c23a',
    'vision': '#e6a23c',
    'auto': '#909399',
    'planning': '#409eff'
  }
  return colors[kernel] || '#909399'
}

// 获取提供商名称
const getProviderName = (provider) => {
  const names = {
    'zhipu': '智谱AI',
    'openai': 'OpenAI',
    'deepseek': 'DeepSeek'
  }
  return names[provider] || provider
}

// 初始化
onMounted(() => {
  loadStats()
})
</script>

<style scoped>
/* ========== 遵循设计系统规范 ========== */

.model-stats-page {
  background: var(--bg-tertiary);
  min-height: 100vh;
}

/* 页面容器 */
.page-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 var(--space-lg) var(--space-xl);
}

/* 摘要信息卡片 */
.summary-section {
  margin-bottom: var(--space-xl);
}

.stat-card-unified {
  border: 1px solid var(--border-light);
 border-radius: var(--radius-base); /* 添加圆角 */   transition: all 0.2s ease;
 background: var(--bg-primary); /* 添加背景色 */ }

.stat-card-unified:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-light);
}

.stat-card-content {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) 0;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
  margin-bottom: var(--space-xs);
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 400;
}

/* 分布卡片 */
.distribution-card {
  margin-bottom: var(--space-xl);
  border: 1px solid var(--border-light);
 border-radius: var(--radius-base); /* 添加圆角 */ }

.kernel-distribution,
.provider-distribution {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.kernel-item,
.provider-item {
  padding: var(--space-lg);
  background: var(--bg-secondary);
  border-radius: var(--radius-base);
  border: 1px solid var(--border-light);
  transition: all 0.2s ease;
}

.kernel-item:hover,
.provider-item:hover {
  background: var(--bg-primary);
  border-color: var(--primary-color);
  box-shadow: var(--shadow-light);
}

.kernel-header,
.provider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-sm);
}

.kernel-name,
.provider-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.kernel-stats,
.provider-stats {
  display: flex;
  gap: var(--space-xl);
  margin-bottom: var(--space-md);
  font-size: 14px;
  color: var(--text-secondary);
}

.stat-detail {
  display: flex;
  gap: var(--space-xs);
  align-items: center;
}

.stat-label {
  color: var(--text-tertiary);
  font-weight: 400;
}

.stat-value {
  color: var(--text-primary);
  font-weight: 600;
}

/* 进度条样式 */
:deep(.el-progress) {
  margin-top: var(--space-xs);
}

:deep(.el-progress-bar__outer) {
  background-color: var(--bg-tertiary);
}

/* 空状态 */
:deep(.el-empty) {
  padding: var(--space-xxl) 0;
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  margin-top: var(--space-xl);
}
</style>

