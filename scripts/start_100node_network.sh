#!/bin/bash
# 启动使用 goal network 生成的100节点私有网络

set -e

cd "$(dirname "$0")/.."

if [ ! -d "private_net_data_100nodes" ]; then
  echo "❌ 网络配置不存在，请先运行: ./scripts/create_100node_network.sh"
  exit 1
fi

echo "🚀 启动100节点 Algorand 私有网络"
echo ""

# 使用 goal network start
docker run -d --rm \
  --name algo_private_network_100 \
  -v "$PWD/private_net_data_100nodes:/data" \
  -p 5001:8080 \
  -p 5002:8081 \
  -p 5101:8100 \
  -p 5102:8101 \
  -p 5103:8102 \
  -p 5104:8103 \
  algorand/algod:latest \
  bash -c '
    cd /data
    
    # 启动网络
    goal network start -r /data
    echo "✅ 网络已启动"
    
    # 保持运行
    tail -f /dev/null
  '

echo "⏳ 等待网络启动..."
sleep 10

echo ""
echo "📊 检查节点状态..."
docker exec algo_private_network_100 bash -c "
  cd /data
  echo 'Relay1:'
  goal node status -d relay1
  echo ''
  echo 'Relay2:'
  goal node status -d relay2
  echo ''
  echo 'Node1:'
  goal node status -d node1
  echo ''
  echo 'Node2:'
  goal node status -d node2
  echo ''
  echo 'Node3:'
  goal node status -d node3
  echo ''
  echo 'Node4:'
  goal node status -d node4
"

echo ""
echo "✅ 私有网络已启动！"