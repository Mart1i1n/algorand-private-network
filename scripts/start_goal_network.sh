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
    # 配置所有节点监听 0.0.0.0（允许外部访问）
    echo "0.0.0.0:8080" > /data/relay/algod-listen.net
    echo "0.0.0.0:8081" > /data/node1/algod-listen.net
    echo "0.0.0.0:8082" > /data/node2/algod-listen.net
    echo "0.0.0.0:8083" > /data/node3/algod-listen.net
    
    cd /data
    goal network start -r /data
    echo "✅ 网络已启动"
    
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
echo "节点信息："
echo "  Relay: http://localhost:4001"
echo "  Node1: http://localhost:4002"
echo "  Node2: http://localhost:4003"
echo "  Node3: http://localhost:4004"
echo ""
echo "管理命令："
echo "  查看状态: docker exec algo_private_network goal network status -r /data"
echo "  停止网络: docker stop algo_private_network"
echo "  查看日志: docker logs -f algo_private_network"
echo ""
echo "测试网络:"
echo "  ./scripts/test_goal_network.sh"
echo ""
echo "验证区块增长:"
echo "  for i in {1..3}; do docker exec algo_private_network goal network status -r /data | grep 'Last committed block'; sleep 5; done"
echo ""
