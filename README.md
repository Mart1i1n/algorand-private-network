# Algorand 4节点私有网络 - 从零开始搭建指南

## 📋 目录

1. [前置要求](#前置要求)
2. [第一步：准备环境](#第一步准备环境)
3. [第二步：生成网络配置](#第二步生成网络配置)
4. [第三步：启动网络](#第三步启动网络)
5. [第四步：验证网络](#第四步验证网络)
6. [第五步：使用网络](#第五步使用网络)
7. [性能测试（TPS 8 延迟）](#性能测试tps--延迟)
8. [常用操作](#常用操作)

---

## 前置要求

### 系统要求
- macOS / Linux / Windows (with Docker)
- Docker Desktop 已安装并运行
- Python 3.7+ (用于辅助脚本，推荐 3.11+)
- 至少 2GB 可用磁盘空间
- 至少 4GB RAM

### 检查 Docker

```bash
# 检查 Docker 是否安装
docker --version

# 检查 Docker 是否运行
docker ps
```

如果 Docker 未运行，请启动 Docker Desktop。

---

## 第一步：准备环境

### 1.1 克隆或进入项目目录

```bash
cd /Users/mingfei/Code/algorand-private-network
```

### 1.2 创建 Python 虚拟环境（如果还没有）

**重要：** 确保使用 Python 3.7+ 创建虚拟环境。如果使用 pyenv，先确认版本：

```bash
# 检查 Python 版本
python --version  # 应该显示 3.7 或更高

# 如果使用 pyenv
pyenv versions
# 确保当前版本是 3.7+

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 验证虚拟环境的 Python 版本
python --version

# 安装依赖
pip install py-algorand-sdk
```

**常见问题：** 如果虚拟环境使用了错误的 Python 版本（如系统的 Python 3.6），删除后重建：

```bash
rm -rf venv
python -m venv venv  # 使用正确的 Python 版本
source venv/bin/activate
pip install py-algorand-sdk
```

### 1.3 停止其他 Algorand 网络

确保没有其他 Algorand 网络在运行，避免端口冲突：

```bash
# 停止 AlgoKit LocalNet（如果在运行）
algokit localnet stop

# 停止之前的 docker-compose 网络（如果在运行）
docker-compose down

# 清理旧的私有网络容器（如果存在）
docker stop algo_private_network 2>/dev/null || true
docker rm algo_private_network 2>/dev/null || true
```

---

## 第二步：生成网络配置

### 2.1 理解网络拓扑

我们要创建的网络结构：

```
网络拓扑模板 (network_template.json)
├── Genesis 配置
│   ├── Wallet1 (30% stake, online)
│   ├── Wallet2 (30% stake, online) 
│   ├── Wallet3 (30% stake, online)
│   └── Wallet4 (10% stake, offline - 测试账户)
│
└── 节点配置
    ├── relay  - 中继节点（不参与共识）
    ├── node1  - 参与节点（Wallet1）
    ├── node2  - 参与节点（Wallet2）
    └── node3  - 参与节点（Wallet3）
```

### 2.2 执行配置生成脚本

```bash
./scripts/create_network_config.sh
```

**这个脚本做了什么：**

1. 停止所有现有网络
2. 清理旧配置目录
3. 使用 Docker 运行 `goal network create` 命令
4. 根据 `network_template.json` 生成：
   - `genesis.json` - Genesis 区块配置
   - 4个节点的数据目录 (relay, node1, node2, node3)
   - 4个钱包的根密钥 (Wallet1-4.rootkey)
   - 3个参与密钥 (Wallet1-3.partkey)
   - `network.json` - 网络拓扑和端口配置

**预期输出：**

```
🚀 创建4节点 Algorand 私有网络（使用 goal network）

📦 停止现有网络...
🧹 清理旧配置...
⚙️  生成网络配置（使用 goal network create）...

Created new rootkey: /workspace/private_net_data/Wallet4.rootkey
Created new rootkey: /workspace/private_net_data/Wallet3.rootkey
Created new rootkey: /workspace/private_net_data/Wallet2.rootkey
Created new rootkey: /workspace/private_net_data/Wallet1.rootkey

Generating Wallet3's keys for a period of 3000000 rounds
Generating Wallet1's keys for a period of 3000000 rounds
Generating Wallet2's keys for a period of 3000000 rounds

participation key generation for Wallet2 completed successfully
participation key generation for Wallet3 completed successfully
participation key generation for Wallet1 completed successfully

Network privatenet created under /workspace/private_net_data
✅ 网络配置已生成
```

### 2.3 验证生成的文件

```bash
ls -la private_net_data/
```

应该看到：

```
private_net_data/
├── genesis.json                      # Genesis 配置
├── network.json                      # 网络拓扑
├── Wallet1.rootkey                   # 钱包1根密钥
├── Wallet1.0.3000000.partkey        # 钱包1参与密钥（61MB）
├── Wallet2.rootkey
├── Wallet2.0.3000000.partkey
├── Wallet3.rootkey
├── Wallet3.0.3000000.partkey
├── Wallet4.rootkey
├── relay/                            # Relay节点数据目录
├── node1/                            # Node1数据目录
├── node2/                            # Node2数据目录
└── node3/                            # Node3数据目录
```

---

## 第三步：启动网络

### 3.1 启动所有节点

**推荐方式：使用正确配置启动（确保外部可访问）**

```bash
docker run -d \
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
    tail -f /dev/null
  '
```

**或使用脚本启动（需要先手动配置监听地址）：**

```bash
./scripts/start_goal_network.sh
```

**启动流程说明：**

1. 检查 `private_net_data` 是否存在
2. 启动 Docker 容器 `algo_private_network`
3. 配置节点监听 `0.0.0.0`（允许容器外部访问）
4. 在容器内运行 `goal network start -r /data`
5. 映射端口：
   - 4001:8080 → Relay
   - 4002:8081 → Node1
   - 4003:8082 → Node2
   - 4004:8083 → Node3
6. 等待10秒让节点启动并开始共识

**预期输出：**

```
✅ 网络已启动
```

**验证网络状态：**

```bash
# 等待启动
sleep 10

# 检查节点状态
docker exec algo_private_network goal network status -r /data

# 应该看到类似输出（区块号会随时间增长）：
# [relay]
# Last committed block: 15
# Time since last block: 3.2s
# ...
```

### 3.2 启动 KMD 服务（可选，用于账户管理）

如果需要使用 `goal account` 命令管理账户，需要启动 KMD（Key Management Daemon）：

```bash
# 为每个节点启动 kmd
docker exec algo_private_network goal kmd start -d /data/relay
docker exec algo_private_network goal kmd start -d /data/node1
docker exec algo_private_network goal kmd start -d /data/node2
docker exec algo_private_network goal kmd start -d /data/node3

# 验证 kmd 状态
docker exec algo_private_network goal kmd status -d /data/node1

# 列出账户（需要 kmd 运行）
docker exec algo_private_network goal account list -d /data/node1
```

**注意：** 
- KMD 不是必须的，API 调用不依赖 KMD
- 只有使用 `goal account`、`goal wallet` 等命令时才需要 KMD
- TPS 测试脚本直接从 genesis.json 读取账户信息，不需要 KMD

### 3.2 理解初始状态

**重要说明：** 
- 初始时所有节点都在 **区块 0**
- 网络已启动，但还在等待第一个区块达成共识
- 这是正常的！共识协议需要时间来协调第一个区块
- 通常在启动后 **10-30秒** 内会开始产生区块

---

## 第四步：验证网络

### 4.1 等待区块生成

启动后等待约 15-30 秒，然后检查：

```bash
docker exec algo_private_network goal network status -r /data
```

你应该看到区块号 **不再是 0**，例如：

```
[relay]
Last committed block: 15
Time since last block: 3.2s

[node1]
Last committed block: 15
Time since last block: 3.4s

[node2]
Last committed block: 15
Time since last block: 3.4s

[node3]
Last committed block: 15
Time since last block: 3.4s
```

**关键指标：**
- ✅ `Last committed block` > 0
- ✅ 所有节点的区块号相同（同步）
- ✅ `Time since last block` < 5秒（区块在持续生成）

### 4.2 运行自动化测试

```bash
./scripts/test_goal_network.sh
```

**预期输出：**

```
🧪 测试多节点私有网络

📋 账户:
  Wallet1 (在线): LZVXPGVN7E...
  Wallet4 (离线): HONINWDJCZ...

📊 当前网络状态:
Last committed block: 23

🚀 发送测试交易 (Wallet1 -> Wallet4, 1 ALGO)...

⏳ 等待区块生成...
  Round: 24 (1/15)

✅ 区块已生成！

Last committed block: 25
Last committed block: 25
Last committed block: 25
Last committed block: 25

🎉 多节点私有网络测试成功！
```

### 4.3 检查共识日志（可选）

查看节点是否在正常运行共识协议：

```bash
docker exec algo_private_network tail -50 /data/node1/node.log | grep Agreement
```

应该看到类似：

```
"Type":"VoteAccepted" - 投票被接受
"Type":"BlockCommittable" - 区块可提交
"Type":"VoteBroadcast" - 投票广播
```

---

## 第五步：使用网络

### 5.1 查看账户信息

获取所有账户地址：

```bash
cat private_net_data/genesis.json | python3 -c "
import json, sys
gen = json.load(sys.stdin)
for item in gen['alloc']:
    if 'Wallet' in item.get('comment', ''):
        algo = item['state']['algo'] / 1000000
        print(f\"{item['comment']:10s} {item['addr'][:10]}... - {algo:,.0f} ALGO\")
"
```

输出：

```
Wallet1    LZVXPGVN7E... - 3,000,000,000 ALGO
Wallet2    3PCKL4LMP6... - 3,000,000,000 ALGO
Wallet3    T5RAOSOAOO... - 3,000,000,000 ALGO
Wallet4    HONINWDJCZ... - 3,000,000,000 ALGO
```

### 5.2 使用 Python SDK 连接

创建测试脚本：

```python
from algosdk.v2client import algod

# 连接到 relay 节点
# Token 可从 private_net_data/network.json 获取
client = algod.AlgodClient(
    "your-token-from-network.json",
    "http://localhost:4001"
)

# 查看状态
status = client.status()
print(f"当前轮次: {status['last-round']}")
print(f"Genesis ID: {status.get('genesis-id')}")

# 查看账户
addr = "LZVXPGVN7ENCRQYMGIUC25CNRR4SF6FJOBP7RMEBUCMRBJYCRLUE7B4PGY"
account_info = client.account_info(addr)
print(f"余额: {account_info['amount']/1000000:,.0f} ALGO")
```

### 5.3 查看实时区块生成

持续监控区块生成：

```bash
watch -n 2 'docker exec algo_private_network goal node status -d /data/relay | grep "Last committed block"'
```

按 `Ctrl+C` 停止监控。

---

## 性能测试（TPS & 延迟）

使用独立的 Python 脚本对已启动的私有网络进行性能测试。

### 快速开始

1. 确认网络在运行：
  ```bash
  docker ps --filter name=algo_private_network
  ```

2. 运行测试（示例：5 轮 × 500 笔，总 2500 笔）：
  ```bash
  # 方式1：直接运行 Python 脚本
  source venv/bin/activate
  TPS_ROUNDS=5 TPS_TX_PER_ROUND=500 python3 scripts/tps_test.py
  
  # 方式2：使用 shell 包装脚本
  TPS_ROUNDS=5 TPS_TX_PER_ROUND=500 timeout 900 ./scripts/test_private_network_tps.sh
  ```

**环境变量：**
- `TPS_ROUNDS`（默认 3）：测试轮次
- `TPS_TX_PER_ROUND`（默认 30）：每轮交易数

**输出信息：**
- 每轮的发送耗时/发送 TPS
- 确认情况、总 TPS、估算延迟
- 最后汇总平均值，并写入 `private_network_tps_results.json`

### 脚本说明

- `scripts/tps_test.py` - 独立的 Python 测试脚本，可直接运行
- `scripts/test_private_network_tps.sh` - Shell 包装脚本，调用 Python 脚本

### 已观测的结果（私有网默认配置）
- 5×500（2500 笔）：平均发送 TPS ~420，总 TPS ~64，平均延迟 ~15s
- 5×1000（5000 笔）：平均发送 TPS ~220，总 TPS ~60，平均延迟 ~31s（延迟随负载上升）

提示：若需显著提升“总 TPS”，需调整节点配置（缩短出块间隔、提高单块容量/交易池），然后重启网络再压测。

---

## 常用操作

### 查看网络状态

```bash
# 所有节点状态
docker exec algo_private_network goal network status -r /data

# 单个节点状态
docker exec algo_private_network goal node status -d /data/relay
docker exec algo_private_network goal node status -d /data/node1
```

### 查看日志

```bash
# 容器日志
docker logs -f algo_private_network

# 单个节点日志
docker exec algo_private_network tail -f /data/node1/node.log
```

### 查看参与密钥

```bash
docker exec algo_private_network goal account listpartkeys -d /data/node1
```

### 管理 KMD 服务

```bash
# 启动 kmd（如果需要使用 goal account 命令）
docker exec algo_private_network goal kmd start -d /data/node1

# 检查 kmd 状态
docker exec algo_private_network goal kmd status -d /data/node1

# 停止 kmd
docker exec algo_private_network goal kmd stop -d /data/node1
```

### 使用 goal account 命令

```bash
# 列出账户（需要 kmd 运行）
docker exec algo_private_network goal account list -d /data/node1

# 查看账户余额
docker exec algo_private_network goal account balance -a <ADDRESS> -d /data/node1

# 导出账户私钥
docker exec algo_private_network goal account export -a <ADDRESS> -d /data/node1
```

### 停止网络

```bash
docker stop algo_private_network
```

### 重新启动网络

```bash
# 停止（如果在运行）
docker stop algo_private_network

# 重新启动
./scripts/start_goal_network.sh
```

### 完全重置网络

如果需要从头开始：

```bash
# 停止并删除容器
docker stop algo_private_network 2>/dev/null || true
docker rm algo_private_network 2>/dev/null || true

# 删除所有配置
rm -rf private_net_data

# 重新生成配置
./scripts/create_network_config.sh

# 启动网络
./scripts/start_goal_network.sh
```

---

## 🎯 快速参考

### 完整启动流程（首次）

```bash
# 0. 配置环境
cd /path/to/algorand-private-network

# 1. 停止其他网络
algokit localnet stop 2>/dev/null || true
docker-compose down 2>/dev/null || true

# 2. 生成配置
./scripts/create_network_config.sh

# 3. 启动网络（推荐方式）
docker run -d \
  --name algo_private_network \
  -v "$PWD/private_net_data:/data" \
  -p 4001:8080 -p 4002:8081 -p 4003:8082 -p 4004:8083 \
  algorand/algod:latest \
  bash -c '
    echo "0.0.0.0:8080" > /data/relay/algod-listen.net
    echo "0.0.0.0:8081" > /data/node1/algod-listen.net
    echo "0.0.0.0:8082" > /data/node2/algod-listen.net
    echo "0.0.0.0:8083" > /data/node3/algod-listen.net
    cd /data && goal network start -r /data
    echo "✅ 网络已启动"
    tail -f /dev/null
  '

# 4. 等待区块生成（15-30秒）
sleep 15

# 5. 验证区块在增长
for i in {1..5}; do
  echo "=== 检查 $i/5 ==="
  docker exec algo_private_network goal network status -r /data | grep "Last committed block"
  sleep 5
done

# 6. 运行测试
source venv/bin/activate
./scripts/test_goal_network.sh
```

### 日常启动流程（配置已存在）

```bash
# 如果容器已停止
docker start algo_private_network

# 验证
docker exec algo_private_network goal network status -r /data
```

### 完全重置流程

```bash
# 停止并清理
docker stop algo_private_network 2>/dev/null || true
docker rm algo_private_network 2>/dev/null || true
rm -rf private_net_data

# 按首次启动流程重新开始
./scripts/create_network_config.sh
# ... (见上方完整启动流程)
```

### 端口映射

| 节点 | 容器端口 | 主机端口 | API URL | Token 文件路径 |
|------|---------|---------|---------|---------------|
| Relay | 8080 | 4001 | http://localhost:4001 | private_net_data/relay/algod.token |
| Node1 | 8081 | 4002 | http://localhost:4002 | private_net_data/node1/algod.token |
| Node2 | 8082 | 4003 | http://localhost:4003 | private_net_data/node2/algod.token |
| Node3 | 8083 | 4004 | http://localhost:4004 | private_net_data/node3/algod.token |

### 测试 API 连接

```bash
# 测试 Relay 节点
curl -s http://localhost:4001/v2/status \
  -H "X-Algo-API-Token: $(cat private_net_data/relay/algod.token)" | python3 -m json.tool

# 测试 Node1
curl -s http://localhost:4002/v2/status \
  -H "X-Algo-API-Token: $(cat private_net_data/node1/algod.token)" | python3 -m json.tool
```

---

## ❓ 常见问题

### Q1: 区块一直停在某个数字不增长怎么办？

**A:** 网络共识可能停止了，需要完全重置：

```bash
# 完全重置网络
docker stop algo_private_network
docker rm algo_private_network
rm -rf private_net_data

# 重新创建
./scripts/create_network_config.sh

# 启动（使用正确配置）
docker run -d \
  --name algo_private_network \
  -v "$PWD/private_net_data:/data" \
  -p 4001:8080 -p 4002:8081 -p 4003:8082 -p 4004:8083 \
  algorand/algod:latest \
  bash -c '
    echo "0.0.0.0:8080" > /data/relay/algod-listen.net
    echo "0.0.0.0:8081" > /data/node1/algod-listen.net
    echo "0.0.0.0:8082" > /data/node2/algod-listen.net
    echo "0.0.0.0:8083" > /data/node3/algod-listen.net
    cd /data && goal network start -r /data
    tail -f /dev/null
  '

# 验证区块增长
sleep 10
docker exec algo_private_network goal network status -r /data | grep "Last committed block"
```

### Q2: API 返回 502 Bad Gateway 或连接被拒绝

**A:** 节点没有监听 0.0.0.0，只监听了 127.0.0.1。需要创建 `algod-listen.net` 文件：

```bash
# 停止网络
docker exec algo_private_network goal network stop -r /data

# 配置监听地址
docker exec algo_private_network bash -c '
  echo "0.0.0.0:8080" > /data/relay/algod-listen.net
  echo "0.0.0.0:8081" > /data/node1/algod-listen.net
  echo "0.0.0.0:8082" > /data/node2/algod-listen.net
  echo "0.0.0.0:8083" > /data/node3/algod-listen.net
'

# 重启网络
docker exec algo_private_network goal network start -r /data

# 测试连接
curl -s http://localhost:4001/v2/status \
  -H "X-Algo-API-Token: $(cat private_net_data/relay/algod.token)"
```

### Q3: Python 版本不兼容（capture_output 错误）

**A:** 虚拟环境使用了 Python 3.6，需要重建：

```bash
rm -rf venv
python --version  # 确认是 3.7+
python -m venv venv
source venv/bin/activate
pip install py-algorand-sdk
```

### Q4: goal account list 报错：connection refused

**A:** KMD 服务未运行，需要启动：

```bash
# 启动 kmd
docker exec algo_private_network goal kmd start -d /data/node1

# 验证
docker exec algo_private_network goal kmd status -d /data/node1

# 再次尝试
docker exec algo_private_network goal account list -d /data/node1
```

**注意：** 如果只使用 API 而不使用 `goal account` 命令，不需要启动 KMD。

### Q5: 容器无法启动或端口被占用

**A:** 检查端口并清理冲突：

```bash
# 检查端口占用
lsof -i :4001
netstat -tlnp | grep 4001

# 停止所有 Algorand 相关容器
docker stop $(docker ps -q --filter ancestor=algorand/algod)
docker rm $(docker ps -aq --filter ancestor=algorand/algod)
```

### Q6: 如何备份网络配置？

**A:** 复制整个数据目录：

```bash
cp -r private_net_data private_net_data.backup
```

### Q7: 参与密钥什么时候过期？

**A:** 参与密钥有效期为 3,000,000 轮次。以每轮 4.5 秒计算，约 156 天。

---

## ✅ 成功标志清单

启动完成后，确认：

- [ ] 容器 `algo_private_network` 正在运行 (`docker ps`)
- [ ] 所有4个节点状态正常（无错误信息）
- [ ] 区块号 > 0 且持续增长（每5秒观察一次，连续3次都在增长）
- [ ] 所有节点区块号相同（同步）
- [ ] API 可以正常访问（curl 返回 JSON 而不是 502/连接拒绝）
- [ ] 测试脚本返回成功

**验证命令：**

```bash
# 1. 容器运行
docker ps --filter name=algo_private_network

# 2. 区块增长测试
for i in {1..3}; do
  docker exec algo_private_network goal network status -r /data | grep "Last committed block"
  sleep 5
done

# 3. API 连接测试
curl -s http://localhost:4001/v2/status \
  -H "X-Algo-API-Token: $(cat private_net_data/relay/algod.token)" | python3 -m json.tool | head -5

# 4. 运行完整测试
source venv/bin/activate
./scripts/test_goal_network.sh
```

**恭喜！你的4节点 Algorand 私有网络已成功运行！** 🎉

---

## 📚 相关文档

- [完整使用指南](PRIVATE_NETWORK_GUIDE.md)
- [Algorand 官方文档](https://developer.algorand.org/)
- [Goal CLI 参考](https://developer.algorand.org/docs/clis/goal/goal/)
