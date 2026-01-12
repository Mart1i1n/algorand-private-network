#!/bin/bash
# 使用 goal network 创建多节点私有网络

set -e

cd "$(dirname "$0")/.."

echo "🚀 创建4节点 Algorand 私有网络（使用 goal network）"
echo ""

# 停止现有网络（如果存在）
if docker ps -a | grep -q algo_private_network; then
  echo "📦 停止现有网络..."
  docker stop algo_private_network 2>/dev/null || true
  docker rm algo_private_network 2>/dev/null || true
fi

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
  "

# 配置 API 端点以允许外部访问
echo "🔧 配置 API 端点..."

# 为每个节点添加 EndpointAddress 配置
for node in relay node1 node2 node3; do
  config_file="private_net_data/$node/config.json"
  if [ -f "$config_file" ]; then
    case $node in
      relay) port=8080;;
      node1) port=8081;;
      node2) port=8082;;
      node3) port=8083;;
    esac
    
    # 使用 Python 添加 EndpointAddress
    python3 -c "
import json
with open('$config_file', 'r') as f:
    config = json.load(f)
config['EndpointAddress'] = '0.0.0.0:$port'
with open('$config_file', 'w') as f:
    json.dump(config, f, indent='\t')
"
    echo "  ✅ $node: 0.0.0.0:$port"
  fi
done

echo ""
echo "✅ 网络配置完成！"
echo ""
echo "下一步："
echo "  ./scripts/start_goal_network.sh"