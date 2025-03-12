from flask import Flask, request
import pandas as pd
import numpy as np
from scipy import stats
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="xs409588.xsrv.jp",  # Xサーバーのホスト
        user="xs409588_user",
        password="gb20141216",
        database="xs409588_btc"
    )

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    conn = get_db_connection()
    conn.cursor().execute("INSERT INTO btc_data (price, timestamp, btc_count) VALUES (%s, %s, %s)",
                          (data['price'], data['timestamp'], data['btc_count']))
    conn.commit()
    df = pd.read_sql("SELECT * FROM btc_data ORDER BY timestamp DESC LIMIT 288", conn)
    conn.close()

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
