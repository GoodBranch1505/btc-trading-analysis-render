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
    df = pd.DataFrame(data_store[-288:]).drop_duplicates(subset=['timestamp'])  # 重複排除

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

        past_signal_eval = "データ不足"
        if len(df) >= 2:
            past = df.iloc[-2]  # 直前のデータ
            past_time = int(past['timestamp'])
            curr_time = int(latest['timestamp'])
            if curr_time - past_time >= 14 * 60 and curr_time - past_time <= 16 * 60:  # 14〜16分
                past_price = past['price']
                curr_price = latest['price']
                past_buy_score = stats.norm.cdf((past['trend'] / 1000000) + (70 - past['rsi']) / 100 + past['sentiment'])
                past_sell_score = stats.norm.cdf((-past['trend'] / 1000000) + (past['rsi'] - 30) / 100 - past['sentiment'])
                past_signal = "買い" if past_buy_score > 0.7 else "売り" if past_sell_score > 0.7 else "ホールド"
                if past_signal == "買い":
                    past_signal_eval = "成功" if curr_price > past_price else "失敗"
                elif past_signal == "売り":
                    past_signal_eval = "成功" if curr_price < past_price else "失敗"
                else:
                    past_signal_eval = "ホールド（評価なし）"

        return {
            'signal': signal,
            'signal_prob': round(signal_prob, 2),
            'buy_prob': round(buy_score, 2),
            'sell_prob': round(sell_score, 2),
            'price': latest['price'],
            'rsi': latest['rsi'],
            'trend': latest['trend'],
            'sentiment': latest['sentiment'],
            'past_signal_eval': past_signal_eval
        }
    return {'signal': 'データ不足'}

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
