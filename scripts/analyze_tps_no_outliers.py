#!/usr/bin/env python3
"""
分析TPS数据，去除极端值（启动和结束阶段）
"""
import json
import numpy as np
from algosdk.v2client import algod

# 加载测试结果
with open('sustained_load_results.json', 'r') as f:
    data = json.load(f)

print('='*80)
print('持续负载测试 - 去除极端值的 TPS 分析')
print('='*80)

# 基础数据
total_sent = data['total_sent']
duration = data['duration_seconds']
start_round = data['start_round']
end_round = data['end_round']

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
        blocks_data.append({
            'round': round_num,
            'tx_count': len(txns),
            'has_tx': len(txns) > 0
        })
    except:
        pass

print(f'  收集了 {len(blocks_data)} 个区块')
blocks_with_tx = [b for b in blocks_data if b['has_tx']]
print(f'  其中 {len(blocks_with_tx)} 个包含交易')

# 原始TPS统计
print(f'\n📈 原始 TPS 统计:')
total_rounds = end_round - start_round
confirmation_tps = total_sent / (total_rounds * block_time)
effective_tps = total_sent / (len(blocks_with_tx) * block_time)

print(f'  基于所有区块: {confirmation_tps:.1f} 笔/秒')
print(f'  基于含交易区块: {effective_tps:.1f} 笔/秒')

# 去除启动和结束阶段的极端值
# 方法1: 去除前后10%的区块
print(f'\n📊 去除极端值后的 TPS (稳态分析):')

# 找到第一个和最后一个包含交易的区块
first_tx_block = next(b['round'] for b in blocks_data if b['has_tx'])
last_tx_block = next(b['round'] for b in reversed(blocks_data) if b['has_tx'])

print(f'\n  实际测试区间: 区块 {first_tx_block} -> {last_tx_block}')

# 去除前后10%
num_blocks_with_tx = len(blocks_with_tx)
skip_count = int(num_blocks_with_tx * 0.1)

blocks_with_tx_sorted = sorted(blocks_with_tx, key=lambda x: x['round'])
stable_blocks = blocks_with_tx_sorted[skip_count:-skip_count] if skip_count > 0 else blocks_with_tx_sorted

stable_tx_count = sum(b['tx_count'] for b in stable_blocks)
stable_block_count = len(stable_blocks)
stable_duration = stable_block_count * block_time

stable_tps = stable_tx_count / stable_duration

print(f'\n  去除前后 10% 区块 (保留中间 80%):')
print(f'    稳态区块: {stable_block_count} 个')
print(f'    稳态交易: {stable_tx_count:,} 笔')
print(f'    稳态时长: {stable_duration:.0f} 秒')
print(f'    稳态 TPS: {stable_tps:.1f} 笔/秒 ⭐')

# 按时间窗口计算TPS（滑动窗口）
print(f'\n  滑动窗口分析 (10个区块窗口):')
window_size = 10
window_tps_list = []

for i in range(len(blocks_data) - window_size + 1):
    window = blocks_data[i:i+window_size]
    window_tx = sum(b['tx_count'] for b in window)
    if window_tx > 0:  # 只统计有交易的窗口
        window_tps = window_tx / (window_size * block_time)
        window_tps_list.append(window_tps)

if window_tps_list:
    window_tps_array = np.array(window_tps_list)
    
    print(f'    窗口数量: {len(window_tps_list)}')
    print(f'    平均 TPS: {np.mean(window_tps_array):.1f} 笔/秒')
    print(f'    中位数 TPS: {np.median(window_tps_array):.1f} 笔/秒 ⭐')
    print(f'    最大 TPS: {np.max(window_tps_array):.1f} 笔/秒')
    print(f'    最小 TPS: {np.min(window_tps_array):.1f} 笔/秒')
    print(f'    标准差: {np.std(window_tps_array):.1f}')

# 每个区块的TPS（瞬时TPS）
print(f'\n  单区块瞬时 TPS 分析:')
block_tps_list = []
for b in blocks_with_tx:
    if b['tx_count'] > 0:
        block_tps = b['tx_count'] / block_time
        block_tps_list.append(block_tps)

if block_tps_list:
    block_tps_array = np.array(block_tps_list)
    
    print(f'    样本数: {len(block_tps_list)} 个区块')
    print(f'    平均: {np.mean(block_tps_array):.1f} 笔/秒')
    print(f'    中位数: {np.median(block_tps_array):.1f} 笔/秒')
    print(f'    最大: {np.max(block_tps_array):.1f} 笔/秒')
    
    # Percentile分布
    print(f'\n    Percentile 分布:')
    for p in [10, 25, 50, 75, 90, 95, 99]:
        value = np.percentile(block_tps_array, p)
        print(f'      P{p:2d}: {value:7.1f} 笔/秒')
    
    # 去除最高最低10%
    p10 = np.percentile(block_tps_array, 10)
    p90 = np.percentile(block_tps_array, 90)
    filtered_tps = block_tps_array[(block_tps_array >= p10) & (block_tps_array <= p90)]
    
    print(f'\n    去除最高最低 10%:')
    print(f'      平均 TPS: {np.mean(filtered_tps):.1f} 笔/秒 ⭐')
    print(f'      中位数 TPS: {np.median(filtered_tps):.1f} 笔/秒')

# Top 10 最高TPS的区块
print(f'\n  🏆 Top 10 最高 TPS 区块:')
top_blocks = sorted(blocks_with_tx, key=lambda x: x['tx_count'], reverse=True)[:10]
for i, b in enumerate(top_blocks, 1):
    tps = b['tx_count'] / block_time
    print(f'    {i:2}. 区块 {b["round"]}: {b["tx_count"]:5,} 笔 → {tps:7.1f} TPS')

# 推荐的TPS指标
print(f'\n{'='*80}')
print(f'🎯 推荐的 TPS 指标 (去除极端值)')
print(f'{'='*80}')
print(f'稳态 TPS (去除前后10%):       {stable_tps:7.1f} 笔/秒  ⭐ (推荐)')
print(f'滑动窗口中位数 TPS:           {np.median(window_tps_array):7.1f} 笔/秒  ⭐ (稳健)')
print(f'单区块中位数 TPS:             {np.median(block_tps_array):7.1f} 笔/秒')
print(f'单区块平均 TPS (去除10%):     {np.mean(filtered_tps):7.1f} 笔/秒')
print(f'峰值 TPS:                     {np.max(block_tps_array):7.1f} 笔/秒  (最高单区块)')
print(f'{'='*80}')

print(f'\n💡 对比:')
print(f'  原始平均 TPS:     {confirmation_tps:7.1f} 笔/秒  (包含所有空区块)')
print(f'  有效平均 TPS:     {effective_tps:7.1f} 笔/秒  (仅含交易区块)')
print(f'  稳态 TPS:         {stable_tps:7.1f} 笔/秒  (去除启动/结束阶段) ⭐')
print(f'  理论最大 TPS:     {np.max(block_tps_array):7.1f} 笔/秒  (峰值能力)')
