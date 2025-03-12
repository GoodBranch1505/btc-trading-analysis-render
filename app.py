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
    df = pd.DataFrame(data_store[-288:]).drop_duplicates(subset=['timestamp']).sort_values('timestamp')

    if len(df) >= 14:
        df['sma_short'] = df['price'].rolling(window=6).mean()
        df['sma_long'] = df['price'].rolling(window=24).mean()
        df['trend'] = df['sma_short'] - df['sma_long']
        df['hour'] = pd.to_datetime(df['timestamp'], unit='s').dt.hour
        seasonal = df.groupby('hour')['price'].transform('mean')
        df['season_adj'] = df['price'] - seasonal
        df['sentiment'] = df['btc_count'].apply(lambda x: 0.5 if x > 7 else -0.5 if x < 3 else 0)
        df['price_adj'] = df['season_adj'] - (df['sentiment'] * 100000)
        delta = df['price_adj'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        latest = df.iloc[-1]
        buy_score = stats.norm.cdf((latest['trend'] / 1000000) + (70 - latest['rsi']) / 100 + latest['sentiment'])
        sell_score = stats.norm.cdf((-latest['trend'] / 1000000) + (latest['rsi'] - 30) / 100 - latest['sentiment'])
        signal = "買い" if buy_score > 0.7 else "売り" if sell_score > 0.7 else "ホールド"
        signal_prob = buy_score if signal == "買い" else sell_score if signal == "売り" else max(1 - buy_score, 1 - sell_score)

        prev_signal_eval = "データ不足"
        success = 0
        failure = 0
        profit_loss = None
        if len(df) >= 2:
            prev = df.iloc[-2]
            prev_price = prev['price']
            curr_price = latest['price']
            prev_buy_score = stats.norm.cdf((prev['trend'] / 1000000) + (70 - prev['rsi']) / 100 + prev['sentiment'])
            prev_sell_score = stats.norm.cdf((-prev['trend'] / 1000000) + (prev['rsi'] - 30) / 100 - prev['sentiment'])
            prev_signal = "買い" if prev_buy_score > 0.7 else "売り" if prev_sell_score > 0.7 else "ホールド"
            
            if prev_signal == "買い":
                prev_signal_eval = "成功" if curr_price > prev_price else "失敗"
                success = 1 if curr_price > prev_price else 0
                failure = 1 if curr_price <= prev_price else 0
                profit_loss = curr_price - prev_price  # 買い: 価格差
            elif prev_signal == "売り":
                prev_signal_eval = "成功" if curr_price < prev_price else "失敗"
                success = 1 if curr_price < prev_price else 0
                failure = 1 if curr_price >= prev_price else 0
                profit_loss = prev_price - curr_price  # 売り: 逆の価格差
            else:  # ホールド
                prev_signal_eval = "成功" if curr_price > prev_price else "失敗" if curr_price < prev_price else "中立"
                success = 1 if curr_price > prev_price else 0
                failure = 1 if curr_price < prev_price else 0
                profit_loss = curr_price - prev_price  # ホールド: 価格変動をそのまま

        return {
            'signal': signal,
            'signal_prob': round(signal_prob, 2),
            'buy_prob': round(buy_score, 2),
            'sell_prob': round(sell_score, 2),
            'price': latest['price'],
            'rsi': latest['rsi'],
            'trend': latest['trend'],
            'sentiment': latest['sentiment'],
            'prev_signal_eval': prev_signal_eval,
            'success': success,
            'failure': failure,
            'profit_loss': profit_loss
        }
    return {'signal': 'データ不足'}

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
