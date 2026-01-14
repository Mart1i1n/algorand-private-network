#!/usr/bin/env python3
"""
持续负载测试 - 5分钟持续发送，测试稳态下的最大区块容量
"""
import json
import time
from datetime import datetime
from algosdk import account, transaction, mnemonic
from algosdk.v2client import algod
import os
import secrets
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_wallet1_info():
    """从容器中获取 Wallet1 地址和私钥"""
    result = subprocess.run(
        ['docker', 'exec', 'algo_private_network', 'bash', '-c',
         'goal account list -d /data/node1 | awk \'{print $2}\' | head -1'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    dispenser_addr = result.stdout.strip()
    
    result = subprocess.run(
        ['docker', 'exec', 'algo_private_network', 'goal', 'account', 'export',
         '-a', dispenser_addr, '-d', '/data/node1'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    
    match = re.search(r'"([^"]+)"', result.stdout)
    mnemonic_phrase = match.group(1)
    dispenser_sk = mnemonic.to_private_key(mnemonic_phrase)
    
    return dispenser_addr, dispenser_sk


if __name__ == "__main__":
    print("="*80)
    print("  持续负载测试 - 5分钟持续发送")
    print("="*80)

    # 参数
    CONCURRENT_WORKERS = 2000
    TX_PER_BATCH = 8000  # 每批次发送8000笔
    DURATION_SECONDS = 300  # 持续5分钟
    
    # 配置
    algod_address = "http://localhost:4001"
    with open('private_net_data/relay/algod.token') as f:
        algod_token = f.read().strip()

    client = algod.AlgodClient(algod_token, algod_address)

    # 检查网络状态
    status = client.status()
    print(f"\n✅ 网络状态:")
    print(f"  当前轮次:      {status['last-round']}")
    print(f"  距上次区块:    {status['time-since-last-round']/1e9:.1f}s")

    # 获取 Wallet1 信息
    print(f"\n🪙 使用 Wallet1 (node1)...")
    dispenser_addr, dispenser_sk = get_wallet1_info()
    print(f"  地址: {dispenser_addr[:10]}...")
    
    account_info = client.account_info(dispenser_addr)
    print(f"  余额: {account_info['amount']:,} ALGO")

    # 创建测试账户
    print(f"\n🔧 创建测试账户...")
    sender_sk, sender_addr = account.generate_account()
    receiver_sk, receiver_addr = account.generate_account()
    
    print(f"  发送方: {sender_addr[:10]}...")
    print(f"  接收方: {receiver_addr[:10]}...")

    # 充值
    print(f"\n💸 充值测试账户...")
    params = client.suggested_params()
    
    # 充值发送方（需要足够的ALGO支付手续费和交易金额）
    # 预计发送约 300,000 笔交易（5分钟 * 8000笔/批 * 7批），每笔1000 microALGO + 1000 fee
    fund_amt = 1_000_000_000  # 1000 ALGO（足够支付所有交易）
    txn = transaction.PaymentTxn(dispenser_addr, params, sender_addr, fund_amt, None)
    signed_txn = txn.sign(dispenser_sk)
    tx_id = client.send_transaction(signed_txn)
    print(f"  充值交易: {tx_id[:10]}...")
    transaction.wait_for_confirmation(client, tx_id, 20)
    print(f"  ✅ 充值完成")

    # 激活接收方账户
    txn = transaction.PaymentTxn(dispenser_addr, params, receiver_addr, 200_000, None)
    signed_txn = txn.sign(dispenser_sk)
    tx_id = client.send_transaction(signed_txn)
    print(f"  接收方充值交易: {tx_id[:10]}...")
    transaction.wait_for_confirmation(client, tx_id, 20)
    print(f"  ✅ 接收方账户已激活")

    # 开始持续负载测试
    print(f"\n🚀 开始持续负载测试")
    print(f"  并发线程: {CONCURRENT_WORKERS}")
    print(f"  每批: {TX_PER_BATCH} 笔交易")
    print(f"  持续时间: {DURATION_SECONDS} 秒 (5分钟)")
    print("="*80)

    start_time = time.time()
    start_round = client.status()['last-round']
    
    total_sent = 0
    total_failed = 0
    batch_num = 0
    
    def send_tx(signed_tx):
        try:
            return client.send_transaction(signed_tx), None
        except Exception as e:
            return None, str(e)
    
    # 持续发送
    while time.time() - start_time < DURATION_SECONDS:
        batch_num += 1
        elapsed = time.time() - start_time
        
        print(f"\n📦 批次 {batch_num} (已运行 {elapsed:.0f}s / {DURATION_SECONDS}s)")
        
        # 构建交易
        params = client.suggested_params()
        txns = []
        for i in range(TX_PER_BATCH):
            note = f"sustained-{batch_num}-{i}-{secrets.token_hex(4)}".encode()
            txn = transaction.PaymentTxn(sender_addr, params, receiver_addr, 1000, note=note)
            txns.append(txn.sign(sender_sk))
        
        # 并发发送
        batch_start = time.time()
        success_count = 0
        fail_count = 0
        
        with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
            futures = {executor.submit(send_tx, txn): txn for txn in txns}
            for future in as_completed(futures):
                tx_id, error = future.result()
                if tx_id:
                    success_count += 1
                else:
                    fail_count += 1
        
        batch_duration = time.time() - batch_start
        batch_tps = success_count / batch_duration
        
        total_sent += success_count
        total_failed += fail_count
        
        print(f"  ✅ 发送: {success_count} 笔成功, {fail_count} 笔失败")
        print(f"  ⏱  耗时: {batch_duration:.2f}s")
        print(f"  📈 TPS: {batch_tps:.1f}")
        print(f"  📊 累计: {total_sent:,} 笔 (失败 {total_failed})")
        
        # 短暂休息，避免过度负载
        time.sleep(0.5)
    
    total_duration = time.time() - start_time
    end_round = client.status()['last-round']
    
    print(f"\n{'='*80}")
    print(f"✅ 持续测试完成")
    print(f"{'='*80}")
    print(f"总运行时间: {total_duration:.1f}s")
    print(f"总发送数: {total_sent:,} 笔")
    print(f"总失败数: {total_failed} 笔")
    print(f"平均 TPS: {total_sent/total_duration:.1f}")
    print(f"区块范围: {start_round} -> {end_round} ({end_round - start_round} 个区块)")
    
    # 等待所有交易确认
    print(f"\n⏳ 等待30秒让所有交易被打包...")
    time.sleep(30)
    
    final_round = client.status()['last-round']
    
    # 分析区块容量
    print(f"\n{'='*80}")
    print(f"📊 区块容量分析")
    print(f"{'='*80}")
    print(f"分析区块范围: {start_round} -> {final_round}")
    
    blocks_info = []
    for round_num in range(start_round, final_round + 1):
        try:
            block = client.block_info(round_num)
            txns = block.get('block', {}).get('txns', [])
            if len(txns) > 0:
                blocks_info.append((round_num, len(txns)))
        except:
            pass
    
    if blocks_info:
        # 排序找出最大的
        blocks_info.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n🏆 Top 20 区块（按交易数量）:")
        print(f"{'-'*60}")
        for i, (round_num, tx_count) in enumerate(blocks_info[:20], 1):
            percentage = tx_count / 10000 * 100
            bar = '█' * int(percentage / 2)
            print(f"{i:2}. 区块 {round_num}: {tx_count:6,} 笔 [{bar:<50}] {percentage:5.1f}%")
        
        # 统计
        max_block = blocks_info[0]
        total_txs = sum(x[1] for x in blocks_info)
        avg_tx = total_txs / len(blocks_info)
        
        # 统计不同容量区间
        capacity_ranges = {
            '9000+': len([x for x in blocks_info if x[1] >= 9000]),
            '8000-8999': len([x for x in blocks_info if 8000 <= x[1] < 9000]),
            '7000-7999': len([x for x in blocks_info if 7000 <= x[1] < 8000]),
            '6000-6999': len([x for x in blocks_info if 6000 <= x[1] < 7000]),
            '5000-5999': len([x for x in blocks_info if 5000 <= x[1] < 6000]),
            '<5000': len([x for x in blocks_info if x[1] < 5000]),
        }
        
        print(f"\n{'='*80}")
        print(f"📈 统计汇总")
        print(f"{'='*80}")
        print(f"最大容量: {max_block[1]:,} 笔/区块 (区块 {max_block[0]})")
        print(f"平均容量: {avg_tx:,.0f} 笔/区块")
        print(f"包含交易的区块数: {len(blocks_info)} 个")
        print(f"总交易数: {total_txs:,} 笔")
        print(f"\nCertCommitteeSize 限制: 10,000 笔")
        print(f"达成率: {max_block[1]/10000*100:.1f}%")
        
        print(f"\n区块容量分布:")
        for range_name, count in capacity_ranges.items():
            if count > 0:
                print(f"  {range_name:12}: {count:3} 个区块")
        
        # 保存详细结果
        result = {
            'test_type': 'sustained_load',
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': total_duration,
            'concurrent_workers': CONCURRENT_WORKERS,
            'tx_per_batch': TX_PER_BATCH,
            'total_sent': total_sent,
            'total_failed': total_failed,
            'avg_tps': total_sent / total_duration,
            'start_round': start_round,
            'end_round': final_round,
            'max_tx_per_block': max_block[1],
            'max_block_round': max_block[0],
            'avg_tx_per_block': avg_tx,
            'blocks_with_tx': len(blocks_info),
            'capacity_distribution': capacity_ranges,
            'top_20_blocks': [(r, c) for r, c in blocks_info[:20]]
        }
        
        with open('sustained_load_results.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 详细结果已保存到: sustained_load_results.json")
    
    print(f"\n{'='*80}")
