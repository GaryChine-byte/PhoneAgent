#!/bin/bash
#############################################################################
# PhoneAgent 服务器端一键部署脚本
# 支持: Ubuntu 20.04+, Debian 11+
# 
# 功能:
#   - 自动检测操作系统
#   - 安装所有依赖（Python 3.10+, ADB 等）
#   - 创建 Python 虚拟环境
#   - 下载并配置 FRP Server
#   - 启动 WebSocket Server
#   - 配置防火墙
#   - 创建 systemd 服务（可选）
#
# 使用方法:
#   cd /path/to/PhoneAgent
#   chmod +x scripts/install/install_server.sh
#   sudo bash scripts/install/install_server.sh
#############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# 检查是否以 root 运行
check_root() {
    if [[ "$EUID" -ne 0 ]]; then
        log_error "请使用 root 权限运行此脚本"
        log_info "使用: sudo bash $0"
        exit 1
    fi
}

# 检测操作系统
detect_os() {
    log_step "步骤 1/9: 检测操作系统"
    
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        log_error "无法检测操作系统"
        exit 1
    fi
    
    log_info "检测到操作系统: $OS $OS_VERSION"
    
    # 只支持 Ubuntu/Debian
    case $OS in
        ubuntu|debian)
            PKG_MANAGER="apt"
            ;;
        *)
            log_error "不支持的操作系统: $OS"
            log_error "本项目仅支持 Ubuntu 20.04+ 或 Debian 11+"
            log_error "CentOS/RHEL 由于 Python 版本问题已不再支持"
            exit 1
            ;;
    esac
}

# 获取当前项目目录
get_project_dir() {
    log_step "步骤 2/8: 检查项目目录"
    
    # 获取脚本所在目录
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    # 脚本在 scripts/install/ 目录下，需要往上两级到达项目根目录
    PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
    
    log_info "项目目录: $PROJECT_DIR"
    
    # 验证项目结构
    if [[ ! -d "$PROJECT_DIR/phone_agent" ]] || [[ ! -d "$PROJECT_DIR/server" ]]; then
        log_error "当前目录不是有效的 PhoneAgent 项目"
        log_error "请确保在项目根目录下运行此脚本"
        log_error "需要存在: phone_agent/ 和 server/ 目录"
        exit 1
    fi
    
    log_info "✅ 项目目录验证成功"
}

# 获取配置
get_config() {
    log_step "步骤 3/8: 配置参数"
    
    echo -e "${YELLOW}请输入必要配置信息:${NC}"
    echo ""
    
    # FRP Token（唯一必填项）
    read -p "FRP Token (用于设备认证): " FRP_TOKEN
    while [ -z "$FRP_TOKEN" ]; do
        log_warn "Token 不能为空，请输入"
        read -p "FRP Token: " FRP_TOKEN
    done
    
    # FRP Dashboard 密码（使用默认值）
    FRP_DASHBOARD_PWD="admin123"
    
    # 是否创建 systemd 服务（保留交互选择）
    read -p "是否创建 systemd 开机自启服务? (y/n, 默认: y): " CREATE_SERVICE
    CREATE_SERVICE=${CREATE_SERVICE:-y}
    
    log_info "配置信息:"
    log_info "  - FRP Dashboard 密码: admin123 (可在frps.ini中修改)"
    log_info "  - 创建 systemd 服务: $CREATE_SERVICE"
    
    # 保存配置
    cat > ~/.phoneagent_config << EOF
FRP_TOKEN="$FRP_TOKEN"
FRP_DASHBOARD_PWD="$FRP_DASHBOARD_PWD"
PROJECT_DIR="$PROJECT_DIR"
CREATE_SERVICE="$CREATE_SERVICE"
EOF
    
    log_info "✅ 配置已保存到 ~/.phoneagent_config"
    
    # 不再要求用户确认，直接继续
    CONFIRM="y"
    
    if [[ "$CONFIRM" != "y" ]]; then
        log_warn "已取消安装"
        exit 0
    fi
}

# 修复Docker镜像源问题（如果存在）
fix_docker_mirror_issue() {
    log_info "检查并修复Docker镜像源问题..."
    
    # 检查是否存在Docker源配置
    DOCKER_SOURCES_FOUND=false
    
    # 检查所有可能包含Docker源的文件
    for file in /etc/apt/sources.list.d/*.list /etc/apt/sources.list; do
        if [[ -f "$file" ]] && grep -q "docker-ce\|mirrors.aliyun.com.*docker" "$file" 2>/dev/null; then
            DOCKER_SOURCES_FOUND=true
            log_warn "发现Docker源配置: $file"
            
            # 备份原文件
            cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
            
            # 临时禁用所有Docker相关源
            sed -i '/docker-ce/s/^/# /' "$file"
            sed -i '/mirrors\.aliyun\.com.*docker/s/^/# /' "$file"
            log_info "已临时禁用Docker源: $file"
        fi
    done
    
    # 特别处理1Panel可能创建的Docker源文件
    if [[ -f "/etc/apt/sources.list.d/docker.list" ]]; then
        DOCKER_SOURCES_FOUND=true
        log_warn "发现1Panel Docker源配置"
        mv "/etc/apt/sources.list.d/docker.list" "/etc/apt/sources.list.d/docker.list.disabled.$(date +%Y%m%d_%H%M%S)"
        log_info "已临时禁用1Panel Docker源"
    fi
    
    if [[ "$DOCKER_SOURCES_FOUND" = true ]]; then
        log_info "清理APT缓存和损坏的包列表..."
        apt clean
        rm -rf /var/lib/apt/lists/* 2>/dev/null || true
        
        # 强制重建包缓存
        log_info "重建包缓存..."
        apt-get clean
        apt-get update --fix-missing 2>/dev/null || true
        
        log_info "✅ Docker镜像源问题修复完成"
    else
        log_info "✅ 未发现Docker源配置，跳过"
    fi
}

# 安装基础依赖
install_dependencies() {
    log_step "步骤 4/8: 安装基础依赖"
    
    if [[ "$PKG_MANAGER" = "apt" ]]; then
        # 先修复可能的Docker镜像源问题
        fix_docker_mirror_issue
        
        log_info "更新包列表..."
        
        # 尝试更新包列表，如果失败则进行修复
        if ! apt update -qq 2>/dev/null; then
            log_warn "包列表更新失败，尝试修复..."
            
            # 再次检查并修复Docker源问题
            fix_docker_mirror_issue
            
            # 尝试使用不同的更新策略
            log_info "使用修复模式更新包列表..."
            apt update --fix-missing -qq || {
                log_error "包列表更新仍然失败，尝试最后的修复方案..."
                
                # 最后的修复尝试：完全重置APT缓存
                apt clean
                rm -rf /var/lib/apt/lists/*
                mkdir -p /var/lib/apt/lists/partial
                
                # 只使用官方源进行更新
                apt update -o Acquire::Check-Valid-Until=false -qq || {
                    log_error "APT更新失败，请检查网络连接和源配置"
                    log_error "您可以手动运行以下命令修复："
                    log_error "  sudo apt clean"
                    log_error "  sudo rm -rf /var/lib/apt/lists/*"
                    log_error "  sudo apt update"
                    exit 1
                }
            }
        fi
        
        log_info "✅ 包列表更新成功"
        
        log_info "安装依赖包..."
        apt install -y \
            curl \
            wget \
            python3 \
            python3-pip \
            python3-venv \
            android-tools-adb \
            net-tools \
            ufw \
            ffmpeg \
            scrcpy
    fi
    
    # 验证安装
    log_info "验证安装..."
    python3 --version || { log_error "Python3 安装失败"; exit 1; }
    adb version || { log_error "ADB 安装失败"; exit 1; }
    ffmpeg -version > /dev/null 2>&1 || { log_error "FFmpeg 安装失败"; exit 1; }
    
    # 验证 Scrcpy（非必需，只警告）
    if command -v scrcpy &> /dev/null; then
        SCRCPY_VERSION=$(scrcpy --version 2>&1 | head -n1)
        log_info "✅ Scrcpy 已安装: $SCRCPY_VERSION"
    else
        log_warn "⚠️  Scrcpy 未安装，实时预览功能将不可用"
    fi
    
    log_info "✅ 所有依赖安装成功"
}

# 创建 Python 虚拟环境
setup_python_venv() {
    log_step "步骤 5/8: 创建 Python 虚拟环境"
    
    # 在项目根目录创建虚拟环境
    cd "$PROJECT_DIR"
    
    # 检查虚拟环境是否已存在
    if [[ -d "venv" ]] && [[ -f "venv/bin/activate" ]]; then
        log_info "虚拟环境已存在，重新安装依赖..."
        source venv/bin/activate
        pip install --upgrade pip -q
        pip install -r requirements.txt -q
        deactivate
    else
        log_info "创建虚拟环境..."
        # 如果目录存在但损坏，先删除
        if [[ -d "venv" ]]; then
            rm -rf venv
        fi
        
        python3 -m venv venv
        
        log_info "激活虚拟环境并安装依赖..."
        source venv/bin/activate
        
        pip install --upgrade pip -q
        pip install -r requirements.txt -q
        
        deactivate
    fi
    
    log_info "✅ Python 虚拟环境创建成功"
}

# 安装并配置 FRP Server
setup_frp() {
    log_step "步骤 6/8: 安装并配置 FRP Server"
    
    cd "$PROJECT_DIR"
    
    # 检测架构
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            FRP_ARCH="amd64"
            ;;
        aarch64)
            FRP_ARCH="arm64"
            ;;
        armv7l)
            FRP_ARCH="arm"
            ;;
        *)
            log_error "不支持的架构: $ARCH"
            exit 1
            ;;
    esac
    
    FRP_VERSION="0.61.1"
    FRP_FILE="frp_${FRP_VERSION}_linux_${FRP_ARCH}.tar.gz"
    FRP_DIR="frp_${FRP_VERSION}_linux_${FRP_ARCH}"
    
    # 检查是否已安装
    if [[ -d "frp" ]] && [[ -f "frp/frps" ]]; then
        log_info "FRP 已安装，跳过下载"
    else
        # 下载 FRP
        if [[ ! -f "$FRP_FILE" ]]; then
            log_info "下载 FRP ${FRP_VERSION} for ${FRP_ARCH}..."
            wget -q --show-progress \
                "https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/${FRP_FILE}"
        else
            log_info "FRP 安装包已存在，跳过下载"
        fi
        
        log_info "解压 FRP..."
        tar -xzf "$FRP_FILE"
        
        # 移动到 frp 目录（如果已存在则先删除旧的）
        if [[ -d "frp" ]]; then
            log_info "删除旧的 FRP 目录..."
            rm -rf frp
        fi
        
        mv "$FRP_DIR" frp
        log_info "✅ FRP 安装完成"
    fi
    
    # 创建配置文件
    log_info "创建 FRP 配置..."
    cat > frp/frps.ini << EOF
[common]
bind_port = 7000
dashboard_port = 7500
dashboard_user = admin
dashboard_pwd = ${FRP_DASHBOARD_PWD}
token = ${FRP_TOKEN}
log_file = ./frps.log
log_level = info
allow_ports = 6100-6199

# 性能优化
max_pool_count = 50
tcp_mux = true
EOF
    
    log_info "✅ FRP Server 配置完成"
}

# 配置防火墙
configure_firewall() {
    log_step "步骤 7/8: 配置防火墙"
    
    # Ubuntu/Debian 使用 ufw
    if command -v ufw &> /dev/null; then
        log_info "配置 UFW 防火墙..."
        ufw allow 7000/tcp comment 'FRP Server' > /dev/null 2>&1 || true
        ufw allow 7500/tcp comment 'FRP Dashboard' > /dev/null 2>&1 || true
        ufw allow 8000/tcp comment 'FastAPI Server' > /dev/null 2>&1 || true
        ufw allow 9999/tcp comment 'WebSocket' > /dev/null 2>&1 || true
        ufw allow 6100:6199/tcp comment 'ADB Devices' > /dev/null 2>&1 || true
        
        # 确保 SSH 端口开放
        ufw allow 22/tcp > /dev/null 2>&1 || true
        
        log_info "✅ UFW 防火墙配置完成"
    fi
    
    log_warn "⚠️  如果使用云服务器，还需要在安全组中开放以下端口:"
    log_warn "   - 7000 (FRP Server)"
    log_warn "   - 7500 (FRP Dashboard)"
    log_warn "   - 8000 (FastAPI Server)"
    log_warn "   - 9999 (WebSocket)"
    log_warn "   - 6100-6199 (设备 ADB 端口)"
}

# 创建 systemd 服务
create_systemd_services() {
    if [[ "$CREATE_SERVICE" != "y" ]]; then
        log_info "跳过创建 systemd 服务"
        return
    fi
    
    log_step "步骤 8/8: 创建 systemd 服务"
    
    # FRP Server 服务
    log_info "创建 FRP Server 服务..."
    cat > /etc/systemd/system/phoneagent-frps.service << EOF
[Unit]
Description=PhoneAgent FRP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}/frp
ExecStart=${PROJECT_DIR}/frp/frps -c ${PROJECT_DIR}/frp/frps.ini
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # FastAPI Server 服务
    log_info "创建 FastAPI Server 服务..."
    cat > /etc/systemd/system/phoneagent-api.service << EOF
[Unit]
Description=PhoneAgent FastAPI Server
After=network.target phoneagent-frps.service

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}
Environment="PYTHONPATH=${PROJECT_DIR}"
ExecStart=${PROJECT_DIR}/venv/bin/python3 server/api/app.py
Restart=on-failure
RestartSec=10
StandardOutput=append:${PROJECT_DIR}/server/api_server.log
StandardError=append:${PROJECT_DIR}/server/api_server_error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # WebSocket Server 服务
    log_info "创建 WebSocket Server 服务..."
    cat > /etc/systemd/system/phoneagent-websocket.service << EOF
[Unit]
Description=PhoneAgent WebSocket Server
After=network.target phoneagent-frps.service phoneagent-api.service

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}
Environment="PYTHONPATH=${PROJECT_DIR}"
ExecStart=${PROJECT_DIR}/venv/bin/python3 -m server.websocket.server
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    log_info "✅ Systemd 服务创建成功"
}

# 启动服务
start_services() {
    log_step "步骤 9/9: 启动服务"
    
    if [[ "$CREATE_SERVICE" = "y" ]]; then
        log_info "启动并启用 systemd 服务..."
        
        systemctl enable phoneagent-frps
        systemctl start phoneagent-frps
        
        sleep 3
        
        systemctl enable phoneagent-api
        systemctl start phoneagent-api
        
        sleep 5
        
        systemctl enable phoneagent-websocket
        systemctl start phoneagent-websocket
        
        sleep 5
        
        log_info "等待服务启动..."
        sleep 8
        
        log_info "检查服务状态..."
        
        # FRP Server
        if systemctl is-active --quiet phoneagent-frps; then
            log_info "✅ FRP Server 运行中"
        else
            # 可能还在启动中，再检查端口
            if netstat -tlnp 2>/dev/null | grep -q ":7000"; then
                log_info "✅ FRP Server 运行中（端口已监听）"
            else
                log_error "❌ FRP Server 启动失败"
                log_warn "查看日志: journalctl -u phoneagent-frps -n 50"
            fi
        fi
        
        # FastAPI Server
        if systemctl is-active --quiet phoneagent-api; then
            log_info "✅ FastAPI Server 运行中"
        else
            # 可能还在启动中，再检查端口
            if netstat -tlnp 2>/dev/null | grep -q ":8000"; then
                log_info "✅ FastAPI Server 运行中（端口已监听）"
            else
                log_error "❌ FastAPI Server 启动失败"
                log_warn "查看日志: journalctl -u phoneagent-api -n 50"
            fi
        fi
        
        # WebSocket Server
        if systemctl is-active --quiet phoneagent-websocket; then
            log_info "✅ WebSocket Server 运行中"
        else
            # 可能还在启动中，再检查端口
            if netstat -tlnp 2>/dev/null | grep -q ":9999"; then
                log_info "✅ WebSocket Server 运行中（端口已监听）"
            else
                log_error "❌ WebSocket Server 启动失败"
                log_warn "查看日志: journalctl -u phoneagent-websocket -n 50"
            fi
        fi
        
    else
        log_info "启动服务（非 systemd 模式）..."
        
        # 强制清理所有相关进程和端口
        log_info "检查并清理已有进程..."
        
        # 清理进程
        pkill -f "frps -c frps.ini" 2>/dev/null || true
        pkill -f "uvicorn server.api.app:app" 2>/dev/null || true
        pkill -f "server.websocket.server" 2>/dev/null || true
        sleep 2
        
        # 清理端口（双重保险）
        for port in 7000 7500 8000 9999; do
            if command -v lsof &> /dev/null; then
                lsof -ti :$port | xargs kill -9 2>/dev/null || true
            fi
            fuser -k $port/tcp 2>/dev/null || true
        done
        sleep 2
        
        log_info "✅ 进程和端口清理完成"
        
        # 1. 启动 FRP Server
        log_info "启动 FRP Server..."
        cd "$PROJECT_DIR/frp"
        nohup ./frps -c frps.ini > frps.log 2>&1 &
        FRP_PID=$!
        log_info "FRP PID: $FRP_PID"
        sleep 3
        
        if ps -p $FRP_PID > /dev/null 2>&1; then
            log_info "✅ FRP Server 运行正常"
        else
            log_error "❌ FRP Server 启动失败，查看日志:"
            tail -20 "$PROJECT_DIR/frp/frps.log" 2>/dev/null || true
        fi
        
        # 2. 启动 FastAPI Server
        log_info "启动 FastAPI Server..."
        cd "$PROJECT_DIR"
        
        # 确保日志目录存在
        mkdir -p "$PROJECT_DIR/server"
        
        # 清空旧日志
        > "$PROJECT_DIR/server/api_server.log"
        
        # 启动 FastAPI
        PYTHONPATH="$PROJECT_DIR" \
        nohup "$PROJECT_DIR/venv/bin/python3" -m uvicorn server.api.app:app \
            --host 0.0.0.0 --port 8000 \
            > "$PROJECT_DIR/server/api_server.log" 2>&1 &
        API_PID=$!
        log_info "FastAPI PID: $API_PID"
        
        sleep 6
        
        # 验证 FastAPI 启动
        if ps -p $API_PID > /dev/null 2>&1; then
            log_info "✅ FastAPI Server 进程运行正常"
            
            # 测试 API 响应
            sleep 2
            if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                log_info "✅ FastAPI API 响应正常"
            else
                log_warn "⚠️  FastAPI API 暂未响应（可能还在初始化）"
            fi
        else
            log_error "❌ FastAPI 启动失败，查看日志:"
            tail -30 "$PROJECT_DIR/server/api_server.log" 2>/dev/null || true
        fi
        
        # 3. 启动 WebSocket Server
        log_info "启动 WebSocket Server..."
        cd "$PROJECT_DIR"
        
        # 清空旧日志
        > "$PROJECT_DIR/server/ws_server.log"
        
        # 启动 WebSocket
        PYTHONPATH="$PROJECT_DIR" \
        nohup "$PROJECT_DIR/venv/bin/python3" -m server.websocket.server \
            > "$PROJECT_DIR/server/ws_server.log" 2>&1 &
        WS_PID=$!
        log_info "WebSocket PID: $WS_PID"
        
        sleep 4
        
        # 验证 WebSocket 启动
        if ps -p $WS_PID > /dev/null 2>&1; then
            log_info "✅ WebSocket Server 进程运行正常"
            
            # 测试 WebSocket 响应
            sleep 2
            if curl -s http://localhost:9999/health > /dev/null 2>&1; then
                log_info "✅ WebSocket API 响应正常"
            else
                log_warn "⚠️  WebSocket API 暂未响应（可能还在初始化）"
            fi
        else
            log_error "❌ WebSocket 启动失败，查看日志:"
            tail -30 "$PROJECT_DIR/server/ws_server.log" 2>/dev/null || true
        fi
        
        log_info "✅ 所有服务已启动（后台运行）"
    fi
}

# 验证安装
verify_installation() {
    log_step "验证安装"
    
    # 端口状态统计
    local port_success=0
    local port_failed=0
    local failed_ports=()
    
    log_info "检查端口监听..."
    echo ""
    
    # 检查各个端口
    if netstat -tlnp | grep -q ":7000"; then
        log_info "✅ FRP Server (7000) 正在监听"
        ((port_success++))
    else
        log_warn "⚠️  FRP Server (7000) 未监听"
        ((port_failed++))
        failed_ports+=("7000 (FRP Server)")
    fi
    
    if netstat -tlnp | grep -q ":7500"; then
        log_info "✅ FRP Dashboard (7500) 正在监听"
        ((port_success++))
    else
        log_warn "⚠️  FRP Dashboard (7500) 未监听"
        ((port_failed++))
        failed_ports+=("7500 (FRP Dashboard)")
    fi
    
    if netstat -tlnp | grep -q ":8000"; then
        log_info "✅ FastAPI Server (8000) 正在监听"
        ((port_success++))
    else
        log_warn "⚠️  FastAPI Server (8000) 未监听"
        ((port_failed++))
        failed_ports+=("8000 (FastAPI)")
    fi
    
    if netstat -tlnp | grep -q ":9999"; then
        log_info "✅ WebSocket Server (9999) 正在监听"
        ((port_success++))
    else
        log_warn "⚠️  WebSocket Server (9999) 未监听"
        ((port_failed++))
        failed_ports+=("9999 (WebSocket)")
    fi
    
    # 显示端口状态汇总
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    if [[ $port_failed -eq 0 ]]; then
        echo -e "${GREEN}✅ 端口检查: 全部成功 (${port_success}/4)${NC}"
    else
        echo -e "${YELLOW}⚠️  端口检查: ${port_success}/4 成功, ${port_failed}/4 失败${NC}"
        echo -e "${RED}❌ 以下端口启动失败:${NC}"
        for port in "${failed_ports[@]}"; do
            echo -e "   ${RED}• $port${NC}"
        done
    fi
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    log_info "测试 API..."
    sleep 2
    
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_info "✅ FastAPI 响应正常"
    else
        log_warn "⚠️  FastAPI 无响应"
    fi
    
    if curl -s http://localhost:9999/health > /dev/null 2>&1; then
        log_info "✅ WebSocket API 响应正常"
    else
        log_warn "⚠️  WebSocket API 无响应"
    fi
}

# 显示完成信息
show_completion_info() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ PhoneAgent 服务器端安装完成!                           ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # 获取公网 IP
    PUBLIC_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || echo "YOUR_SERVER_IP")
    
    echo -e "${YELLOW}📊 服务信息:${NC}"
    echo -e "  FRP Server:       http://${PUBLIC_IP}:7000"
    echo -e "  FRP Dashboard:    http://${PUBLIC_IP}:7500"
    echo -e "    用户名: admin"
    echo -e "    密码: ${FRP_DASHBOARD_PWD}"
    echo -e "  FastAPI Server:   http://${PUBLIC_IP}:8000 ✅"
    echo -e "    API文档: http://${PUBLIC_IP}:8000/api/docs"
    echo -e "  WebSocket:        http://${PUBLIC_IP}:9999"
    echo ""
    
    echo -e "${YELLOW}📝 重要信息（手机端配置需要）:${NC}"
    echo -e "  服务器 IP:   ${PUBLIC_IP}"
    echo -e "  FRP Token:   ${FRP_TOKEN}"
    echo ""
    
    if [[ "$CREATE_SERVICE" = "y" ]]; then
        echo -e "${YELLOW}🔧 服务管理命令:${NC}"
        echo -e "  查看状态:    systemctl status phoneagent-frps"
        echo -e "              systemctl status phoneagent-api"
        echo -e "              systemctl status phoneagent-websocket"
        echo -e "  启动服务:    systemctl start phoneagent-frps phoneagent-api phoneagent-websocket"
        echo -e "  停止服务:    systemctl stop phoneagent-frps phoneagent-api phoneagent-websocket"
        echo -e "  重启服务:    systemctl restart phoneagent-frps phoneagent-api phoneagent-websocket"
        echo -e "  查看日志:    journalctl -u phoneagent-frps -f"
        echo -e "              journalctl -u phoneagent-api -f"
        echo -e "              journalctl -u phoneagent-websocket -f"
    else
        echo -e "${YELLOW}🔧 服务管理:${NC}"
        echo -e "  启动服务:    bash ${PROJECT_DIR}/scripts/start_server.sh"
        echo -e "  停止服务:    bash ${PROJECT_DIR}/scripts/stop_server.sh"
        echo -e "  查看进程:    ps aux | grep -E '(frps|uvicorn|websocket)' | grep -v grep"
        echo -e "  查看日志:"
        echo -e "    FRP:       tail -f ${PROJECT_DIR}/frp/frps.log"
        echo -e "    FastAPI:   tail -f ${PROJECT_DIR}/server/api_server.log"
        echo -e "    WebSocket: tail -f ${PROJECT_DIR}/server/ws_server.log"
    fi
    
    echo ""
    echo -e "${YELLOW}📱 下一步 - 部署手机端:${NC}"
    echo -e "  1. 在手机上安装 Termux (从 F-Droid)"
    echo -e "  2. 在 Termux 中运行:"
    echo -e "     ${GREEN}bash <(curl -s https://raw.githubusercontent.com/tmwgsicp/PhoneAgent/main/client/install_termux.sh)${NC}"
    echo -e "  3. 输入配置:"
    echo -e "     - 服务器 IP: ${PUBLIC_IP}"
    echo -e "     - FRP Token: ${FRP_TOKEN}"
    echo ""
    
    echo -e "${YELLOW}🧪 测试服务:${NC}"
    echo -e "  测试API: ${GREEN}curl http://localhost:8000/api/v1/devices${NC}"
    echo -e "  测试WebSocket: ${GREEN}curl http://localhost:9999/health${NC}"
    echo ""
    
    echo -e "${YELLOW}📚 文档:${NC}"
    echo -e "  详细文档: ${PROJECT_DIR}/QUICK_START.md"
    echo ""
}

#############################################################################
# 主流程
#############################################################################

main() {
    clear
    
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  PhoneAgent 服务器端一键安装脚本                          ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    check_root
    detect_os
    
    # 在开始安装前先检查并修复Docker镜像源问题
    log_step "预检查: Docker镜像源问题"
    fix_docker_mirror_issue
    
    get_project_dir
    get_config
    install_dependencies
    setup_python_venv
    setup_frp
    configure_firewall
    create_systemd_services
    start_services
    verify_installation
    show_completion_info
}

# 执行主流程
main

