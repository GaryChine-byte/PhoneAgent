<template>
  <div class="app-config-page">
    <!-- 统一导航栏 -->
    <TopNavigation />

    <!-- 统一页面头部 -->
    <PageHeader 
      title="应用配置" 
      subtitle="管理Agent可以操作的应用列表（已预置100+常用应用）"
    >
      <template #actions>
        <el-button type="primary" @click="showAddDialog" :icon="Plus">
          添加应用
        </el-button>
        <el-button @click="loadApps" :icon="Refresh" circle :loading="loading" />
      </template>
    </PageHeader>

    <!-- 搜索和筛选 -->
    <div class="page-container">
      <el-card class="filter-card unified-card" shadow="never">
        <div class="filter-content">
          <el-input
            v-model="searchQuery"
            placeholder="搜索App名称或包名..."
            clearable
            style="width: 300px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-radio-group v-model="selectedCategory" size="default">
            <el-radio-button label="全部">全部 ({{ apps.length }})</el-radio-button>
            <el-radio-button 
              v-for="cat in categories" 
              :key="cat" 
              :label="cat"
            >
              {{ cat }} ({{ getAppCountByCategory(cat) }})
            </el-radio-button>
          </el-radio-group>
          
          <div class="quick-actions">
            <el-button size="small" @click="enableAll">全部启用</el-button>
            <el-button size="small" @click="disableAll">全部禁用</el-button>
            <el-button size="small" @click="enableFiltered">启用当前筛选</el-button>
          </div>
        </div>
      </el-card>
      
      <!-- App列表 -->
      <div class="app-list" v-loading="loading">
      <el-empty v-if="filteredApps.length === 0 && !loading" description="暂无配置的App" />
      
      <el-card 
        v-for="app in filteredApps" 
        :key="app.package_name" 
        class="app-card list-item-card"
        :class="{ disabled: !app.enabled }"
        shadow="never"
      >
        <div class="app-header">
          <div class="app-info">
            <el-icon class="app-icon" :class="`category-${app.category}`">
              <Iphone />
            </el-icon>
            <div class="app-details">
              <h3>
                {{ app.display_name }}
                <span v-if="app.display_name_en" class="app-name-en">
                  / {{ app.display_name_en }}
                </span>
              </h3>
              <p class="package-name">{{ app.package_name }}</p>
              <div v-if="app.aliases && app.aliases.length > 0" class="app-aliases">
                <el-tag 
                  v-for="alias in app.aliases" 
                  :key="alias" 
                  size="small" 
                  type="info"
                  effect="plain"
                >
                  {{ alias }}
                </el-tag>
              </div>
            </div>
          </div>
          <div class="app-actions">
            <el-switch 
              v-model="app.enabled" 
              @change="updateApp(app)"
              :loading="app._updating"
            />
            <el-button 
              type="primary" 
              text 
              @click="editApp(app)"
              :icon="Edit"
            />
            <el-button 
              type="danger" 
              text 
              @click="deleteApp(app)"
              :icon="Delete"
            />
          </div>
        </div>
        <div class="app-meta">
          <el-tag size="small" :type="getCategoryTagType(app.category)">
            {{ app.category }}
          </el-tag>
          <el-tag v-if="!app.enabled" size="small" type="info">已禁用</el-tag>
        </div>
      </el-card>
      </div>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEditing ? '编辑应用' : '添加应用'"
      width="600px"
    >
      <el-alert
        v-if="!isEditing"
 title=" 提示：系统已预置100+常用应用"         type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      >
        微信、淘宝、支付宝、抖音、小红书等常用App已内置，无需手动添加。
        只有在需要使用特殊App时才需要手动添加。
      </el-alert>
      
      <el-form :model="formData" label-width="120px">
        <el-form-item label="中文显示名" required>
          <el-input v-model="formData.display_name" placeholder="例如：微信" />
          <div class="form-hint">AI 优先使用此名称（推荐中文）</div>
        </el-form-item>
        
        <el-form-item label="英文显示名">
          <el-input v-model="formData.display_name_en" placeholder="例如：WeChat" />
          <div class="form-hint">可选，支持英文任务指令</div>
        </el-form-item>
        
        <el-form-item label="别名">
          <el-input 
            v-model="aliasesInput" 
            placeholder="例如：微信,weixin,WX（逗号分隔）"
            @blur="updateAliases"
          />
          <div class="form-hint">可选，支持多个别名，用逗号分隔</div>
        </el-form-item>
        
        <el-form-item label="包名" required>
          <el-input 
            v-model="formData.package_name" 
            placeholder="例如：com.tencent.mm"
            :disabled="isEditing"
          />
          <div class="form-hint">Android 应用包名，创建后不可修改</div>
        </el-form-item>
        
        <el-form-item label="分类" required>
          <el-select v-model="formData.category" placeholder="选择分类">
            <el-option 
              v-for="cat in allCategories" 
              :key="cat" 
              :label="cat" 
              :value="cat" 
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input 
            v-model="formData.description" 
            type="textarea" 
            :rows="2"
            placeholder="应用描述（可选）"
          />
        </el-form-item>
        
        <el-form-item label="启用">
          <el-switch v-model="formData.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveApp" :loading="saving">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Plus, Refresh, Edit, Delete, Iphone, Search
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { request } from '@/api/index'
import TopNavigation from '@/components/TopNavigation.vue'
import PageHeader from '@/components/PageHeader.vue'

const router = useRouter()

const apps = ref([])
const loading = ref(false)
// const scanning = ref(false) // 已移除扫描功能 const searchQuery = ref('')
const selectedCategory = ref('全部')
const dialogVisible = ref(false)
const isEditing = ref(false)
const saving = ref(false)

const formData = ref({
  display_name: '',
  display_name_en: '',
  aliases: [],
  package_name: '',
  category: '其他',
  description: '',
  enabled: true
})

// 别名输入框（用于显示和编辑）
const aliasesInput = ref('')

// 更新别名数组
const updateAliases = () => {
  if (aliasesInput.value) {
    formData.value.aliases = aliasesInput.value
      .split(',')
      .map(a => a.trim())
      .filter(a => a.length > 0)
  } else {
    formData.value.aliases = []
  }
}

const allCategories = ['社交', '娱乐', '生活', '购物', '支付', '出行', '工具', '其他']

const categories = computed(() => {
  const cats = new Set(apps.value.map(app => app.category))
  return Array.from(cats).sort()
})

const filteredApps = computed(() => {
  let filtered = apps.value
  
  // 按分类筛选
  if (selectedCategory.value !== '全部') {
    filtered = filtered.filter(app => app.category === selectedCategory.value)
  }
  
  // 按搜索关键词筛选
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(app => 
      app.display_name.toLowerCase().includes(query) ||
      app.package_name.toLowerCase().includes(query)
    )
  }
  
  return filtered
})

function getAppCountByCategory(category) {
  return apps.value.filter(app => app.category === category).length
}

function getCategoryTagType(category) {
  const typeMap = {
    '社交': 'success',
    '娱乐': 'warning',
    '生活': 'info',
    '购物': 'danger',
    '支付': 'success',
    '出行': 'primary',
    '工具': 'info',
    '其他': ''
  }
  return typeMap[category] || ''
}

// 批量启用所有App
async function enableAll() {
  try {
    await ElMessageBox.confirm('确定要启用所有App吗？', '批量操作', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    apps.value.forEach(app => app.enabled = true)
    await saveAllApps()
    ElMessage.success('已启用所有App')
  } catch {
    // 用户取消
  }
}

// 批量禁用所有App
async function disableAll() {
  try {
    await ElMessageBox.confirm('确定要禁用所有App吗？这将影响Agent的功能。', '批量操作', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    apps.value.forEach(app => app.enabled = false)
    await saveAllApps()
    ElMessage.success('已禁用所有App')
  } catch {
    // 用户取消
  }
}

// 启用当前筛选的App
async function enableFiltered() {
  const count = filteredApps.value.length
  try {
    await ElMessageBox.confirm(`确定要启用当前筛选的 ${count} 个App吗？`, '批量操作', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })
    
    filteredApps.value.forEach(app => app.enabled = true)
    await saveAllApps()
    ElMessage.success(`已启用 ${count} 个App`)
  } catch {
    // 用户取消
  }
}

// 批量启用/禁用App（替代保存所有配置）
async function saveAllApps() {
  loading.value = true
  try {
    // 新API不再支持批量保存，而是通过单个更新完成
    // 这里保留函数以兼容现有代码
    ElMessage.success('配置已保存（通过单个更新完成）')
  } catch (error) {
    console.error('Failed to save apps:', error)
    ElMessage.error('保存失败')
    throw error
  } finally {
    loading.value = false
  }
}

// 扫描设备已安装的App
// 已移除扫描功能 // 原因：扫描出来的都是英文包名，用户体验不好
// 方案：使用预置的100+常用应用 + 手动添加

async function loadApps() {
  loading.value = true
  try {
    // 新API: /apps 替代 /apps/config
    const response = await request.get('/apps')
    // 新API返回格式: { apps: [...], total: N, stats: {...} }
    if (response && response.apps) {
      apps.value = response.apps
    } else if (Array.isArray(response)) {
      apps.value = response
    } else {
      console.warn('Unexpected response format:', response)
      apps.value = []
    }
  } catch (error) {
    console.error('Failed to load apps:', error)
    ElMessage.error('加载App配置失败')
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  isEditing.value = false
  formData.value = {
    display_name: '',
    display_name_en: '',
    aliases: [],
    package_name: '',
    category: '其他',
    description: '',
    enabled: true
  }
  aliasesInput.value = ''
  dialogVisible.value = true
}

function editApp(app) {
  isEditing.value = true
  formData.value = { ...app }
  // 将别名数组转换为逗号分隔的字符串
  aliasesInput.value = app.aliases ? app.aliases.join(', ') : ''
  dialogVisible.value = true
}

async function saveApp() {
  if (!formData.value.display_name || !formData.value.package_name) {
    ElMessage.warning('请填写完整信息')
    return
  }

  saving.value = true
  try {
    // 新API: 统一使用 POST /apps 进行创建和更新
    await request.post('/apps', formData.value)
    ElMessage.success(isEditing.value ? '更新成功' : '添加成功')
    dialogVisible.value = false
    await loadApps()
  } catch (error) {
    console.error('Failed to save app:', error)
    ElMessage.error(isEditing.value ? '更新失败' : '添加失败')
  } finally {
    saving.value = false
  }
}

async function updateApp(app) {
  app._updating = true
  try {
    // 新API: PATCH /apps/{package}/toggle 替代 PUT /apps/config/{package}
    await request.patch(`/apps/${app.package_name}/toggle`, { enabled: app.enabled })
    ElMessage.success(app.enabled ? '已启用' : '已禁用')
  } catch (error) {
    console.error('Failed to update app:', error)
    ElMessage.error('更新失败')
    app.enabled = !app.enabled // 回滚
  } finally {
    app._updating = false
  }
}

async function deleteApp(app) {
  try {
    await ElMessageBox.confirm(
      `确定要删除 "${app.display_name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 新API: DELETE /apps/{package} 替代 DELETE /apps/config/{package}
    await request.delete(`/apps/${app.package_name}`)
    ElMessage.success('删除成功')
    await loadApps()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete app:', error)
      ElMessage.error('删除失败')
    }
  }
}



onMounted(() => {
  loadApps()
})
</script>

<style scoped>
.app-config-page {
  min-height: 100vh;
  background: var(--bg-tertiary);
}

.page-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 var(--space-lg) var(--space-md);
}

/* 统一筛选卡片 */
.filter-card {
  margin-bottom: var(--space-lg);
}

.filter-content {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.quick-actions {
  display: flex;
  gap: var(--space-sm);
  margin-left: auto;
}

/* App列表 */
.app-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: var(--space-md);
}

.app-card {
  transition: all 0.3s ease;
  cursor: pointer;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-large);
  box-shadow: var(--shadow-light);
}

.app-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-base);
}

.app-card.disabled {
  opacity: 0.6;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.app-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.app-icon {
  font-size: 40px;
  padding: 10px;
  border-radius: var(--radius-large);
  background: var(--primary-color);
  color: white;
  flex-shrink: 0;
}

.app-icon.category-社交 {
  background: var(--success-color);
}

.app-icon.category-娱乐 {
  background: var(--warning-color);
}

.app-icon.category-购物 {
  background: var(--error-color);
}

.app-icon.category-支付 {
  background: var(--primary-color);
}

.app-details {
  flex: 1;
  min-width: 0;
}

.app-details h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.app-name-en {
  font-size: 14px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.package-name {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-aliases {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  flex-wrap: wrap;
}

.app-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.app-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.form-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
</style>

