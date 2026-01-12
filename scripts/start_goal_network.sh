#!/bin/bash
# 启动使用 goal network 生成的多节点私有网络

set -e

cd "$(dirname "$0")/.."

if [ ! -d "private_net_data" ]; then
  echo "❌ 网络配置不存在，请先运行: ./scripts/create_network_config.sh"
  exit 1
fi

echo "🚀 启动4节点 Algorand 私有网络"
echo ""

# 使用 goal network start
docker run -d --rm \
  --name algo_private_network \
  -v "$PWD/private_net_data:/data" \
  -p 4001:8080 \
  -p 4002:8081 \
  -p 4003:8082 \
  -p 4004:8083 \
  algorand/algod:latest \
  bash -c '
    cd /data
    
    # 修改所有节点的 config.json 以允许外部访问 API
    for node in relay node1 node2 node3; do
      if [ -f "/data/$node/config.json" ]; then
        case $node in
          relay) port=8080;;
          node1) port=8081;;
          node2) port=8082;;
          node3) port=8083;;
        esac
        # 添加 EndpointAddress 配置以允许外部访问
        python3 -c "
import json
with open('/data/$node/config.json', 'r') as f:
    config = json.load(f)
config['EndpointAddress'] = '0.0.0.0:$port'
with open('/data/$node/config.json', 'w') as f:
    json.dump(config, f, indent=8)
"
      fi
    done
    
    # 启动网络
    goal network start -r /data
    echo "✅ 网络已启动并配置外部访问"
    
    # 保持运行
    tail -f /dev/null
  '

echo "⏳ 等待网络启动..."
sleep 10

echo ""
echo "📊 检查节点状态..."
docker exec algo_private_network bash -c "
  cd /data
  echo 'Relay:'
  goal node status -d relay
  echo ''
  echo 'Node1:'
  goal node status -d node1
  echo ''
  echo 'Node2:'
  goal node status -d node2
  echo ''
  echo 'Node3:'
  goal node status -d node3
"

echo ""
echo "✅ 私有网络已启动！"
echo ""
