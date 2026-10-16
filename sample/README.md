# 样本数据说明

这里的三个文件都是从**真实数据集**里取的前 N 条（不是编造的），
足够你**验证字段口径、跑通代码、判断数据是否有用**。

| 文件 | 来源 | 条数 | 说明 |
|---|---|---|---|
| `btc1h_snapshots_head1000.csv` | 1H 快照 | 1,000 | 35 列，可直接验证"边界报价"结论 |
| `btc5m_orderbook_head1000.csv` | 5M 逐档订单簿 | 1,000 | 13 列长格式 |
| `book-v2-head200.jsonl` | 3 秒级盘口 | 200 | 38 字段，**含真实 10 档与滑点字段** |

## 两个必须注意的读取细节

### 1. CSV 记录数 ≠ 行数

`description` 字段**含内嵌换行**，所以：

```
1H 完整文件：1,211,058 行  ↔  403,686 条记录（约 3 倍差）
```

**必须用 CSV 解析器**（`pandas.read_csv` / `csv.DictReader`），
**不要**用 `wc -l` 或按行 split 来数记录。

本样本 `head1000.csv` 取的是前 1000 **条记录**（对应约 3000 物理行）。

### 2. `best_bid` / `best_ask` 是边界报价

在快照文件里：

- `best_bid` = 0.01 占 **98.6%**
- `best_ask` = 0.99 占 **98.6%**
- 因此 `spread` 恒为 **0.98**

**这是采集口径（边界报价），不是数据损坏。**
真实价格在 **`bid_vwap` / `ask_vwap`**。

但注意：`book-v2-head200.jsonl` 里的 `best_bid`/`best_ask`
**是真实最优价**（如 0.51/0.53），因为那个采集器直接读 CLOB `/book` 接口。
**两份数据口径不同，不要混用。**

## 自己验证

```bash
# 复算"98.6% 边界报价"这个结论
python examples/analyze_boundary.py sample/btc1h_snapshots_head1000.csv

# 读三种文件的完整示例
python examples/quickstart.py sample
```

## 字段完整说明

见仓库根目录 `README.md` 第六节，或完整数据集内附的 35 字段文档。
