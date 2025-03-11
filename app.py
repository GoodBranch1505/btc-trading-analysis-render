from flask import Flask, request
import pandas as pd
import numpy as np

app = Flask(__name__)
data_store = []

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    data_store.append(data)
    df = pd.DataFrame(data_store[-14:])

    if len(df) >= 14:
        df['sma_short'] = df['price'].rolling(window=5).mean()
        df['sma_long'] = df['price'].rolling(window=14).mean()
        delta = df['price'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['sentiment'] = df['btc_count'].apply(lambda x: 0.5 if x > 7 else -0.5 if x < 3 else 0)

        latest = df.iloc[-1]
        if latest['sma_short'] > latest['sma_long'] and latest['rsi'] < 70 and latest['sentiment'] > 0:
            signal = "買い"
        elif latest['sma_short'] < latest['sma_long'] and latest['rsi'] > 30 and latest['sentiment'] < 0:
            signal = "売り"
        else:
            signal = "ホールド"
        return {'signal': signal, 'price': latest['price'], 'rsi': latest['rsi'], 'sentiment': latest['sentiment']}
    return {'signal': 'データ不足'}

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
