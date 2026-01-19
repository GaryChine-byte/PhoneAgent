<template>
  <div class="top-nav-unified">
    <div class="nav-content-unified">
      <div class="logo-unified" @click="router.push('/')" style="cursor: pointer;">
        <el-icon><Cellphone /></el-icon>
        <span>PhoneAgent</span>
      </div>
      <div class="nav-actions-unified">
        <!-- 核心导航（始终显示）-->
        <el-button 
          @click="router.push('/')" 
          text 
          :type="currentRoute === '/' ? 'primary' : ''"
          class="nav-btn-unified"
        >
          <el-icon><HomeFilled /></el-icon>
          首页
        </el-button>
        
        <el-button 
          @click="router.push('/tasks')" 
          text
          :type="currentRoute === '/tasks' ? 'primary' : ''"
          class="nav-btn-unified"
        >
          <el-icon><Document /></el-icon>
          任务
        </el-button>
        
        <el-button 
          @click="router.push('/devices')" 
          text
          :type="currentRoute === '/devices' ? 'primary' : ''"
          class="nav-btn-unified"
        >
          <el-icon><Monitor /></el-icon>
          设备
        </el-button>

        <el-divider direction="vertical" class="nav-divider-unified" />
        
        <!-- 配置菜单（下拉）-->
        <el-dropdown trigger="hover" @command="handleCommand">
          <el-button text class="nav-dropdown-btn">
            <el-icon><Setting /></el-icon>
            <span class="nav-text">配置</span>
            <el-icon class="dropdown-icon" :size="12"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="/app-config">
                <el-icon><Iphone /></el-icon>
                <span>应用配置</span>
              </el-dropdown-item>
              <el-dropdown-item command="/anti-detection">
                <el-icon><Lock /></el-icon>
                <span>防风控配置</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        
        <!-- 工具菜单（下拉）-->
        <el-dropdown trigger="hover" @command="handleCommand">
          <el-button text class="nav-dropdown-btn">
            <el-icon><Tools /></el-icon>
            <span class="nav-text">工具</span>
            <el-icon class="dropdown-icon" :size="12"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="/logs">
                <el-icon><Document /></el-icon>
                <span>系统日志</span>
              </el-dropdown-item>
              <el-dropdown-item command="/diagnostic">
                <el-icon><DataAnalysis /></el-icon>
                <span>性能诊断</span>
              </el-dropdown-item>
              <el-dropdown-item command="/model-stats">
                <el-icon><Coin /></el-icon>
                <span>模型统计</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-divider direction="vertical" class="nav-divider-unified" />
        
        <!-- GitHub -->
        <el-tooltip content="GitHub 仓库" placement="bottom">
          <el-button
            @click="openGitHub"
            text
            circle
            class="nav-btn-circle-unified"
          >
            <svg class="github-icon" viewBox="0 0 16 16" width="18" height="18" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
            </svg>
          </el-button>
        </el-tooltip>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  Cellphone,
  HomeFilled,
  Document,
  Monitor,
  Setting,
  Lock,
  DataAnalysis,
  ArrowDown,
  Tools,
  Iphone,
  Coin  // 新增: 模型统计图标
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

const currentRoute = computed(() => route.path)

// 处理下拉菜单命令
const handleCommand = (command) => {
  router.push(command)
}

// GitHub 跳转
const openGitHub = () => {
  window.open('https://github.com/tmwgsicp/PhoneAgent', '_blank')
}
</script>

<style scoped>
/* 统一导航栏样式 */
.top-nav-unified {
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 0;
  z-index: 1000;
  box-shadow: var(--shadow-light);
  backdrop-filter: blur(10px);
}

.nav-content-unified {
  max-width: 1400px;
  margin: 0 auto;
  height: 64px;
  padding: 0 var(--space-lg);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-unified {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color);
  transition: all 0.3s ease;
}

.logo-unified:hover {
  color: var(--primary-light);
}

.logo-unified .el-icon {
  font-size: 24px;
}

.nav-actions-unified {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.nav-divider-unified {
  height: 20px;
  margin: 0 var(--space-xs);
}

/* 普通导航按钮 */
.nav-btn-unified {
  font-size: 15px;
  color: var(--text-secondary);
  padding: 10px var(--space-md);
  border-radius: var(--radius-base);
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 40px;
}

.nav-btn-unified .el-icon {
  font-size: 16px;
}

.nav-btn-unified:hover {
  color: var(--primary-color);
  background: var(--info-bg);
}

.nav-btn-unified.el-button--primary {
  color: var(--primary-color);
  background: var(--info-bg);
  font-weight: 500;
}

/* 下拉导航按钮 */
.nav-dropdown-btn {
  font-size: 15px;
  color: var(--text-secondary);
  padding: 10px var(--space-md);
  border-radius: var(--radius-base);
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 40px;
}

.nav-dropdown-btn .el-icon {
  font-size: 16px;
}

.nav-dropdown-btn .dropdown-icon {
  margin-left: 2px;
  transition: transform 0.3s ease;
}

.nav-dropdown-btn:hover {
  color: var(--primary-color);
  background: var(--info-bg);
}

.nav-dropdown-btn:hover .dropdown-icon {
  transform: rotate(180deg);
}

.nav-btn-circle-unified {
  padding: 10px;
  width: 40px;
  height: 40px;
  color: var(--text-secondary);
  transition: all 0.3s ease;
}

.nav-btn-circle-unified:hover {
  color: var(--primary-color);
  background: var(--info-bg);
}

.github-icon {
  display: block;
}

/* 下拉菜单样式优化 */
.el-dropdown-menu {
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-dark);
  border: 1px solid var(--border-light);
  padding: var(--space-xs) 0;
}

.el-dropdown-menu__item {
  padding: 10px var(--space-md);
  font-size: 14px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  transition: all 0.3s ease;
}

.el-dropdown-menu__item:hover {
  background: var(--info-bg);
  color: var(--primary-color);
}

.el-dropdown-menu__item .el-icon {
  font-size: 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .nav-content-unified {
    padding: 0 var(--space-md);
  }
  
  .logo-unified {
    font-size: 18px;
  }
  
  .logo-unified .el-icon {
    font-size: 20px;
  }
  
  .nav-btn-unified,
  .nav-dropdown-btn {
    padding: 8px var(--space-sm);
    font-size: 14px;
  }
  
  /* 移动端隐藏文字，只显示图标 */
  .nav-text {
    display: none;
  }
  
  .nav-btn-circle-unified {
    width: 36px;
    height: 36px;
    padding: 8px;
  }
  
  .nav-divider-unified {
    margin: 0 2px;
  }
}
</style>
