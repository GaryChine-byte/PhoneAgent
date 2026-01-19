/**
 * 前端请求监控器
 * 用于追踪和诊断请求超时问题
 */

class RequestMonitor {
  constructor() {
    // 请求统计
    this.stats = new Map()
    
    // 活跃请求
    this.activeRequests = new Map()
    
    // 超时阈值（毫秒）
    this.timeoutThreshold = 30000
    this.slowRequestThreshold = 5000
    
    // 是否启用详细日志
    this.verboseLogging = import.meta.env.DEV
  }
  
  /**
   * 开始追踪请求
   */
  startRequest(requestId, config) {
    const startTime = Date.now()
    
    this.activeRequests.set(requestId, {
      url: config.url,
      method: config.method,
      startTime,
      config
    })
    
    if (this.verboseLogging) {
 console.log(` [Request ${requestId}] ${config.method?.toUpperCase()} ${config.url}`)     }
  }
  
  /**
   * 结束追踪请求
   */
  endRequest(requestId, success = true, error = null) {
    const request = this.activeRequests.get(requestId)
    if (!request) return
    
    const duration = Date.now() - request.startTime
    const endpoint = `${request.method} ${request.url}`
    
    // 更新统计
    if (!this.stats.has(endpoint)) {
      this.stats.set(endpoint, {
        count: 0,
        totalTime: 0,
        maxTime: 0,
        minTime: Infinity,
        slowCount: 0,
        timeoutCount: 0,
        errorCount: 0,
        lastRequests: []
      })
    }
    
    const stats = this.stats.get(endpoint)
    stats.count++
    stats.totalTime += duration
    stats.maxTime = Math.max(stats.maxTime, duration)
    stats.minTime = Math.min(stats.minTime, duration)
    
    if (duration > this.slowRequestThreshold) {
      stats.slowCount++
    }
    
    if (error) {
      stats.errorCount++
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        stats.timeoutCount++
      }
    }
    
    // 记录最近的请求
    stats.lastRequests.push({
      timestamp: new Date().toISOString(),
      duration,
      success,
      error: error ? error.message : null
    })
    
    // 只保留最近10条
    if (stats.lastRequests.length > 10) {
      stats.lastRequests.shift()
    }
    
    // 日志
    const isSlow = duration > this.slowRequestThreshold
    const isTimeout = duration > this.timeoutThreshold
    
    if (isTimeout || !success || this.verboseLogging) {
      const emoji = isTimeout ? '⏱️' : isSlow ? '⏳' : success ? '✓' : '❌'
      const level = isTimeout ? 'error' : isSlow ? 'warn' : success ? 'log' : 'error'
      
      console[level](
        `${emoji} [Request ${requestId}] ${endpoint} - ${duration}ms`,
        error ? `\nError: ${error.message}` : ''
      )
    }
    
    // 清理
    this.activeRequests.delete(requestId)
  }
  
  /**
   * 获取统计报告
   */
  getStats() {
    const report = {
      endpoints: {},
      activeRequests: this.activeRequests.size,
      totalRequests: 0,
      timeoutThreshold: this.timeoutThreshold,
      slowThreshold: this.slowRequestThreshold
    }
    
    this.stats.forEach((stats, endpoint) => {
      const avgTime = stats.totalTime / stats.count
      const slowRate = (stats.slowCount / stats.count) * 100
      const timeoutRate = (stats.timeoutCount / stats.count) * 100
      const errorRate = (stats.errorCount / stats.count) * 100
      
      report.endpoints[endpoint] = {
        totalRequests: stats.count,
        averageTime: Math.round(avgTime),
        maxTime: stats.maxTime,
        minTime: stats.minTime === Infinity ? 0 : stats.minTime,
        slowRequests: stats.slowCount,
        slowRate: slowRate.toFixed(2),
        timeoutCount: stats.timeoutCount,
        timeoutRate: timeoutRate.toFixed(2),
        errorCount: stats.errorCount,
        errorRate: errorRate.toFixed(2),
        lastRequests: stats.lastRequests.slice(-5)
      }
      
      report.totalRequests += stats.count
    })
    
    // 按平均耗时排序
    const sortedEndpoints = Object.entries(report.endpoints)
      .sort(([, a], [, b]) => b.averageTime - a.averageTime)
    
    report.endpoints = Object.fromEntries(sortedEndpoints)
    
    return report
  }
  
  /**
   * 获取慢端点
   */
  getSlowEndpoints(minSlowRate = 10) {
    const slowEndpoints = []
    
    this.stats.forEach((stats, endpoint) => {
      const avgTime = stats.totalTime / stats.count
      const slowRate = (stats.slowCount / stats.count) * 100
      
      if (slowRate >= minSlowRate || avgTime > this.slowRequestThreshold) {
        slowEndpoints.push({
          endpoint,
          averageTime: Math.round(avgTime),
          slowRate: slowRate.toFixed(2),
          totalRequests: stats.count,
          slowRequests: stats.slowCount,
          timeoutCount: stats.timeoutCount
        })
      }
    })
    
    return slowEndpoints.sort((a, b) => parseFloat(b.slowRate) - parseFloat(a.slowRate))
  }
  
  /**
   * 获取当前活跃的请求
   */
  getActiveRequests() {
    const now = Date.now()
    const active = []
    
    this.activeRequests.forEach((request, requestId) => {
      const duration = now - request.startTime
      active.push({
        requestId,
        url: request.url,
        method: request.method,
        duration,
        isTimeout: duration > this.timeoutThreshold,
        isSlow: duration > this.slowRequestThreshold
      })
    })
    
    return active.sort((a, b) => b.duration - a.duration)
  }
  
  /**
   * 生成诊断报告
   */
  generateDiagnosticReport() {
    const stats = this.getStats()
    const slowEndpoints = this.getSlowEndpoints()
    const activeRequests = this.getActiveRequests()
    
 console.group(' API 请求诊断报告')     
    console.log(`总请求数: ${stats.totalRequests}`)
    console.log(`活跃请求: ${stats.activeRequests}`)
    console.log(`慢请求阈值: ${stats.slowThreshold}ms`)
    console.log(`超时阈值: ${stats.timeoutThreshold}ms`)
    
    if (slowEndpoints.length > 0) {
      console.group('慢端点 (耗时超过阈值或慢请求率 ≥10%)')
      slowEndpoints.forEach(endpoint => {
        console.warn(
          `${endpoint.endpoint}\n` +
          `  平均耗时: ${endpoint.averageTime}ms\n` +
          `  慢请求率: ${endpoint.slowRate}%\n` +
          `  超时次数: ${endpoint.timeoutCount}`
        )
      })
      console.groupEnd()
    }
    
    if (activeRequests.length > 0) {
      console.group('当前活跃请求')
      activeRequests.forEach(req => {
        const emoji = req.isTimeout ? '⏱️' : req.isSlow ? '⏳' : '✓'
        console.log(`${emoji} ${req.method} ${req.url} - ${req.duration}ms`)
      })
      console.groupEnd()
    }
    
    console.groupEnd()
    
    return {
      stats,
      slowEndpoints,
      activeRequests
    }
  }
  
  /**
   * 清除统计数据
   */
  clearStats() {
    this.stats.clear()
 console.log(' 请求统计已清除')   }
}

// 创建全局实例
export const requestMonitor = new RequestMonitor()

// 暴露到全局（方便调试）
if (typeof window !== 'undefined') {
  window.__requestMonitor = requestMonitor
}

export default requestMonitor

