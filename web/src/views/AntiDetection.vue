<template>
  <div class="anti-detection-page">
    <!-- 统一导航栏 -->
    <TopNavigation />

    <!-- 统一页面头部 -->
    <PageHeader title="防风控配置" subtitle="让自动化操作更像真人，降低被检测风险">
      <template #actions>
        <el-switch
          v-model="config.enabled"
          size="large"
          inline-prompt
          active-text="已启用"
          inactive-text="已禁用"
          @change="toggleAntiDetection"
          :loading="loading"
        />
        <el-button type="primary" @click="saveConfig" :loading="saving" :icon="Check">
          保存配置
        </el-button>
        <el-button @click="resetConfig" :icon="RefreshRight">重置</el-button>
        <el-button @click="loadConfig" :icon="Refresh" circle :loading="loading" />
      </template>
    </PageHeader>

    <div class="page-container" v-loading="loading">
      <!-- 防护等级选择 -->
      <el-card class="level-card unified-card" shadow="never">
        <template #header>
          <div class="card-header-unified">
            <div class="card-title-content">
              <el-icon><TrendCharts /></el-icon>
              <span class="card-title-text">防护等级</span>
            </div>
          </div>
        </template>
        
        <el-radio-group v-model="config.level" size="large" @change="onLevelChange" class="level-radio-group">
          <el-radio-button label="low">
            <div class="level-option">
              <div class="level-name">🟢 低级防护</div>
              <div class="level-desc">快速执行，适合测试</div>
              <div class="level-time">延迟: 0.3-1.0秒</div>
            </div>
          </el-radio-button>
          <el-radio-button label="medium">
            <div class="level-option">
              <div class="level-name">🟡 中级防护 <el-tag size="small">推荐</el-tag></div>
              <div class="level-desc">平衡性能和安全</div>
              <div class="level-time">延迟: 0.5-3.0秒</div>
            </div>
          </el-radio-button>
          <el-radio-button label="high">
            <div class="level-option">
              <div class="level-name">🔴 高级防护</div>
              <div class="level-desc">最安全，适合高风险操作</div>
              <div class="level-time">延迟: 1.0-5.0秒</div>
            </div>
          </el-radio-button>
        </el-radio-group>
      </el-card>

      <!-- 高级配置 -->
      <el-card class="advanced-card unified-card" shadow="never">
        <template #header>
          <div class="card-header-unified">
            <div class="card-title-content">
              <el-icon><Tools /></el-icon>
              <span class="card-title-text">高级配置</span>
            </div>
          </div>
        </template>

        <el-collapse>
          <!-- 功能开关 -->
          <el-collapse-item title="🎛️ 功能开关" name="features">
            <el-form label-width="180px">
              <el-form-item label="时间随机化">
                <el-switch v-model="config.enable_time_random" />
                <div class="help-text">为每个操作添加随机延迟</div>
              </el-form-item>

              <el-form-item label="坐标随机化">
                <el-switch v-model="config.enable_position_random" />
 <div class="help-text"> 点击坐标随机偏移（可能影响准确性，建议关闭）</div>               </el-form-item>

              <el-form-item label="贝塞尔曲线滑动">
                <el-switch v-model="config.enable_bezier_swipe" />
                <div class="help-text">使用自然曲线模拟滑动轨迹</div>
              </el-form-item>

              <el-form-item label="输入速度模拟">
                <el-switch v-model="config.enable_typing_simulation" />
                <div class="help-text">模拟真人打字速度和节奏</div>
              </el-form-item>

              <el-form-item label="探索行为">
                <el-switch v-model="config.enable_exploration" />
                <div class="help-text">随机添加探索性操作（滚动、浏览等）</div>
              </el-form-item>
            </el-form>
          </el-collapse-item>

          <el-collapse-item title="⏱️ 时间配置" name="time">
            <el-form label-width="180px">
              <el-form-item label="低级延迟范围 (秒)">
                <el-col :span="11">
                  <el-input-number 
                    v-model="config.delay_levels.low.min" 
                    :min="0.1" 
                    :max="2" 
                    :step="0.1"
                    :precision="1"
                  />
                </el-col>
                <el-col :span="2" style="text-align: center;">~</el-col>
                <el-col :span="11">
                  <el-input-number 
                    v-model="config.delay_levels.low.max" 
                    :min="0.2" 
                    :max="3" 
                    :step="0.1"
                    :precision="1"
                  />
                </el-col>
              </el-form-item>

              <el-form-item label="中级延迟范围 (秒)">
                <el-col :span="11">
                  <el-input-number 
                    v-model="config.delay_levels.medium.min" 
                    :min="0.1" 
                    :max="3" 
                    :step="0.1"
                    :precision="1"
                  />
                </el-col>
                <el-col :span="2" style="text-align: center;">~</el-col>
                <el-col :span="11">
                  <el-input-number 
                    v-model="config.delay_levels.medium.max" 
                    :min="0.5" 
                    :max="5" 
                    :step="0.1"
                    :precision="1"
                  />
                </el-col>
              </el-form-item>

              <el-form-item label="高级延迟范围 (秒)">
                <el-col :span="11">
                  <el-input-number 
                    v-model="config.delay_levels.high.min" 
                    :min="0.5" 
                    :max="5" 
                    :step="0.1"
                    :precision="1"
                  />
                </el-col>
                <el-col :span="2" style="text-align: center;">~</el-col>
                <el-col :span="11">
                  <el-input-number 
                    v-model="config.delay_levels.high.max" 
                    :min="1" 
                    :max="10" 
                    :step="0.1"
                    :precision="1"
                  />
                </el-col>
              </el-form-item>
            </el-form>
          </el-collapse-item>

          <el-collapse-item title="📍 坐标配置" name="position">
            <el-form label-width="180px">
              <el-form-item label="坐标偏移百分比">
                <el-slider 
                  v-model="positionOffsetPercent" 
                  :min="0" 
                  :max="50" 
                  :step="5"
                  show-input
                  @change="updatePositionOffset"
                />
                <div class="help-text">点击坐标随机偏移±{{ positionOffsetPercent }}%</div>
              </el-form-item>
            </el-form>
          </el-collapse-item>

 <el-collapse-item title=" 贝塞尔曲线配置" name="bezier">             <el-form label-width="180px">
              <el-form-item label="曲线分段数">
                <el-input-number 
                  v-model="config.bezier_steps" 
                  :min="10" 
                  :max="50" 
                  :step="5"
                />
                <div class="help-text">分段越多，滑动越平滑（建议20）</div>
              </el-form-item>

              <el-form-item label="控制点随机范围">
                <el-input-number 
                  v-model="config.bezier_control_randomness" 
                  :min="50" 
                  :max="200" 
                  :step="10"
                />
                <div class="help-text">像素偏移范围，越大轨迹越弯曲</div>
              </el-form-item>
            </el-form>
          </el-collapse-item>

          <el-collapse-item title="⌨️ 输入配置" name="typing">
            <el-form label-width="180px">
              <el-form-item label="打字延迟 (秒)">
                <el-col :span="11">
                  <el-input-number 
                    v-model="config.typing_delay.min" 
                    :min="0.05" 
                    :max="0.5" 
                    :step="0.05"
                    :precision="2"
                  />
                </el-col>
                <el-col :span="2" style="text-align: center;">~</el-col>
                <el-col :span="11">
                  <el-input-number 
                    v-model="config.typing_delay.max" 
                    :min="0.1" 
                    :max="1" 
                    :step="0.05"
                    :precision="2"
                  />
                </el-col>
              </el-form-item>

              <el-form-item label="打错字概率">
                <el-slider 
                  v-model="typoPercentage" 
                  :min="0" 
                  :max="20" 
                  :step="1"
                  show-input
                  @change="updateTypoProbability"
                />
                <div class="help-text">{{ typoPercentage }}% 概率模拟打错字</div>
              </el-form-item>

              <el-form-item label="停顿间隔">
                <el-input-number 
                  v-model="config.pause_every_n_chars" 
                  :min="5" 
                  :max="20" 
                  :step="1"
                />
                <div class="help-text">每输入N个字符停顿思考</div>
              </el-form-item>
            </el-form>
          </el-collapse-item>

 <el-collapse-item title=" 探索行为配置" name="exploration">             <el-form label-width="180px">
              <el-form-item label="探索概率">
                <el-slider 
                  v-model="explorationPercentage" 
                  :min="0" 
                  :max="100" 
                  :step="5"
                  show-input
                  @change="updateExplorationProbability"
                />
                <div class="help-text">{{ explorationPercentage }}% 概率先探索再执行</div>
              </el-form-item>
            </el-form>
          </el-collapse-item>
        </el-collapse>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  RefreshRight, Check, TrendCharts, Tools, Refresh
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { request } from '@/api/index'
import TopNavigation from '@/components/TopNavigation.vue'
import PageHeader from '@/components/PageHeader.vue'

const router = useRouter()

const config = ref({
  enabled: true,
  level: 'medium',
  enable_time_random: true,
  enable_position_random: true,
  enable_bezier_swipe: true,
  enable_typing_simulation: true,
  enable_exploration: true,
  delay_levels: {
    low: { min: 0.3, max: 1.0 },
    medium: { min: 0.5, max: 3.0 },
    high: { min: 1.0, max: 5.0 }
  },
  position_offset_percentage: 0.2,
  bezier_steps: 20,
  bezier_control_randomness: 100,
  typing_delay: { min: 0.1, max: 0.3 },
  typo_probability: 0.05,
  pause_every_n_chars: 10,
  exploration_probability: 0.3
})

const loading = ref(false)
const saving = ref(false)

// 辅助计算属性
const positionOffsetPercent = computed({
  get: () => Math.round(config.value.position_offset_percentage * 100),
  set: (val) => {}
})

const typoPercentage = computed({
  get: () => Math.round(config.value.typo_probability * 100),
  set: (val) => {}
})

const explorationPercentage = computed({
  get: () => Math.round(config.value.exploration_probability * 100),
  set: (val) => {}
})

async function loadConfig() {
  loading.value = true
  try {
    const response = await request.get('/anti-detection/config')
    config.value = response
  } catch (error) {
    console.error('Failed to load config:', error)
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    await request.put('/anti-detection/config', config.value)
    ElMessage.success('配置已保存')
  } catch (error) {
    console.error('Failed to save config:', error)
    ElMessage.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

async function resetConfig() {
  try {
    await ElMessageBox.confirm('确定要重置为默认配置吗？', '确认重置', {
      confirmButtonText: '重置',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    loading.value = true
    await request.post('/anti-detection/reset')
    await loadConfig()
    ElMessage.success('已重置为默认配置')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to reset config:', error)
      ElMessage.error('重置失败')
    }
  } finally {
    loading.value = false
  }
}

async function toggleAntiDetection() {
  try {
    const endpoint = config.value.enabled ? 'enable' : 'disable'
    await request.post(`/anti-detection/${endpoint}`)
    ElMessage.success(config.value.enabled ? '已启用防风控' : '已禁用防风控')
  } catch (error) {
    console.error('Failed to toggle:', error)
    config.value.enabled = !config.value.enabled // 回滚
    ElMessage.error('操作失败')
  }
}

async function onLevelChange() {
  try {
    await request.put(`/anti-detection/level?level=${config.value.level}`)
    ElMessage.success(`已切换到${config.value.level}级防护`)
  } catch (error) {
    console.error('Failed to change level:', error)
    ElMessage.error('切换失败')
  }
}

function updatePositionOffset(value) {
  config.value.position_offset_percentage = value / 100
}

function updateTypoProbability(value) {
  config.value.typo_probability = value / 100
}

function updateExplorationProbability(value) {
  config.value.exploration_probability = value / 100
}



onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.anti-detection-page {
  min-height: 100vh;
  background: var(--bg-tertiary);
}

/* 使用统一的 page-container 样式 */
.page-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

/* 使用统一的 card-header-unified 样式,移除自定义样式 */

/* 等级卡片 */
.level-card {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-large);
  box-shadow: var(--shadow-light);
}

.level-radio-group {
  display: flex;
  gap: var(--space-sm);
  width: 100%;
}

.level-radio-group :deep(.el-radio-button) {
  flex: 1;
}

.level-radio-group :deep(.el-radio-button__inner) {
  width: 100%;
  padding: 16px;
  height: auto;
  border-radius: var(--radius-base) !important;
}

.level-radio-group :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: var(--radius-base) 0 0 var(--radius-base) !important;
}

.level-radio-group :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 var(--radius-base) var(--radius-base) 0 !important;
}

.level-option {
  text-align: center;
}

.level-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.level-desc {
  font-size: 13px;
  color: var(--text-tertiary);
  margin-bottom: var(--space-xs);
}

.level-time {
  font-size: 12px;
  color: var(--success-color);
  font-weight: 500;
}

/* 卡片统一样式 */
.level-card,
.advanced-card {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-large);
  box-shadow: var(--shadow-light);
}

/* 高级配置 */
.advanced-card :deep(.el-collapse-item__header) {
  font-weight: 600;
  font-size: 15px;
}

.help-text {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>

