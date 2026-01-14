#!/usr/bin/env python3
"""
TPS & Latency 测试 - 4节点私有网络（优化版）
使用批量发送和高效确认
"""
import json
import time
from datetime import datetime
from algosdk import account, transaction, mnemonic
from algosdk.v2client import algod
import numpy as np
import os
import secrets
import subprocess
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_wallet1_info():
    """从容器中获取 Wallet1 地址和私钥"""
    # 获取地址
    result = subprocess.run(
        ['docker', 'exec', 'algo_private_network', 'bash', '-c',
         'goal account list -d /data/node1 | awk \'{print $2}\' | head -1'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    dispenser_addr = result.stdout.strip()
    
    if not dispenser_addr:
        print("❌ 无法获取 Wallet1 地址")
        sys.exit(1)
    
    # 导出私钥
    result = subprocess.run(
        ['docker', 'exec', 'algo_private_network', 'goal', 'account', 'export',
         '-a', dispenser_addr, '-d', '/data/node1'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    
    if 'Exported key for account' not in result.stdout:
        print(f"❌ 无法导出密钥")
        print(result.stdout + result.stderr)
        sys.exit(1)
    
    match = re.search(r'"([^"]+)"', result.stdout)
    if not match:
        print(f"❌ 无法解析私钥")
        sys.exit(1)
    
    mnemonic_phrase = match.group(1)
    dispenser_sk = mnemonic.to_private_key(mnemonic_phrase)
    
    return dispenser_addr, dispenser_sk


def main():
    print("="*80)
    print("  4节点私有网络 - TPS & 延迟测试（优化版）")
    print("="*80)

    # 参数（可通过环境变量覆盖）
    ROUNDS = int(os.getenv("TPS_ROUNDS", "3"))
    TX_PER_ROUND = int(os.getenv("TPS_TX_PER_ROUND", "12000"))
    CONCURRENT_WORKERS = int(os.getenv("TPS_CONCURRENT_WORKERS", "2000"))

    # 配置
    algod_address = "http://localhost:4001"
    with open('private_net_data/relay/algod.token') as f:
        algod_token = f.read().strip()

    client = algod.AlgodClient(algod_token, algod_address)

    # 检查连接
    try:
        status = client.status()
        print(f"\n✅ 网络状态:")
        print(f"  Genesis ID:    {status.get('genesis-id', 'N/A')}")
        print(f"  当前轮次:      {status['last-round']}")
        print(f"  距上次区块:    {status.get('time-since-last-round', 0)/1000000000:.1f}s")
    except Exception as e:
        print(f"\n❌ 无法连接网络: {e}")
        sys.exit(1)

    # 获取 Wallet1 信息
    print(f"\n🪙 使用 Wallet1 (node1)...")
    dispenser_addr, dispenser_sk = get_wallet1_info()
    print(f"  地址: {dispenser_addr[:10]}...")

    # 查询余额
    try:
        account_info = client.account_info(dispenser_addr)
        balance = account_info.get('amount', 0) / 1_000_000
        print(f"  余额: {balance:,.0f} ALGO")
    except Exception as e:
        print(f"❌ 无法查询余额: {e}")
        sys.exit(1)

    print(f"✅ 密钥加载成功")

    # 创建测试账户
    print(f"\n🔧 创建测试账户...")
    sender_sk, sender_addr = account.generate_account()
    receiver_sk, receiver_addr = account.generate_account()
    print(f"  发送方: {sender_addr[:10]}...")
    print(f"  接收方: {receiver_addr[:10]}...")

    # 充值
    print(f"\n💸 充值测试账户...")
    params = client.suggested_params()

    fund_txn = transaction.PaymentTxn(
        dispenser_addr, params, sender_addr, 100_000_000, None
    )
    signed_fund = fund_txn.sign(dispenser_sk)
    tx_id = client.send_transaction(signed_fund)
    print(f"  充值交易: {tx_id[:10]}...")

    try:
        transaction.wait_for_confirmation(client, tx_id, 20)
        print(f"  ✅ 充值完成")
    except Exception as e:
        print(f"  ❌ 充值失败: {e}")
        sys.exit(1)

    # 为接收方预先充值，避免最小余额限制
    receiver_fund_txn = transaction.PaymentTxn(
        dispenser_addr, params, receiver_addr, 200_000, None
    )
    signed_receiver_fund = receiver_fund_txn.sign(dispenser_sk)
    receiver_tx_id = client.send_transaction(signed_receiver_fund)
    print(f"  接收方充值交易: {receiver_tx_id[:10]}...")

    try:
        transaction.wait_for_confirmation(client, receiver_tx_id, 20)
        print(f"  ✅ 接收方账户已激活")
    except Exception as e:
        print(f"  ❌ 接收方充值失败: {e}")
        sys.exit(1)

    # TPS 测试
    print(f"\n🚀 开始 TPS 测试 ({ROUNDS} 轮)")
    print(f"  每轮: {TX_PER_ROUND} 笔交易")
    print(f"  并发线程: {CONCURRENT_WORKERS}")
    print("="*80)

    results = []
    for round_num in range(1, ROUNDS + 1):
        print(f"\n📊 第 {round_num}/{ROUNDS} 轮")
        
        params = client.suggested_params()
        start_round = params.first
        
        # 构建所有交易
        txns = []
        for i in range(TX_PER_ROUND):
            # 为避免重复 txid，在 note 中加入随机前缀
            note = f"tps-{round_num}-{i}-{secrets.token_hex(4)}".encode()
            txn = transaction.PaymentTxn(
                sender_addr, params, receiver_addr, 1000, note=note
            )
            signed = txn.sign(sender_sk)
            txns.append(signed)
        
        # 并发批量发送（极速发送所有交易）
        send_start = time.time()
        tx_ids = []
        failed = 0
        
        print(f"    🚀 并发发送 {len(txns)} 笔交易...")
        
        def send_single_tx(signed_tx):
            """发送单笔交易"""
            try:
                return client.send_transaction(signed_tx), None
            except Exception as e:
                return None, str(e)
        
        # 使用线程池并发发送
        with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
            # 提交所有发送任务
            futures = {executor.submit(send_single_tx, signed): signed for signed in txns}
            
            # 收集结果
            for future in as_completed(futures):
                tx_id, error = future.result()
                if tx_id:
                    tx_ids.append(tx_id)
                else:
                    failed += 1
                    if failed <= 3:
                        print(f"    ⚠️  发送失败: {error}")
        
        send_duration = time.time() - send_start
        
        print(f"    ✅ 发送完成: {len(tx_ids)} 笔成功, {failed} 笔失败 ({send_duration:.2f}s)")
        print(f"    📈 发送 TPS: {len(tx_ids)/send_duration:.1f}")
        
        # 高效等待确认：从第1个区块就开始检查
        print(f"    ⏳ 等待确认（发送轮次: {start_round}）...")
        confirm_start = time.time()
        
        max_wait_rounds = 30  # 最多等待30个区块
        current_round = start_round
        confirmed = 0
        first_confirm_round = None
        
        for i in range(max_wait_rounds):
            try:
                # 等待下一个区块
                status = client.status_after_block(current_round)
                current_round = status['last-round']
                block_num = i + 1  # 这是第几个区块
                
                # 每个区块都检查确认情况
                confirmed = 0
                for tx_id in tx_ids:
                    try:
                        txinfo = client.pending_transaction_info(tx_id)
                        # 如果有 confirmed-round，说明已确认
                        if 'confirmed-round' in txinfo and txinfo['confirmed-round'] > 0:
                            confirmed += 1
                            if first_confirm_round is None:
                                first_confirm_round = txinfo['confirmed-round']
                    except Exception:
                        # 不在pending池中，可能已确认
                        confirmed += 1
                
                # 每个区块都显示详细进度
                print(f"      第{block_num}个区块 (轮次{current_round}): 已确认 {confirmed}/{len(tx_ids)} ({confirmed/len(tx_ids)*100:.0f}%)")
                
                # 如果全部确认，提前退出
                if confirmed == len(tx_ids):
                    blocks_needed = current_round - start_round
                    print(f"      ✅ 所有交易已确认！")
                    print(f"         发送轮次: {start_round}")
                    print(f"         确认轮次: {current_round}")
                    print(f"         区块间隔: {blocks_needed} 个区块")
                    break
                
            except Exception as e:
                print(f"    ⚠️  等待区块失败: {e}")
                break
        
        confirm_duration = time.time() - confirm_start
        total_duration = send_duration + confirm_duration
        
        # 计算延迟
        final_status = client.status()
        final_round = final_status['last-round']
        latency = (final_round - start_round) * 4.5  # ~4.5s per block
        
        result = {
            'round': round_num,
            'sent': len(tx_ids),
            'confirmed': confirmed,
            'send_time': send_duration,
            'confirm_time': confirm_duration,
            'total_time': total_duration,
            'send_tps': len(tx_ids)/send_duration if send_duration > 0 else 0,
            'total_tps': confirmed/total_duration if total_duration > 0 else 0,
            'latency': latency
        }
        results.append(result)
        
        print(f"    ✅ 确认: {confirmed}/{len(tx_ids)} ({confirmed/len(tx_ids)*100:.0f}%)")
        print(f"    ⏱  总耗时: {total_duration:.2f}s")
        print(f"    📊 总 TPS: {result['total_tps']:.1f}")
        print(f"    ⏰ 延迟: {latency:.1f}s")
        
        time.sleep(2)

    # 汇总
    print(f"\n" + "="*80)
    print(f"📈 测试汇总")
    print(f"="*80)

    total_sent = sum(r['sent'] for r in results)
    total_confirmed = sum(r['confirmed'] for r in results)
    avg_send_tps = np.mean([r['send_tps'] for r in results])
    avg_total_tps = np.mean([r['total_tps'] for r in results])
    avg_latency = np.mean([r['latency'] for r in results])

    print(f"\n总交易数: {total_sent}")
    print(f"确认数: {total_confirmed} ({total_confirmed/total_sent*100:.1f}%)")
    print(f"\n平均发送 TPS: {avg_send_tps:.1f}")
    print(f"平均总 TPS: {avg_total_tps:.1f}")
    print(f"平均延迟: {avg_latency:.1f}s")

    print(f"\n💾 保存结果...")
    with open('private_network_tps_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'network': '4-node private network (optimized test)',
            'rounds': results,
            'summary': {
                'total_sent': total_sent,
                'total_confirmed': total_confirmed,
                'avg_send_tps': avg_send_tps,
                'avg_total_tps': avg_total_tps,
                'avg_latency': avg_latency
            }
        }, f, indent=2)

    print(f"✅ 结果已保存到: private_network_tps_results.json")
    print("="*80)


if __name__ == "__main__":
    main()
