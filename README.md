# Polymarket 预测市场数据获取 · 踩坑与样本

> 这是我在采集 Polymarket 预测市场盘口数据时踩过的坑、验证方法，以及**一份可直接跑的样本数据**。
> 完整数据集（40 万条 1H 盘口 / 90 万条逐档订单簿 / 3 秒级高频段）见文末。

---

## 一、为什么这份数据要"抢着记"

Polymarket 的 Gamma / CLOB API **只返回当前市场状态**。
一个「BTC 涨跌」市场**结算之后，它存续期里的挂单分布就永久查不到了**。

这跟股票不同 —— 股票的 Level 2 有交易所和第三方存档，预测市场没有，
因为它本质上是**临时市场**（5 分钟 / 1 小时就换一批）。

**⇒ 想研究预测市场的微观结构，必须在市场活着的时候持续轮询并落盘。**

---

## 二、坑 1：`best_bid` / `best_ask` 不是你想要的

我最初从市场对象里取 `best_bid` / `best_ask`，抓了 40 万条，结果：

```
best_bid = 0.01   占 98.6%
best_ask = 0.99   占 98.6%
spread   = 0.98   占 98.6%
```

第一反应是"API 坏了"。于是我把**逐档订单簿**拉出来交叉核对：

```
快照.best_bid == 订单簿.level1.bid_price   89,682 对，100.00% 一致
快照.best_ask == 订单簿.level1.ask_price   89,682 对，100.00% 一致
```

**⇒ 不是数据坏，是那个字段本身就是"边界报价"（可报价区间 0.01~0.99），
不是订单簿的真实最优挂单。**

### 真实价格在哪

在 **`bid_vwap` / `ask_vwap`** 列。同一个市场同一时刻：

```
best_ask = 0.99      ← 边界，无信息
ask_vwap = 0.983     ← 真实卖压
```

差别看着只有 0.7 分钱，但它让"价差"这个指标**完全失真**：

| 口径 | 价差中位 |
|---|---|
| 用 `best_ask - best_bid` | **0.980**（无意义） |
| 用 `ask_vwap - bid_vwap` | **0.948** |

要拿真实最优价，得直接读 CLOB 的 `/book` 接口，取 `asks[0]` / `bids[0]`。

> 本仓库 `sample/` 里的 `book-v2-samples.jsonl` 就是直接读 `/book` 的，
> 它的 `best_bid`/`best_ask`（如 0.51/0.53）**是真实最优价** —— 可与快照文件对比体会差别。

---

## 三、坑 2：结算规则里的等号

每个市场的 `description` 字段写着完整结算规则。BTC 1 小时市场的原文是：

> This market will resolve to "Up" if the close price is **greater than or equal to**
> the open price for the BTC/USDT 1 hour candle that **begins** on the time and date
> specified in the title.

两个必须注意的点：

1. **`greater than or equal`** —— **平盘算 Up**。这个等号不读原文猜不到。
   （实测存在 `close - open = 0.000` 的完全平盘小时，仍结算为 UP。）
2. **`begins`** —— 标题里的 `10am ET` 指 K 线**开盘**时刻，窗口是 `[14:00Z, 15:00Z)`。

---

## 四、采样频率怎么选

| 用途 | 频率 | 理由 |
|---|---|---|
| 研究价差 / 深度的低频演化 | **60 秒** | 足够，数据量可控 |
| 研究执行 / 滑点 / 冲击成本 | **3~5 秒** | 需同时记 10 档明细 |

我最后两套并行：6 周 × 60 秒打底，外加 2 天 × 3 秒的高频段。

---

## 五、样本数据（本仓库自带，可直接跑）

```
sample/
├── btc1h_snapshots_head1000.csv     1H 快照 · 前 1000 条
├── btc5m_orderbook_head1000.csv     5M 逐档订单簿 · 前 1000 条
├── book-v2-head200.jsonl            3 秒级盘口（含真实 10 档）· 前 200 条
└── README.md                         样本字段说明
```

跑一下看看：

```bash
pip install pandas
python examples/quickstart.py sample
```

`examples/analyze_boundary.py` 会**复算**上面那个 98.6% 的结论 —— 你可以自己验证我说的是真的：

```bash
python examples/analyze_boundary.py sample/btc1h_snapshots_head1000.csv
```

---

## 六、字段速查

### 快照文件（35 列）

| 组 | 字段 |
|---|---|
| 标识 | `collection_timestamp_utc` `market_id` `event_id` `condition_id` `slug` `asset` `question` `description` |
| 窗口 | `window_start_unix` `window_start_utc` `window_end_utc` `end_time` `resolution_time` `market_type` `active_status` `closed_status` `outcomes` `outcome_prices` |
| 盘口 | ⚠️ `best_bid` / `best_ask`（**边界报价，勿直接用**） `spread`(同理) · ✅ **`bid_vwap` / `ask_vwap`** · ✅ `bid_depth_shares` `ask_depth_shares` `bid_depth_usdc` `ask_depth_usdc` `bid_levels_count` `ask_levels_count` `volume` `volume_24h` `liquidity` |
| 空列 | `market_category` `resolution_time` `last_price`（采集期全空，见下） |

### 订单簿文件（13 列，长格式）

每个 `(时刻, 市场, 方向, 档位)` 一行：
`collection_timestamp_utc` `market_id` `asset` `market_type` `slug` `token_id` `side`(`bid`/`ask`) `level`(1=最优) `price` `size` `usdc_value` `cumulative_size` `cumulative_usdc`

> `token_id` 可区分 Up / Down 两个 outcome —— 做双腿或套利研究的前提。

### 高频盘口（38 字段 JSON）

`ts_utc` `slug` `side` `min_into_period` `prev_streak` `prev_up`
`best_bid` `best_ask`（**真实**） `n_ask_levels` `n_bid_levels`
`total_ask_shares` `total_bid_shares` `ask_shares_le_cap` `ask_usd_le_cap` `ask_avgpx_le_cap` `touch`
`fill_shares_{20,50,100,200,300}` `fill_usd_*` `fill_pct_*`（**吃单 N 美元的可成交占比 —— 滑点研究现成结果**）
`asks` `bids`（各 10 档 `[[price, size], ...]`） `in_first50`

---

## 七、已知限制（请务必读）

1. **CSV 记录数 ≠ 行数** —— `description` 含内嵌换行，1H 文件 **1,211,058 行 ↔ 403,686 条记录**（约 3 倍差）。必须用 CSV 解析器，勿按行切分。
2. **`last_price` / `market_category` / `resolution_time` 在采集期全空**（非损坏，是当时接口未返回）。
3. **`best_bid`/`best_ask` 空值不是损坏** —— 是那一刻**确实没有对手盘**（可用于研究流动性枯竭，别直接 `dropna()` 丢掉信号）。
4. **不含结算胜负字段** —— `outcome_prices` 采集期多为 `["0.5","0.5"]`。要标签需自行按 `description` 规则算，或用 `condition_id` 回查 Gamma API。
5. **60 秒定频轮询，不是逐笔** —— 可研究价差/深度低频演化，**不可**用于高频排队位置重建。
6. **只含 BTC**，覆盖 **6 周**（2026-03-14 → 04-25），跨市场状态泛化能力有限。

---

## 八、数据来源与合规

- 来源：**Polymarket 公开 API**（Gamma / CLOB），**只读轮询**采集。
- **不含**：账户地址、私钥、个人身份信息、任何交易指令。
- 本文与样本数据**仅供研究与学习**，不构成投资建议。
- 预测市场在部分司法辖区受限，使用者请自行确认当地法规与平台条款。

---

## 九、完整数据集

本仓库只含**样本**。完整数据（压缩后约 35 MB）包含：

| 内容 | 规模 |
|---|---|
| 1H 市场盘口快照 | 403,686 条 · 775 个市场 · 60 秒/次 |
| 5M 市场盘口快照 | 92,358 条 · 9,253 个市场 · 60 秒/次 |
| 5M 逐档订单簿 | 899,405 条 · 买卖各 5 档 |
| 1H 3 秒级盘口（加赠） | 90,575 条 · 含真实 10 档明细 |
| 1H 逐笔成交（加赠） | 2,103 笔 · 含钱包与链上 tx 哈希 |

> 完整数据集与字段说明文档在闲鱼。**本仓库的样本足够你验证数据口径、跑通代码** ——
> 确定有用了再考虑完整版。

---

## 附：仓库结构

```
.
├── README.md                      ← 本文件
├── LICENSE
├── examples/
│   ├── quickstart.py              读三种文件的示例（可直接跑）
│   └── analyze_boundary.py        复算"best_ask 恒 0.99"结论
└── sample/
    ├── btc1h_snapshots_head1000.csv
    ├── btc5m_orderbook_head1000.csv
    ├── book-v2-head200.jsonl
    └── README.md
```
