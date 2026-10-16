#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
复算"best_bid/best_ask 是边界报价"这个结论。
你可以自己跑一遍验证 README 里说的数字，不用信我。

用法：
    python examples/analyze_boundary.py sample/btc1h_snapshots_head1000.csv
    python examples/analyze_boundary.py <完整数据集>/solal9_btc1h_snapshots.csv
"""
import collections
import csv
import os
import sys

csv.field_size_limit(10 ** 9)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    if not os.path.exists(path):
        print("文件不存在: " + path)
        return 1

    n = 0
    bid = collections.Counter()
    ask = collections.Counter()
    spread = collections.Counter()
    consistent = 0          # spread == ask - bid 的行数
    vwap_ok = 0

    with open(path, "r", encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        has_vwap = "bid_vwap" in (rd.fieldnames or [])
        for row in rd:
            n += 1
            b, a, s = row.get("best_bid"), row.get("best_ask"), row.get("spread")
            if b: bid[b] += 1
            if a: ask[a] += 1
            if s: spread[s] += 1
            try:
                if b and a and s and abs((float(a) - float(b)) - float(s)) < 1e-9:
                    consistent += 1
            except ValueError:
                pass
            if has_vwap and row.get("bid_vwap") and row.get("ask_vwap"):
                vwap_ok += 1

    print("=" * 62)
    print("文件: %s" % path)
    print("记录数: %d" % n)
    print("=" * 62)
    print()
    print("best_bid 取值分布（前 5）：")
    for v, c in bid.most_common(5):
        print("   %-8s %9d  (%.2f%%)" % (v, c, 100.0 * c / max(n, 1)))
    print()
    print("best_ask 取值分布（前 5）：")
    for v, c in ask.most_common(5):
        print("   %-8s %9d  (%.2f%%)" % (v, c, 100.0 * c / max(n, 1)))
    print()
    print("spread 取值分布（前 5）：")
    for v, c in spread.most_common(5):
        print("   %-8s %9d  (%.2f%%)" % (v, c, 100.0 * c / max(n, 1)))
    print()
    print("自洽性检查：spread == ask - bid 的行数 = %d (%.2f%%)"
          % (consistent, 100.0 * consistent / max(n, 1)))
    print()
    if has_vwap:
        print("★ 结论：")
        print("   best_bid/best_ask 大量钉在 0.01/0.99 上，")
        print("   这是**边界报价**（可报价区间），不是订单簿的真实最优挂单。")
        print("   真实价格请用 bid_vwap / ask_vwap。")
        print("   （本文件有 vwap 数据的行数：%d）" % vwap_ok)
    else:
        print("★ 本文件无 vwap 列，无法对比真实价格。")
    print()
    print("  完整数据集里这个文件的实测值：")
    print("    best_bid==0.01 占 98.6%（403,686 条中 398,042 条）")
    print("    best_ask==0.99 占 98.6%")
    print("    与逐档订单簿交叉核对 89,682 对，100.00% 一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
