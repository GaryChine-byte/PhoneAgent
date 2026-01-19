#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
FastAPI Application - PhoneAgent Web API

提供RESTful API和WebSocket服务
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.services import get_agent_service, get_device_pool
from server.config import Config

# 初始化日志系统（必须在其他导入之前）
from server.logging_config import setup_logging
config = Config()
setup_logging(
    log_level=config.LOG_LEVEL,
    log_file="phoneagent.log",
    enable_console=True,
    enable_file=True
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(" Starting PhoneAgent API Server...")     
    # 初始化数据库
    from server.database import init_database
    init_database()
    logger.info(" Database initialized")     
    # 【重要】清理残留的 ADB 连接和端口（服务器重启后）
    from server.services.port_manager import get_port_manager
    port_manager = get_port_manager()
    await port_manager.cleanup_all_adb_connections()
    logger.info(" ADB connections cleaned up")     
    # 初始化设备池
    config = Config()
    device_pool = get_device_pool(max_devices=config.MAX_DEVICES)
    
    # 启动健康检查
    await device_pool.start_health_check(interval=config.HEALTH_CHECK_INTERVAL)
    
    # 【新增】启动设备扫描器
    from server.services.device_scanner import get_device_scanner
    scanner = get_device_scanner()
    await scanner.start()
    logger.info("设备扫描器已启动")
    
    # 启动截图和日志清理服务
    from server.tasks.cleanup import start_cleanup_service
    await start_cleanup_service()
    logger.info("清理服务已启动")     
    # 初始化App配置管理器（懒加载，首次调用时才真正加载）
    from phone_agent.config.app_manager import get_app_manager
    try:
        manager = get_app_manager()
        stats = manager.get_stats()
        logger.info(f"App config manager initialized: {stats['total']} apps ({stats['enabled']} enabled)")
    except Exception as e:
        logger.warning(f"Failed to initialize app config manager: {e}")
    
    # 设置WebSocket广播回调给AgentService（关键修复）
    from server.websocket.server import get_device_manager
    ws_manager = get_device_manager()
    agent_service = get_agent_service()
    agent_service.set_websocket_broadcast_callback(ws_manager.broadcast)
    logger.info("WebSocket广播回调已设置")
    
    # 启动后台状态广播任务
    import asyncio
    async def broadcast_status_updates():
        """定期广播状态更新"""
        while True:
            try:
                await asyncio.sleep(5)  # 每5秒推送一次
                
                # 广播设备状态
                await ws_manager.broadcast({
                    "type": "device_update",
                    "data": device_pool.get_stats()
                })
                
                # 广播任务状态
                await ws_manager.broadcast({
                    "type": "task_update",
                    "data": agent_service.get_stats()
                })
                
            except Exception as e:
                logger.error(f"Broadcast error: {e}", exc_info=True)
    
    # 启动后台任务
    broadcast_task = asyncio.create_task(broadcast_status_updates())
    logger.info("Background status broadcast task started")
    logger.info(f"PhoneAgent API Server started (max_devices={config.MAX_DEVICES})")
    yield
    
    # 关闭时取消后台任务
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass
    
    # 关闭时
    logger.info("🛑 Shutting down PhoneAgent API Server...")
    await device_pool.stop_health_check()
    
    # 【新增】停止设备扫描器
    await scanner.stop()
    
    logger.info(" PhoneAgent API Server stopped")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    
    app = FastAPI(
        title="PhoneAgent API",
        description="AI-powered phone automation platform",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # 请求日志中间件（最先添加，记录所有请求）
    from server.middleware.request_logger import RequestLoggerMiddleware
    app.add_middleware(RequestLoggerMiddleware, exclude_paths=["/health", "/api/docs", "/api/redoc"])
    
    # 超时监控中间件
    from server.middleware.timeout_monitor import TimeoutMonitorMiddleware, set_timeout_monitor
    timeout_monitor = TimeoutMonitorMiddleware(app, slow_request_threshold=5.0)
    app.add_middleware(TimeoutMonitorMiddleware, slow_request_threshold=5.0)
    set_timeout_monitor(timeout_monitor)
    
    # CORS配置（允许前端跨域访问）
    config = Config()
    logger.info(f"CORS允许的来源: {config.CORS_ORIGINS}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,  # 从配置读取允许的来源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    from server.api.routes import router
    app.include_router(router, prefix="/api/v1")
    
    # 注册应用配置管理路由
    from server.api.app_config_routes import router as app_config_router
    app.include_router(app_config_router, prefix="/api/v1")
    
    # 新增：注册截图API路由
    from server.api.screenshot import router as screenshot_router
    app.include_router(screenshot_router)
    
    # 健康检查端点
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "phoneagent-api"}
    
    # 诊断端点 - 用于查看请求统计
    @app.get("/api/v1/diagnostics/request-stats")
    async def get_request_stats():
        """获取请求统计信息"""
        from server.middleware.timeout_monitor import get_timeout_monitor
        monitor = get_timeout_monitor()
        if monitor:
            return monitor.get_stats()
        return {"error": "监控未启用"}
    
    @app.get("/api/v1/diagnostics/slow-endpoints")
    async def get_slow_endpoints(min_slow_rate: float = 10.0):
        """获取慢端点列表"""
        from server.middleware.timeout_monitor import get_timeout_monitor
        monitor = get_timeout_monitor()
        if monitor:
            return {"slow_endpoints": monitor.get_slow_endpoints(min_slow_rate)}
        return {"error": "监控未启用"}
    
    # 静态文件服务（前端）
    # app.mount("/", StaticFiles(directory="web/dist", html=True), name="static")
    
    return app


# 创建全局app实例，供uvicorn使用
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 启动服务
    config = Config()
    
    uvicorn.run(
        app,
        host=config.SERVER_HOST,
        port=8000,
        log_level="info"
    )

