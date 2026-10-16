#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
读三种文件的示例。用法：
    python examples/quickstart.py sample

对应本文 README 里的三节：
  1. 1H 快照 —— 演示 best_bid/best_ask 是边界报价，真实价格在 vwap
  2. 5M 订单簿 —— 重建某一时刻的档位结构
  3. 3 秒级盘口 —— 真实 10 档 + 滑点字段
"""
import json
import os
import sys


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "sample"
    try:
        import pandas as pd
    except ImportError:
        print("请先安装 pandas: pip install pandas")
        return 1

    print("=" * 64)
    print("[1] 1H 快照 —— 边界报价 vs 真实价格")
    print("=" * 64)
    p = os.path.join(d, "btc1h_snapshots_head1000.csv")
    if os.path.exists(p):
        df = pd.read_csv(p)
        print("  行数        : %d" % len(df))
        print("  列数        : %d" % len(df.columns))
        # 边界报价占比
        b = (df.best_bid == 0.01).mean() * 100
        a = (df.best_ask == 0.99).mean() * 100
        print("  best_bid==0.01 占比 : %.1f%%   <-- 边界报价，不是真实最优价" % b)
        print("  best_ask==0.99 占比 : %.1f%%" % a)
        # 真实价格
        df["real_spread"] = df.ask_vwap - df.bid_vwap
        s = df.real_spread.dropna()
        if len(s):
            print("  由 vwap 构造的价差   : p50 = %.3f   <-- 真实价差" % s.median())
            print("  由 best 构造的价差   : p50 = %.3f   <-- 无意义（恒 0.98）"
                  % (df.best_ask - df.best_bid).median())
        print()
        print("  样本前 3 行（关键列）：")
        print(df[["collection_timestamp_utc", "best_bid", "best_ask",
                  "bid_vwap", "ask_vwap"]].head(3).to_string(index=False))
    else:
        print("  未找到 " + p)

    print()
    print("=" * 64)
    print("[2] 5M 逐档订单簿")
    print("=" * 64)
    p = os.path.join(d, "btc5m_orderbook_head1000.csv")
    if os.path.exists(p):
        ob = pd.read_csv(p)
        print("  行数: %d   市场数: %d" % (len(ob), ob.slug.nunique()))
        slug0 = ob.slug.iloc[0]
        snap = ob[ob.slug == slug0]
        t0 = snap.collection_timestamp_utc.min()
        book = snap[snap.collection_timestamp_utc == t0]
        print("  市场 %s @ %s 的档位：" % (slug0, t0))
        for _, r in book.sort_values(["side", "level"]).iterrows():
            print("    %-4s L%d  price=%.3f  size=%.2f  cum_size=%.2f"
                  % (r.side, r.level, r.price, r.size, r.cumulative_size))
        print("  注：level=1 也是边界口径；真实最优价请看 [3]")
    else:
        print("  未找到 " + p)

    print()
    print("=" * 64)
    print("[3] 3 秒级盘口（真实 10 档 + 滑点字段）")
    print("=" * 64)
    p = os.path.join(d, "book-v2-head200.jsonl")
    if os.path.exists(p):
        recs = []
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    recs.append(json.loads(line))
        print("  记录数: %d   字段数: %d" % (len(recs), len(recs[0])))
        r = recs[0]
        print("  时间   : %s" % r["ts_utc"])
        print("  市场   : %s" % r["slug"])
        print("  真实最优: bid=%s  ask=%s   <-- 与快照的 0.01/0.99 对比" % (r["best_bid"], r["best_ask"]))
        print("  卖盘前 3 档: %s" % (r["asks"][:3]))
        print("  买盘前 3 档: %s" % (r["bids"][:3]))

        # 挑一条"有实际成交"的记录来演示滑点字段（否则全是 0，看着像坏了）
        filled = next((x for x in recs if x.get("fill_pct_100", 0) > 0), None)
        if filled is None:
            print("  （样本内无带成交的记录，跳过滑点演示）")
        else:
            print()
            print("  滑点字段示例（%s bid=%s ask=%s）："
                  % (filled["ts_utc"], filled["best_bid"], filled["best_ask"]))
            print("  含义：假设你市价吃单 N 美元，能成交多少股、占该侧挂单的百分之几")
            for n in (20, 50, 100, 200, 300):
                print("    吃 $%-4d -> 成交 %8.2f 股 / 占挂单 %5.1f%%"
                      % (n, filled["fill_shares_%d" % n], filled["fill_pct_%d" % n]))
            nz = sum(1 for x in recs if x.get("fill_pct_100", 0) > 0)
            print("  （样本 %d 条中，有 %d 条存在可成交量 —— 全 0 表示当时对手盘不足）"
                  % (len(recs), nz))
    else:
        print("  未找到 " + p)

    print()
    print("=" * 64)
    print("完成。重点：快照的 best_bid/best_ask 是边界报价，真实价格在 vwap。")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
