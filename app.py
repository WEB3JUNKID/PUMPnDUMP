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
INTERVAL = "30m"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

def check_signal():
    # Fetch last 3 candles: [0]=Previous closed, [1]=Just closed, [2]=Currently open
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit=3"
    try:
        data = requests.get(url).json()
        
        # Previous candle (T-2)
        prev_high = float(data[0][2])
        prev_low = float(data[0][3])
        prev_close = float(data[0][4])
        
        # Just closed candle (T-1)
        curr_high = float(data[1][2])
        curr_low = float(data[1][3])
        curr_close = float(data[1][4])
        
        # Sweep Logic
        low_taken = curr_low < prev_low
        high_taken = curr_high > prev_high
        
        bullish = False
        bearish = False
        sl = 0.0
        
        # Bullish: Low or High taken, closes higher than previous close
        if (low_taken or high_taken) and (curr_close > prev_close):
            bullish = True
            sl = curr_low
            
        # Bearish: Low or High taken, closes lower than previous close
        elif (high_taken or low_taken) and (curr_close < prev_close):
            bearish = True
            sl = curr_high
            
        if bullish:
            msg = f"🟢 <b>BULLISH SIGNAL</b> 🟢\nAsset: {SYMBOL} (30m)\nAction: BUY\nClose: {curr_close}\nStop Loss: {sl}"
            send_telegram_message(msg)
        elif bearish:
            msg = f"🔴 <b>BEARISH SIGNAL</b> 🔴\nAsset: {SYMBOL} (30m)\nAction: SELL\nClose: {curr_close}\nStop Loss: {sl}"
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
    return "Crypto Signal Bot is Active."

if __name__ == '__main__':
    # Run bot loop in background thread
    threading.Thread(target=bot_loop, daemon=True).start()
    # Bind Flask to port for Render
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
          
