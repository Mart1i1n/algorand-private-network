#!/usr/bin/env python3
"""
分析延迟数据，去除极端值
"""
import json
import numpy as np
from algosdk.v2client import algod

# 加载测试结果
with open('sustained_load_results.json', 'r') as f:
    data = json.load(f)

print('='*80)
print('持续负载测试 - 去除极端值的 Latency 分析')
print('='*80)

# 基础数据
total_sent = data['total_sent']
start_round = data['start_round']
end_round = data['end_round']
blocks_with_tx = data['blocks_with_tx']

block_time = 4.5  # 秒

# 获取所有区块的交易数
with open('private_net_data/relay/algod.token') as f:
    token = f.read().strip()
client = algod.AlgodClient(token, 'http://localhost:4001')

# 收集所有区块的数据
print(f'\n📊 收集区块数据 ({start_round} -> {end_round})...')
blocks_data = []
for round_num in range(start_round, end_round + 1):
    try:
        block = client.block_info(round_num)
        txns = block.get('block', {}).get('txns', [])
        if len(txns) > 0:
            blocks_data.append({
                'round': round_num,
                'tx_count': len(txns),
                'relative_round': round_num - start_round
            })
    except:
        pass

print(f'  找到 {len(blocks_data)} 个包含交易的区块')

# 计算每笔交易的平均延迟（基于区块位置）
tx_latencies = []
cumulative_tx = 0

for block in blocks_data:
    tx_count = block['tx_count']
    relative_round = block['relative_round']
    
    # 为这个区块中的每笔交易记录延迟（单位：区块）
    for _ in range(tx_count):
        # 估算：假设交易在测试开始后均匀发送
        send_time_block = cumulative_tx / (total_sent / (end_round - start_round))
        # 延迟 = 确认区块 - 发送区块
        latency_blocks = relative_round - send_time_block
        if latency_blocks > 0:  # 只计算正值
            tx_latencies.append(latency_blocks)
        cumulative_tx += 1

# 转换为秒
tx_latencies_seconds = [l * block_time for l in tx_latencies]

# 统计分析
if tx_latencies_seconds:
    latencies = np.array(tx_latencies_seconds)
    
    print(f'\n⏱  原始延迟统计 (包含所有数据):')
    print(f'  样本数: {len(latencies):,} 笔交易')
    print(f'  平均: {np.mean(latencies):.1f} 秒')
    print(f'  中位数: {np.median(latencies):.1f} 秒')
    print(f'  最小: {np.min(latencies):.1f} 秒')
    print(f'  最大: {np.max(latencies):.1f} 秒')
    print(f'  标准差: {np.std(latencies):.1f} 秒')
    
    # 去除极端值 - 使用 Percentile 方法
    print(f'\n📊 去除极端值后的延迟统计:')
    
    # 方法1: 去除最高和最低 10%
    p10 = np.percentile(latencies, 10)
    p90 = np.percentile(latencies, 90)
    filtered_80 = latencies[(latencies >= p10) & (latencies <= p90)]
    
    print(f'\n  去除最高最低 10% (保留中间 80%):')
    print(f'    样本数: {len(filtered_80):,} 笔')
    print(f'    平均延迟: {np.mean(filtered_80):.1f} 秒')
    print(f'    中位数: {np.median(filtered_80):.1f} 秒')
    print(f'    范围: {np.min(filtered_80):.1f}s - {np.max(filtered_80):.1f}s')
    
    # 方法2: 去除最高和最低 5%
    p5 = np.percentile(latencies, 5)
    p95 = np.percentile(latencies, 95)
    filtered_90 = latencies[(latencies >= p5) & (latencies <= p95)]
    
    print(f'\n  去除最高最低 5% (保留中间 90%):')
    print(f'    样本数: {len(filtered_90):,} 笔')
    print(f'    平均延迟: {np.mean(filtered_90):.1f} 秒')
    print(f'    中位数: {np.median(filtered_90):.1f} 秒')
    print(f'    范围: {np.min(filtered_90):.1f}s - {np.max(filtered_90):.1f}s')
    
    # 方法3: 使用 IQR (四分位距) 方法去除离群值
    q1 = np.percentile(latencies, 25)
    q3 = np.percentile(latencies, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    filtered_iqr = latencies[(latencies >= lower_bound) & (latencies <= upper_bound)]
    
    print(f'\n  IQR 方法去除离群值:')
    print(f'    样本数: {len(filtered_iqr):,} 笔')
    print(f'    平均延迟: {np.mean(filtered_iqr):.1f} 秒')
    print(f'    中位数: {np.median(filtered_iqr):.1f} 秒')
    print(f'    范围: {np.min(filtered_iqr):.1f}s - {np.max(filtered_iqr):.1f}s')
    print(f'    Q1 (25%): {q1:.1f}s')
    print(f'    Q3 (75%): {q3:.1f}s')
    
    # Percentile 分布
    print(f'\n📈 延迟分布 (Percentile):')
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    for p in percentiles:
        value = np.percentile(latencies, p)
        print(f'    P{p:2d}: {value:6.1f} 秒')
    
    # 推荐的延迟指标
    print(f'\n{'='*80}')
    print(f'🎯 推荐的延迟指标 (去除极端值)')
    print(f'{'='*80}')
    print(f'中位数延迟 (P50):     {np.median(latencies):7.1f} 秒  ⭐ (最稳健)')
    print(f'修正平均延迟 (IQR):   {np.mean(filtered_iqr):7.1f} 秒  ⭐ (推荐)')
    print(f'P90 延迟:             {np.percentile(latencies, 90):7.1f} 秒  (90%交易的延迟)')
    print(f'P95 延迟:             {np.percentile(latencies, 95):7.1f} 秒  (95%交易的延迟)')
    print(f'{'='*80}')

else:
    print('没有足够的数据进行延迟分析')
