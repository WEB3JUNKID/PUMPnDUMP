import os
import time
import requests
import threading
from datetime import datetime
from flask import Flask

app = Flask(__name__)

# Environment Variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SYMBOL = "BTCUSDT"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

def check_signal():
    try:
        # Fetch 30m and 1h candles
        # Limit=3 gives us: [0]=Previous closed, [1]=Just closed, [2]=Currently open
        url_30m = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval=30m&limit=3"
        url_1h = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval=1h&limit=3"
        
        data_30m = requests.get(url_30m).json()
        data_1h = requests.get(url_1h).json()
        
        # --- 30 MINUTE LOGIC ---
        prev_30m_high = float(data_30m[0][2])
        prev_30m_low = float(data_30m[0][3])
        prev_30m_close = float(data_30m[0][4])
        
        curr_30m_high = float(data_30m[1][2])
        curr_30m_low = float(data_30m[1][3])
        curr_30m_close = float(data_30m[1][4])
        
        # 30m Sweep Detection
        low_taken_30m = curr_30m_low < prev_30m_low
        high_taken_30m = curr_30m_high > prev_30m_high
        
        bullish_30m = (low_taken_30m or high_taken_30m) and (curr_30m_close > prev_30m_close)
        bearish_30m = (high_taken_30m or low_taken_30m) and (curr_30m_close < prev_30m_close)
        
        # --- 1 HOUR CONFLUENCE LOGIC ---
        # Evaluate the last fully closed 1h candle
        prev_1h_close = float(data_1h[0][4])
        curr_1h_close = float(data_1h[1][4])
        
        # 1h aligns if it swept/closed higher OR continued higher (close > prev close)
        bullish_1h = curr_1h_close > prev_1h_close
        bearish_1h = curr_1h_close < prev_1h_close
        
        # --- SIGNAL GENERATION ---
        if bullish_30m:
            confluence = "100%" if bullish_1h else "75%"
            sl = curr_30m_low
            msg = (
                f"🟢 <b>BULLISH SIGNAL</b> 🟢\n"
                f"Asset: {SYMBOL}\n"
                f"Confluence: <b>{confluence}</b>\n"
                f"Action: BUY\n"
                f"Close: {curr_30m_close}\n"
                f"Stop Loss: {sl}"
            )
            send_telegram_message(msg)
            
        elif bearish_30m:
            confluence = "100%" if bearish_1h else "75%"
            sl = curr_30m_high
            msg = (
                f"🔴 <b>BEARISH SIGNAL</b> 🔴\n"
                f"Asset: {SYMBOL}\n"
                f"Confluence: <b>{confluence}</b>\n"
                f"Action: SELL\n"
                f"Close: {curr_30m_close}\n"
                f"Stop Loss: {sl}"
            )
            send_telegram_message(msg)
            
    except Exception as e:
        print(f"Error fetching data: {e}")

def bot_loop():
    while True:
        now = datetime.utcnow()
        minutes = now.minute
        
        # Calculate exactly how many minutes until the next XX:00 or XX:30 mark
        if minutes < 30:
            sleep_mins = 30 - minutes
        else:
            sleep_mins = 60 - minutes
            
        # Add 5 seconds to ensure the exchange candle has fully closed
        sleep_secs = (sleep_mins * 60) - now.second + 5 
        time.sleep(sleep_secs)
        
        check_signal()

@app.route('/')
def home():
    return "Crypto Signal Bot (with 1H Confluence) is Active."

if __name__ == '__main__':
    threading.Thread(target=bot_loop, daemon=True).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
