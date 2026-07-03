#!/bin/bash
# GenData — 腾讯云一键部署脚本
# 用法: bash deploy.sh

set -e

echo "=== GenData 部署开始 ==="

# 检查环境
if ! command -v python3 &>/dev/null; then
    echo "安装 Python3..."
    apt update && apt install -y python3 python3-pip python3-venv nginx
fi

# 目录
APP_DIR=/opt/gendata
sudo mkdir -p $APP_DIR $APP_DIR/backend/data $APP_DIR/backend/data/tasks

# 复制文件
echo "复制项目文件..."
sudo cp -r backend $APP_DIR/
sudo cp -r frontend $APP_DIR/
sudo cp requirements.txt $APP_DIR/

# 安装依赖
echo "安装 Python 依赖..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -q

# 创建 .env 配置
cat > $APP_DIR/.env << 'EOF'
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
LLM_API_KEY=your-deepseek-api-key-here
LLM_API_URL=https://api.deepseek.com/v1/chat/completions
LLM_MODEL=deepseek-chat
HOST=127.0.0.1
PORT=8000
EOF

# 创建 systemd 服务
sudo cat > /etc/systemd/system/gendata.service << 'SERVICEEOF'
[Unit]
Description=GenData - Synthetic Data Generator
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/gendata
EnvironmentFile=/opt/gendata/.env
ExecStart=/opt/gendata/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Nginx 反向代理配置
sudo cat > /etc/nginx/sites-available/gendata << 'NGINXEOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXEOF

sudo ln -sf /etc/nginx/sites-available/gendata /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 启动
echo "启动服务..."
sudo systemctl daemon-reload
sudo systemctl enable gendata
sudo systemctl restart gendata
sudo systemctl restart nginx

echo ""
echo "=== 部署完成 ==="
echo "服务状态："
sudo systemctl status gendata --no-pager | head -5
echo ""
echo "先修改 /opt/gendata/.env 填入你的 LLM_API_KEY"
echo "然后重启服务：sudo systemctl restart gendata"
