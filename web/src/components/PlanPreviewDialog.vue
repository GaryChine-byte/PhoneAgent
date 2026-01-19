<template>
  <el-dialog
    v-model="visible"
 title=" 任务执行计划预览"     width="90%"
    :fullscreen="isMobile"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div v-if="plan" class="plan-preview-content">
      <!-- Tab选项卡 -->
      <el-tabs v-model="activeTab" type="card" class="plan-tabs">
        <!-- 计划概览 Tab -->
 <el-tab-pane label=" 计划概览" name="overview">           <el-card class="plan-overview-card" shadow="never">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="任务指令">
                {{ plan.instruction }}
              </el-descriptions-item>
              <el-descriptions-item label="复杂度">
                <el-tag :type="getComplexityType(plan.complexity)" size="small">
                  {{ getComplexityText(plan.complexity) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="预计步骤">
                {{ plan.steps?.length || 0 }} 步
              </el-descriptions-item>
              <el-descriptions-item label="确认点">
                {{ plan.checkpoints?.length || 0 }} 个
              </el-descriptions-item>
              <el-descriptions-item label="预计耗时" :span="2">
                {{ plan.estimated_duration_seconds || 30 }} 秒
              </el-descriptions-item>
            </el-descriptions>
            
            <div v-if="plan.task_analysis" class="plan-analysis">
              <div class="analysis-label">任务分析：</div>
              <div class="analysis-content">{{ plan.task_analysis }}</div>
            </div>
            
            <div v-if="plan.overall_strategy" class="plan-strategy">
              <div class="strategy-label">执行策略：</div>
              <div class="strategy-content">{{ plan.overall_strategy }}</div>
            </div>
          </el-card>
        </el-tab-pane>
        
        <!-- 执行步骤 Tab -->
        <el-tab-pane name="steps">
          <template #label>
 <span> 执行步骤 <el-tag size="small" type="info">{{ plan.steps?.length || 0 }} 步</el-tag></span>           </template>
          
          <el-card class="plan-steps-card" shadow="never">
            <el-timeline>
              <el-timeline-item
                v-for="(step, index) in plan.steps"
                :key="index"
                :icon="getStepIcon(step.action_type)"
                :color="index === 0 ? '#409EFF' : '#909399'"
              >
                <div class="step-detail">
                  <div class="step-header-row">
                    <span class="step-number">步骤 {{ step.step_id }}</span>
                    <el-tag :type="getActionTypeTag(step.action_type)" size="small">
                      {{ step.action_type }}
                    </el-tag>
                  </div>
                  
                  <div class="step-description">
                    <strong>目标：</strong>{{ step.target_description }}
                  </div>
                  
                  <div class="step-expected">
                    <strong>预期结果：</strong>{{ step.expected_result }}
                  </div>
                  
                  <div v-if="step.reasoning" class="step-reasoning">
                    <strong>原因：</strong>{{ step.reasoning }}
                  </div>
                </div>
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </el-tab-pane>
        
        <!-- 确认点 Tab -->
        <el-tab-pane v-if="plan.checkpoints && plan.checkpoints.length > 0" name="checkpoints">
          <template #label>
 <span> 确认点 <el-tag size="small" type="warning">{{ plan.checkpoints.length }} 个</el-tag></span>           </template>
          
          <el-card class="plan-checkpoints-card" shadow="never">
            <div class="checkpoints-list">
              <div
                v-for="(checkpoint, index) in plan.checkpoints"
                :key="index"
                class="checkpoint-item"
                :class="{ critical: checkpoint.critical }"
              >
                <div class="checkpoint-header">
                  <span class="checkpoint-name">
 {{ checkpoint.critical ? '🔴' : '' }}                     {{ checkpoint.name || `确认点 ${checkpoint.step_id}` }}
                  </span>
                  <el-tag :type="checkpoint.critical ? 'danger' : 'warning'" size="small">
                    {{ checkpoint.critical ? '关键' : '普通' }}
                  </el-tag>
                </div>
                
                <div class="checkpoint-purpose">
                  <strong>目的：</strong>{{ checkpoint.purpose || '验证当前状态是否符合预期' }}
                </div>
                
                <div class="checkpoint-criteria">
                  <strong>验证标准：</strong>{{ checkpoint.validation_criteria }}
                </div>
                
                <div class="checkpoint-failure">
                  <strong>失败处理：</strong>{{ checkpoint.on_failure }}
                </div>
              </div>
            </div>
          </el-card>
        </el-tab-pane>
        
        <!-- 风险提示 Tab -->
        <el-tab-pane v-if="plan.risk_points && plan.risk_points.length > 0" name="risks">
          <template #label>
 <span> 风险提示 <el-tag size="small" type="danger">{{ plan.risk_points.length }} 个</el-tag></span>           </template>
          
          <el-card class="plan-risks-card" shadow="never">
            <el-alert
              title="以下风险可能影响任务执行"
              type="warning"
              :closable="false"
              show-icon
            >
              <ul class="risk-list">
                <li v-for="(risk, index) in plan.risk_points" :key="index">
                  {{ risk }}
                </li>
              </ul>
            </el-alert>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </div>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleExecute" :icon="VideoPlay">
          确认并执行计划
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  plan: {
    type: Object,
    default: null
  },
  isMobile: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'execute'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const activeTab = ref('overview')

const handleClose = () => {
  visible.value = false
}

const handleExecute = () => {
  emit('execute')
}

// 辅助方法
const getComplexityType = (complexity) => {
  const typeMap = {
    simple: 'success',
    medium: 'warning',
    complex: 'danger'
  }
  return typeMap[complexity] || 'info'
}

const getComplexityText = (complexity) => {
  const textMap = {
    simple: '简单任务',
    medium: '中等任务',
    complex: '复杂任务'
  }
  return textMap[complexity] || complexity
}

const getStepIcon = (actionType) => {
  const iconMap = {
    LAUNCH: 'Promotion',
    TAP: 'Pointer',
    TYPE: 'Edit',
    SWIPE: 'DArrowLeft',
    BACK: 'Back',
    HOME: 'HomeFilled',
    WAIT: 'Timer',
    CHECKPOINT: 'Check'
  }
  return iconMap[actionType] || 'Operation'
}

const getActionTypeTag = (actionType) => {
  const tagMap = {
    LAUNCH: 'primary',
    TAP: 'success',
    TYPE: 'warning',
    SWIPE: 'info',
    CHECKPOINT: 'danger'
  }
  return tagMap[actionType] || 'info'
}
</script>

<style scoped>
.plan-preview-content {
  min-height: 400px;
  max-height: 70vh;
  overflow-y: auto;
}

.plan-tabs {
  --el-tabs-header-height: 48px;
}

.plan-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.plan-tabs :deep(.el-tabs__item) {
  height: 48px;
  line-height: 48px;
  font-size: 14px;
  font-weight: 500;
}

.plan-overview-card,
.plan-steps-card,
.plan-checkpoints-card,
.plan-risks-card {
  border: none;
}

.plan-analysis,
.plan-strategy {
  margin-top: var(--space-md);
  padding: var(--space-sm);
  background: var(--bg-tertiary);
  border-radius: var(--radius-small);
}

.analysis-label,
.strategy-label {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-xs);
}

.analysis-content,
.strategy-content {
  color: var(--text-secondary);
  line-height: 1.6;
}

.step-detail {
  padding: var(--space-sm);
  background: var(--bg-tertiary);
  border-radius: var(--radius-small);
}

.step-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-sm);
}

.step-number {
  font-weight: 600;
  color: var(--text-primary);
}

.step-description,
.step-expected,
.step-reasoning {
  margin-top: var(--space-xs);
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.checkpoints-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.checkpoint-item {
  padding: var(--space-md);
  background: var(--bg-tertiary);
  border-left: 3px solid var(--warning-color);
  border-radius: var(--radius-small);
}

.checkpoint-item.critical {
  border-left-color: var(--error-color);
  background: var(--error-bg);
}

.checkpoint-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-sm);
}

.checkpoint-name {
  font-weight: 600;
  color: var(--text-primary);
}

.checkpoint-purpose,
.checkpoint-criteria,
.checkpoint-failure {
  margin-top: var(--space-xs);
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.risk-list {
  margin: 0;
  padding-left: 20px;
}

.risk-list li {
  margin-top: var(--space-xs);
  color: var(--warning-color);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
}
</style>

