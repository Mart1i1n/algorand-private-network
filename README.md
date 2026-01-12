# Algorand 4节点私有网络 - 从零开始搭建指南

本项目提供一个完全自动化的 Algorand 4节点私有网络搭建方案，支持 TPS 性能测试。

## 🚀 快速开始

```bash
# 1. 生成网络配置（自动配置 API 端点）
./scripts/create_network_config.sh

# 2. 启动网络
./scripts/start_goal_network.sh

# 3. 验证 API 访问
curl -H "X-Algo-API-Token: $(cat private_net_data/relay/algod.token)" \
  http://localhost:4001/v2/status

# 4. 运行 TPS 测试（可选）
source venv/bin/activate
python3 scripts/tps_test.py
```

> **重要：** `private_net_data/` 目录不在版本控制中（已在 `.gitignore` 中）。每次需要重新生成时，运行 `./scripts/create_network_config.sh` 即可自动配置好所有必要设置，无需手动修改配置文件。

---

## 📋 目录

1. [前置要求](#前置要求)
2. [第一步：准备环境](#第一步准备环境)
3. [第二步：生成网络配置](#第二步生成网络配置)
4. [第三步：启动网络](#第三步启动网络)
5. [第四步：验证网络](#第四步验证网络)
6. [第五步：使用网络](#第五步使用网络)
7. [性能测试（TPS & 延迟）](#性能测试tps--延迟)
8. [故障排除](#故障排除)
9. [常用操作](#常用操作)

---

## 前置要求

### 系统要求
- macOS / Linux / Windows (with Docker)
- Docker Desktop 已安装并运行
- Python 3.7+ (用于tps)
- 至少 2GB 可用磁盘空间
- 至少 4GB RAM

### 检查 Docker

```bash
# 检查 Docker 是否安装
docker --version

# 检查 Docker 是否运行
docker ps
```

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

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 验证虚拟环境的 Python 版本
python --version

# 安装依赖
pip install py-algorand-sdk
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

**脚本会自动完成：**
1. 停止现有网络（如果存在）
2. 清理旧配置
3. 使用 `goal network create` 生成网络配置
4. **自动配置 API 端点**（允许外部访问）

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

🔧 配置 API 端点...
  ✅ relay: 0.0.0.0:8080
  ✅ node1: 0.0.0.0:8081
  ✅ node2: 0.0.0.0:8082
  ✅ node3: 0.0.0.0:8083

✅ 网络配置完成！
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
│   └── config.json                   # 已配置 EndpointAddress: 0.0.0.0:8080
├── node1/                            # Node1数据目录
│   └── config.json                   # 已配置 EndpointAddress: 0.0.0.0:8081
├── node2/                            # Node2数据目录
│   └── config.json                   # 已配置 EndpointAddress: 0.0.0.0:8082
└── node3/                            # Node3数据目录
    └── config.json                   # 已配置 EndpointAddress: 0.0.0.0:8083
```

> **重要提示：** `private_net_data/` 目录不会提交到版本控制（已在 `.gitignore` 中）。每次需要重新生成时，运行 `./scripts/create_network_config.sh` 即可自动配置好所有必要设置。

---

## 第三步：启动网络

### 3.1 启动所有节点

```bash
./scripts/start_goal_network.sh
```

**启动流程说明：**

1. 检查 `private_net_data` 是否存在
2. 启动 Docker 容器 `algo_private_network`
3. 在容器内运行 `goal network start -r /data`
4. 映射端口：
   - 4001:8080 → Relay
   - 4002:8081 → Node1
   - 4003:8082 → Node2
   - 4004:8083 → Node3
5. 等待10秒让节点启动并开始共识

**预期输出：**

```
🚀 启动4节点 Algorand 私有网络

[容器ID]
⏳ 等待网络启动...

📊 检查节点状态...
Relay:
Last committed block: 0
Time since last block: 0.0s
...
✅ 私有网络已启动！
```

**验证网络状态：**

```bash
# 检查节点状态
docker exec algo_private_network goal network status -r /data

# 应该看到类似输出（区块号会随时间增长）：
# [relay]
# Last committed block: 15
# Time since last block: 3.2s
# ...
```

---

## 第四步：验证网络

### 4.1 等待区块生成

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

### 4.2 验证 API 访问

由于我们配置了 `EndpointAddress: 0.0.0.0:端口`，现在可以从主机访问 Algorand API：

```bash
# 获取 API token
cat private_net_data/relay/algod.token

# 测试 relay 节点 API（端口 4001）
curl -H "X-Algo-API-Token: $(cat private_net_data/relay/algod.token)" \
  http://localhost:4001/v2/status | python3 -m json.tool

# 应该看到 JSON 响应，包含：
# {
#   "last-round": 15,
#   "last-version": "...",
#   "next-version": "...",
#   ...
# }
```

**端口映射：**
- `http://localhost:4001` → Relay 节点
- `http://localhost:4002` → Node1
- `http://localhost:4003` → Node2
- `http://localhost:4004` → Node3

### 4.3 运行自动化测试

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

## 故障排除

### 问题 1：API 连接失败 (HTTP 502 Bad Gateway)

**症状：**
```bash
python3 scripts/tps_test.py
# ❌ 无法连接网络: HTTP Error 502: Bad Gateway
```

**原因：**
- `EndpointAddress` 未配置，节点 API 只监听 `127.0.0.1`（容器内部）
- Docker 端口映射无法访问

**解决方案：**
```bash
# 1. 重新生成配置（会自动配置 EndpointAddress）
./scripts/create_network_config.sh

# 2. 重启网络
docker stop algo_private_network
./scripts/start_goal_network.sh

# 3. 验证 API 端点
docker exec algo_private_network cat /data/relay/algod.net
# 应该显示: [::]:8080 或 0.0.0.0:8080

# 4. 测试连接
curl -H "X-Algo-API-Token: $(cat private_net_data/relay/algod.token)" \
  http://localhost:4001/v2/status
```

### 问题 2：容器名称冲突

**症状：**
```
Error: The container name "/algo_private_network" is already in use
```

**解决方案：**
```bash
# 停止并删除现有容器
docker stop algo_private_network
docker rm algo_private_network

# 或使用强制删除
docker rm -f algo_private_network

# 重新启动
./scripts/start_goal_network.sh
```

### 问题 3：网络配置丢失

**症状：**
```
❌ 网络配置不存在，请先运行: ./scripts/create_network_config.sh
```

**原因：**
`private_net_data/` 目录不在版本控制中，可能被删除或未生成

**解决方案：**
```bash
# 重新生成网络配置
./scripts/create_network_config.sh

# 启动网络
./scripts/start_goal_network.sh
```

### 问题 4：节点无法启动或共识失败

**症状：**
- 区块号一直为 0
- `Time since last block` 持续增加

**解决方案：**
```bash
# 1. 查看节点日志
docker exec algo_private_network tail -100 /data/relay/node.log

# 2. 检查所有节点状态
docker exec algo_private_network goal network status -r /data

# 3. 如果问题持续，重新生成配置
docker stop algo_private_network
rm -rf private_net_data
./scripts/create_network_config.sh
./scripts/start_goal_network.sh
```

### 问题 5：手动修改配置后失效

**注意：** 由于 `private_net_data/` 不在版本控制中，手动修改的配置会在重新生成时丢失。

**正确做法：**
1. 修改 `create_network_config.sh` 脚本，在生成配置后自动应用修改
2. 或修改 `network_template.json` 模板文件
3. 重新运行 `./scripts/create_network_config.sh`

**示例 - 修改区块时间：**
编辑 `network_template.json`，在 Genesis 配置中添加：
```json
{
  "Genesis": {
    "ConsensusProtocol": "future",
    "NetworkName": "privatenet",
    // 添加共识参数
    "Proto": {
      "AgreementFilterTimeoutPeriod0": 1000000000  // 1秒
    }
  }
}
```

---

## 常用命令速查

```bash
# 生成网络配置
./scripts/create_network_config.sh

# 启动网络
./scripts/start_goal_network.sh

# 停止网络
docker stop algo_private_network

# 查看状态
docker exec algo_private_network goal network status -r /data

# 查看日志
docker logs -f algo_private_network

# 运行 TPS 测试
source venv/bin/activate
python3 scripts/tps_test.py

# 清理并重新开始
docker stop algo_private_network
rm -rf private_net_data
./scripts/create_network_config.sh
./scripts/start_goal_network.sh
```