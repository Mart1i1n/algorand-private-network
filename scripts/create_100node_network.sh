#!/bin/bash
# 创建500节点 Algorand 私有网络配置

set -e

cd "$(dirname "$0")/.."

echo "🚀 创建100节点 Algorand 私有网络"
echo "  - 2 个 Relay 节点"
echo "  - 4 个 Participating 节点 (Committee Size = 4)"
echo "  - 94 个非 Participating 节点"
echo ""

# 停止现有网络
if docker ps -a | grep -q algo_private_network_100; then
  echo "📦 停止现有网络..."
  docker stop algo_private_network_100 2>/dev/null || true
  docker rm algo_private_network_100 2>/dev/null || true
fi

# 清理旧配置
echo "🧹 清理旧配置..."
rm -rf private_net_data_100nodes
mkdir -p private_net_data_100nodes

# 检查模板文件是否存在
if [ ! -f "network_template_100nodes.json" ]; then
  echo "❌ 错误: network_template_100nodes.json 不存在"
  echo "请先运行: python3 scripts/generate_100node_template.py"
  exit 1
fi

# 使用 Docker 运行 goal network create
echo ""
echo "⚙️  生成网络配置（这可能需要几分钟...）"

docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  algorand/algod:latest \
  bash -c "
    goal network create \
      -r /workspace/private_net_data_100nodes \
      -n privatenet100 \
      -t /workspace/network_template_100nodes.json
    
    echo '✅ 网络配置已生成'
  "

# 修改共识参数：设置 CertCommitteeSize = 4
echo ""
echo "🔧 配置共识参数 (CertCommitteeSize = 4)..."

python3 << 'PYTHON_SCRIPT'
import json
import os
import glob

# 遍历所有节点目录
node_dirs = glob.glob('private_net_data_100nodes/*/consensus.json')
print(f"找到 {len(node_dirs)} 个节点的 consensus.json")

for consensus_file in node_dirs:
    node_name = os.path.basename(os.path.dirname(consensus_file))
    
    with open(consensus_file, 'r') as f:
        consensus = json.load(f)
    
    # 备份
    backup_file = consensus_file + '.backup'
    with open(backup_file, 'w') as f:
        json.dump(consensus, f, indent=2)
    
    # 修改所有协议版本的 CertCommitteeSize
    modified_count = 0
    for protocol, params in consensus.items():
        if isinstance(params, dict) and 'CertCommitteeSize' in params:
            old_value = params['CertCommitteeSize']
            params['CertCommitteeSize'] = 4
            # 同时调整 CertCommitteeThreshold (75% of committee size)
            params['CertCommitteeThreshold'] = 3
            modified_count += 1
    
    with open(consensus_file, 'w') as f:
        json.dump(consensus, f, indent=2)
    
    print(f"  ✅ {node_name}: 修改了 {modified_count} 个协议版本")

print(f"\n✅ 共识参数配置完成")
print(f"  CertCommitteeSize: 1500 → 4")
print(f"  CertCommitteeThreshold: 1112 → 3")
PYTHON_SCRIPT

# 配置节点性能参数和端口
echo ""
echo "🔧 配置节点性能参数和端口..."

python3 << 'PYTHON_CONFIG'
import json
import os
import glob

node_dirs = glob.glob('private_net_data_100nodes/*/')
print(f"配置 {len(node_dirs)} 个节点...")

for node_dir in sorted(node_dirs):
    node_name = os.path.basename(node_dir.rstrip('/'))
    config_file = os.path.join(node_dir, 'config.json')
    
    if not os.path.exists(config_file):
        continue
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # 基础优化配置
    config['TxPoolSize'] = 50000
    config['TxBacklogSize'] = 50000
    config['EnableTxBacklogRateLimiting'] = False
    config['BaseLoggerDebugLevel'] = 1
    
    # 为relay节点和所有4个participating节点配置端口
    if 'relay' in node_name:
        # relay1: 8080, relay2: 8081
        relay_num = int(node_name.replace('relay', ''))
        port = 8080 + relay_num - 1
        config['EndpointAddress'] = f'0.0.0.0:{port}'
        print(f"  ✅ {node_name}: 0.0.0.0:{port}")
    elif node_name.startswith('node'):
        # 所有4个participating节点都暴露端口
        try:
            node_num = int(node_name.replace('node', ''))
            if node_num <= 4:
                port = 8100 + node_num - 1
                config['EndpointAddress'] = f'0.0.0.0:{port}'
                print(f"  ✅ {node_name}: 0.0.0.0:{port}")
        except:
            pass
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent='\t')

print(f"  ✅ 配置完成（2个relay + 4个participating节点可访问）")
PYTHON_CONFIG

echo ""
echo "✅ 100节点网络配置完成！"
