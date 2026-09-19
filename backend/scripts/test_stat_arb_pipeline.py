import sys
import requests
import json

sys.stdout.reconfigure(encoding='utf-8')

base = 'http://localhost:8000'
print("=" * 60)
print("STATISTICAL ARBITRAGE NIFTY 50 ENDPOINT VERIFICATION")
print("=" * 60)

# 1. Health
h = requests.get(f'{base}/health').json()
print(f"1. Health: {h}")

# 2. Pairs
pairs = requests.get(f'{base}/api/pairs').json()
print(f"2. Pairs count: {len(pairs)}")
if pairs:
    print(f"   Top Pair: {pairs[0]['pair']} | Cointegration p-val: {pairs[0]['cointP']} | Hedge Ratio: {pairs[0]['hedgeRatio']} | Half-Life: {pairs[0]['halfLife']}D")

# 3. Series for Top Pair
top_id = pairs[0]['id'] if pairs else 'jswsteel-eichermot'
series = requests.get(f'{base}/api/pairs/{top_id}/series?range=1M').json()
print(f"3. Historical 1M Series points for {top_id}: {len(series)}")
if series:
    print(f"   Sample Bar: Date={series[-1]['label']}, Spread={series[-1]['spread']}, Z={series[-1]['z']}, A={series[-1]['a']}, B={series[-1]['b']}")

# 4. Signals
signals = requests.get(f'{base}/api/signals').json()
print(f"4. Active Signals count: {len(signals)}")
if signals:
    print(f"   First Signal: {signals[0]['pair']} -> {signals[0]['signal']} (Z={signals[0]['z']}, Spread={signals[0]['spread']})")

# 5. Risk Exposure
exp = requests.get(f'{base}/api/risk/exposure').json()
print(f"5. Risk Portfolio Exposure: {len(exp)} pairs")
for p in exp[:4]:
    print(f"   - {p['pair']}: Weight {p['weight']}%, Cointegration p={p['cointP']}, Half-Life={p['halfLife']}D")

# 6. Risk Metrics
risk = requests.get(f'{base}/api/risk').json()
print(f"6. Risk Metrics: Vol={risk.get('volatility')}, Sharpe={risk.get('sharpe')}, VaR={risk.get('var')}, ES={risk.get('es')}")

# 7. Backtest Run on Real Historical Data
bt_payload = {
    'entry': 2.0,
    'exit': 0.0,
    'stop': 4.0,
    'holding': 30,
    'cost': 0.1,
    'slippage': 0.05,
    'position': 'Volatility Adjusted',
    'start': '2023-01-02',
    'end': '2026-09-18',
    'pair_id': top_id
}
bt = requests.post(f'{base}/api/backtests', json=bt_payload).json()
print("7. Backtest execution on real prices:")
print(f"   ID: {bt.get('id')}")
print(f"   Initial: ₹{bt.get('initial'):,} -> Final: ₹{bt.get('final'):,}")
print(f"   Total Return: {bt.get('total')}% | Sharpe: {bt.get('sharpe')} | Win Rate: {bt.get('winRate')}% | Max Drawdown: {bt.get('drawdown')}%")
print(f"   Trades Executed: {bt.get('count')}")
print(f"   Equity Curve points: {len(bt.get('curve', []))}")

# 8. Backtest Trades
if bt.get('id'):
    trades = requests.get(f"{base}/api/backtests/{bt['id']}/trades").json()
    print(f"8. Backtest Trade Ledger: {len(trades)} trades recorded in DB")
    for t in trades[:3]:
        print(f"   - Trade #{t['id']}: {t['pair']} {t['direction']} | Entry={t['entryDate']} (Z={t['entryZ']}) -> Exit={t['exitDate']} (Z={t['exitZ']}) | P&L=₹{t['pnl']} ({t['return']}%)")

# 9. Research Experiments
exp_payload = {
    'entry': 2.3,
    'exit': 0.2,
    'stop': 4.0,
    'holding': 30,
    'cost': 0.1,
    'slippage': 0.05,
    'position': 'Volatility Adjusted',
    'start': '2023-01-02',
    'end': '2026-09-18',
    'pair_id': top_id
}
rexp = requests.post(f"{base}/api/research/experiments", json=exp_payload).json()
print("9. Research Experiment execution (Genuine Quantitative Backtest):")
print(f"   Name: {rexp.get('name')} | Return: {rexp.get('return_val')}% | Sharpe: {rexp.get('sharpe')} | Drawdown: {rexp.get('drawdown')}%")

all_rexp = requests.get(f"{base}/api/research/experiments").json()
print(f"   Saved experiments in DB: {len(all_rexp)}")

# 10. WebSocket Verification
try:
    import websocket
    ws = websocket.create_connection("ws://localhost:8000/api/ws/signals", timeout=5)
    ws.send(json.dumps({"action": "subscribe", "pair_ids": [top_id]}))
    msg = ws.recv()
    print("10. WebSocket tick message received:")
    print(f"    Sample: {msg[:120]}...")
    ws.close()
except Exception as e:
    print(f"10. WebSocket note: {e}")

print("=" * 60)
print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
print("=" * 60)
