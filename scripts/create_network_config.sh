#!/bin/bash
# 使用 goal network 创建多节点私有网络

set -e

cd "$(dirname "$0")/.."

echo "🚀 创建4节点 Algorand 私有网络（使用 goal network）"
echo ""

# 停止现有网络
echo "📦 停止现有网络..."
docker-compose down 2>/dev/null || true

# 清理旧配置
echo "🧹 清理旧配置..."
rm -rf private_net_data
mkdir -p private_net_data

# 使用 Docker 运行 goal network create
echo "⚙️  生成网络配置（使用 goal network create）..."

docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  algorand/algod:latest \
  bash -c "
    goal network create \
      -r /workspace/private_net_data \
      -n privatenet \
      -t /workspace/network_template.json
    
    echo '✅ 网络配置已生成'
    ls -la /workspace/private_net_data/
  "