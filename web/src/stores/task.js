import { defineStore } from 'pinia'
import { ref } from 'vue'
import { taskApi, pcTaskApi } from '@/api'

export const useTaskStore = defineStore('task', () => {
  // 状态
  const tasks = ref([])
  const loading = ref(false)
  const currentTask = ref(null)
  
  // 获取任务列表（手机 + PC）
  async function fetchTasks(params = {}) {
    loading.value = true
    try {
      // 并行获取手机任务和 PC 任务
      const [mobileTasks, pcTasksResponse] = await Promise.all([
        taskApi.list(params).catch(err => {
          console.warn('获取手机任务失败:', err)
          return []
        }),
        pcTaskApi.list(params).catch(err => {
          console.warn('获取 PC 任务失败:', err)
          return { tasks: [] }
        })
      ])
      
      // 合并任务列表（添加 device_type 标识）
      const allTasks = [
        ...mobileTasks.map(t => ({ ...t, device_type: 'mobile' })),
        ...(pcTasksResponse.tasks || []).map(t => ({ ...t, device_type: 'pc' }))
      ]
      
      // 按创建时间排序
      tasks.value = allTasks.sort((a, b) => 
        new Date(b.created_at) - new Date(a.created_at)
      )
      
      console.log(`获取任务列表: 手机 ${mobileTasks.length} 个, PC ${pcTasksResponse.tasks?.length || 0} 个`)
      
      return tasks.value
    } catch (error) {
      console.error('Failed to fetch tasks:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  // 获取任务详情（自动识别设备类型）
  async function fetchTask(taskId, deviceType = null) {
    loading.value = true
    try {
      // 如果没有指定设备类型，尝试从缓存的任务列表中推断
      if (!deviceType) {
        const cachedTask = tasks.value.find(t => t.task_id === taskId)
        deviceType = cachedTask?.device_type || 'mobile'
      }
      
      // 根据设备类型选择API
      if (deviceType === 'pc') {
        currentTask.value = await pcTaskApi.get(taskId)
        currentTask.value.device_type = 'pc'
      } else {
        currentTask.value = await taskApi.get(taskId)
        currentTask.value.device_type = 'mobile'
      }
      
      return currentTask.value
    } catch (error) {
      console.error('Failed to fetch task:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  // 创建任务
  async function createTask(data) {
    loading.value = true
    try {
      const task = await taskApi.create(data)
      tasks.value.unshift(task)
      return task
    } catch (error) {
      console.error('Failed to create task:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  // 取消任务（自动识别设备类型）
  async function cancelTask(taskId, deviceType = null) {
    loading.value = true
    try {
      // 如果没有指定设备类型，尝试从缓存的任务列表中推断
      if (!deviceType) {
        const cachedTask = tasks.value.find(t => t.task_id === taskId)
        deviceType = cachedTask?.device_type || 'mobile'
      }
      
      // 根据设备类型选择API
      if (deviceType === 'pc') {
        await pcTaskApi.cancel(taskId)
      } else {
        await taskApi.cancel(taskId)
      }
      
      // 更新本地状态
      const task = tasks.value.find(t => t.task_id === taskId)
      if (task) {
        task.status = 'cancelled'
      }
    } catch (error) {
      console.error('Failed to cancel task:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  // 删除任务（自动识别设备类型）
  async function deleteTask(taskId, deviceType = null) {
    loading.value = true
    try {
      // 如果没有指定设备类型，尝试从缓存的任务列表中推断
      if (!deviceType) {
        const cachedTask = tasks.value.find(t => t.task_id === taskId)
        deviceType = cachedTask?.device_type || 'mobile'
      }
      
      // 根据设备类型选择API
      if (deviceType === 'pc') {
        // PC 任务暂不支持删除，只能取消
        console.warn('PC 任务暂不支持删除，请使用取消功能')
        throw new Error('PC 任务暂不支持删除')
      } else {
        await taskApi.delete(taskId)
      }
      
      // 从列表中移除
      const index = tasks.value.findIndex(t => t.task_id === taskId)
      if (index !== -1) {
        tasks.value.splice(index, 1)
      }
    } catch (error) {
      console.error('Failed to delete task:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  // 批量删除任务（仅支持手机任务）
  async function deleteBatchTasks(taskIds) {
    loading.value = true
    try {
      // 过滤出手机任务
      const mobileTaskIds = taskIds.filter(taskId => {
        const task = tasks.value.find(t => t.task_id === taskId)
        return task && task.device_type !== 'pc'
      })
      
      if (mobileTaskIds.length === 0) {
        console.warn('没有可删除的手机任务（PC 任务不支持批量删除）')
        return
      }
      
      await taskApi.deleteBatch(mobileTaskIds)
      
      // 从列表中移除
      tasks.value = tasks.value.filter(t => !mobileTaskIds.includes(t.task_id))
      
      // 提示 PC 任务未删除
      const pcTaskCount = taskIds.length - mobileTaskIds.length
      if (pcTaskCount > 0) {
        console.warn(`已跳过 ${pcTaskCount} 个 PC 任务（PC 任务不支持删除）`)
      }
    } catch (error) {
      console.error('Failed to batch delete tasks:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  return {
    // 状态
    tasks,
    loading,
    currentTask,
    
    // 方法
    fetchTasks,
    fetchTask,
    createTask,
    cancelTask,
    deleteTask,
    deleteBatchTasks
  }
})

