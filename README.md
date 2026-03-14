# OpenClaw 交易系統

一個功能完整的股票與加密貨幣量化交易系統，支援回測、即時報價、技術指標分析、選股策略等功能。

## 功能特色

### 📊 資料獲取
- 美股、台股即時報價與歷史資料
- 加密貨幣價格數據
- 基本面數據擷取

### 📈 技術分析
- 多種技術指標計算（MA、RSI、MACD、布林帶、KD 等）
- 個股與大盤分析
- K 線圖生成

### 🎯 選股策略
- 高勝率股票篩選
- 綜合推薦系統
- 多元因子分析

### 🔄 回測系統
- MA 與 RSI 策略回測
- 參數優化
- 隔夜策略模組

### 📡 即時報價
- 股票報價伺服器
- 漲跌率分析
- 籌碼面資料

## 主要腳本

| 腳本 | 說明 |
|------|------|
| `backtest_framework.py` | 基本回測框架 |
| `louie_backtest.py` | Louie 策略回測 |
| `louie_optimize.py` | 策略參數優化 |
| `louie_overnight_strategy.py` | 隔夜策略 |
| `calculate_indicators.py` | 技術指標計算 |
| `fetch_stocks.py` | 股票資料獲取 |
| `fetch_fundamental.py` | 基本面數據 |
| `stock_server.py` | 股票報價伺服器 |
| `winrate_server.py` | 勝率伺服器 |

## 安裝

```bash
pip install pandas numpy yfinance
```

## 使用範例

```python
# 獲取股票數據
python fetch_stocks.py

# 執行回測
python louie_backtest.py

# 執行策略優化
python louie_optimize.py

# 啟動報價伺服器
python stock_server.py
```

## 數據輸出

- `stocks_data.json` - 股票歷史數據
- `us_top500.json` - 美股前 500 大
- `tw_top100.json` - 台股前 100 大
- `crypto.json` - 加密貨幣數據
- `*.json` - 各策略輸出結果

## 技術栈

- **Python 3**
- **pandas** - 數據處理
- **yfinance** - Yahoo Finance API
- **numpy** - 數值計算

## 授權

MIT License

---

*此系統僅供學習與研究使用，不構成投資建議。*
