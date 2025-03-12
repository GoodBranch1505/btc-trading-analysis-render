from flask import Flask, request
import pandas as pd
import numpy as np
from scipy import stats

app = Flask(__name__)
data_store = []

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    data_store.append(data)
    df = pd.DataFrame(data_store[-288:])  # 24時間分（5分×288）

    if len(df) >= 14:  # 最低限のデータ
        # トレンド
        df['sma_short'] = df['price'].rolling(window=6).mean()  # 30分
        df['sma_long'] = df['price'].rolling(window=24).mean()  # 2時間
        df['trend'] = df['sma_short'] - df['sma_long']

        # シーズン性（簡易: 1時間周期の残差）
        df['hour'] = pd.to_datetime(df['timestamp'], unit='s').dt.hour
        seasonal = df.groupby('hour')['price'].transform('mean')
        df['season_adj'] = df['price'] - seasonal

        # 外的要因（btc_countの影響を除去）
        df['sentiment'] = df['btc_count'].apply(lambda x: 0.5 if x > 7 else -0.5 if x < 3 else 0)
        df['price_adj'] = df['season_adj'] - (df['sentiment'] * 100000)  # 仮の影響係数

        # RSI
        delta = df['price_adj'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # 確率計算（簡易ロジスティックモデル）
        latest = df.iloc[-1]
        buy_score = stats.norm.cdf((latest['trend'] / 1000000) + (70 - latest['rsi']) / 100 + latest['sentiment'])
        sell_score = stats.norm.cdf((-latest['trend'] / 1000000) + (latest['rsi'] - 30) / 100 - latest['sentiment'])

        signal = "買い" if buy_score > 0.7 else "売り" if sell_score > 0.7 else "ホールド"
        return {
            'signal': signal,
            'buy_prob': round(buy_score, 2),
            'sell_prob': round(sell_score, 2),
            'price': latest['price'],
            'rsi': latest['rsi'],
            'trend': latest['trend'],
            'sentiment': latest['sentiment']
        }
    return {'signal': 'データ不足'}

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
