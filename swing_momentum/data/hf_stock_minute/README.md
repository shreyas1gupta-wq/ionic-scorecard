---
license: mit
task_categories:
- time-series-forecasting
- tabular-regression
tags:
- finance
- nse
- india
- stock-market
- quantitative-finance
- upstox
pretty_name: Indian Stock Market Minute & Daily Data
size_categories:
- 10B<n<100B
configs:
- config_name: default
  data_files:
  - split: minute
    path: minute/*.parquet
  - split: day
    path: day/*.parquet
---

# 🇮🇳 Indian Stock Market Data: Minute & Daily (2000 - 2026)

## 📌 Overview
This is a high-performance financial dataset containing the historical price history of **2,500+ NSE Stocks and Indices**. 

The dataset has been **sharded and optimized** for high-speed training. Instead of thousands of tiny files, it is grouped into large ~1.5GB Parquet shards, making it ideal for fast streaming with the Hugging Face `datasets` library.

## 📊 Dataset Stats
- **Total Rows:** ~715 Million
- **Size:** ~10.5 GB (Compressed Snappy Parquet) / ~125 GB (Uncompressed)
- **Coverage:** 99.4% of active/suspended NSE Equities & Indices
- **Granularity:** - **Minute:** 1-minute intraday candles (2022-2026)
  - **Day:** Daily candles (2000-2026)
- **Schema:** `symbol`, `timestamp` (UTC), `open`, `high`, `low`, `close`, `volume`, `oi`

## 📂 Directory Structure
The data is partitioned by frequency to allow for efficient loading.

```text
/minute/
    train-00000.parquet  (Stocks A-C)
    train-00001.parquet  (Stocks C-H)
    ...
/day/
    train-00000.parquet  (All Daily Data)
```

> **Note:** The files are sorted by `Symbol` then `Timestamp`. This means all data for a specific stock (e.g., `RELIANCE`) is contiguous within a single shard, maximizing compression and read speed.

## 💻 Usage (Python)

### 🚀 Option 1: Using Hugging Face Datasets (Recommended)
This method automatically handles downloading, caching, and iterating over the shards.

```python
from datasets import load_dataset

# 1. Load ALL Minute-Level Data (Streams 10.5 GB in shards)
# Use split="minute" to get the high-res intraday data
ds_minute = load_dataset("xxparthparekhxx/indian-stock-market-minute-data", split="minute")

# 2. Filter for a specific stock
# (The library efficiently scans the Arrow table in RAM)
reliance = ds_minute.filter(lambda x: x['symbol'] == 'RELIANCE')

print(reliance[0])
```

### ⚡ Option 2: Streaming (No Download)
If you don't want to download the full 10.5 GB to disk, you can stream it on-the-fly.

```python
from datasets import load_dataset

dataset = load_dataset(
    "xxparthparekhxx/indian-stock-market-minute-data", 
    split="minute", 
    streaming=True
)

# Iterate through the dataset without downloading everything
# Since data is sorted by Symbol, you will see all rows for a stock sequentially
for row in dataset:
    if row['symbol'] == 'TATASTEEL':
        print(row)
        # Stop after finding the first row to prove it works
        break
```

### 📉 Option 3: Load Daily Data Only
If you only need daily timeframe data (2000-2026), you can load just the daily split (~100MB).

```python
from datasets import load_dataset

ds_day = load_dataset("xxparthparekhxx/indian-stock-market-minute-data", split="day")
print(ds_day[0])
```

### 🐼 Option 4: Using Pandas
You can read individual shards directly if you prefer manual control.

```python
import pandas as pd

# Load the first shard of minute data (Contains stocks starting with A-B approx)
df = pd.read_parquet("hf://datasets/xxparthparekhxx/indian-stock-market-minute-data/minute/train-00000.parquet")

print(df.head())
```

## 📝 Schema & Data Types

| Column | Type | Description |
|---|---|---|
| `symbol` | String | NSE Trading Symbol (e.g., `RELIANCE`, `NIFTY_50`) |
| `timestamp` | Datetime (ns) | **UTC Timezone**. (Add +5:30 for IST) |
| `open` | Float32 | Opening Price |
| `high` | Float32 | High Price |
| `low` | Float32 | Low Price |
| `close` | Float32 | Closing Price |
| `volume` | Int64 | Volume Traded |
| `oi` | Int64 | Open Interest (0 if not applicable) |

## ⚠️ Disclaimer
This dataset is intended for **research, educational, and backtesting purposes only**.
- It is not a live feed.
- Do not use this as the primary basis for live financial trading.
- The authors are not responsible for any financial losses incurred from using this data.

## 📄 License
This dataset is released under the **MIT License**.