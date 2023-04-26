import os
import ccxt
import json
from flask import Flask, request

app = Flask(__name__)

# خواندن تنظیمات از فایل config.json
with open('config.json') as config_file:
    config = json.load(config_file)

# تنظیمات API برای بایننس و بای‌بیت
bybit_config = config["EXCHANGES"]["BYBIT"]

use_binance_futures = False
if "BINANCE-FUTURES" in config["EXCHANGES"]:
    if config["EXCHANGES"]["BINANCE-FUTURES"]["ENABLED"]:
        print("Binance is enabled!")
        use_binance_futures = True

        binance = ccxt.binance({
            "apiKey": config["EXCHANGES"]["BINANCE-FUTURES"]["API_KEY"],
            "secret": config["EXCHANGES"]["BINANCE-FUTURES"]["API_SECRET"],
            "options": {"defaultType": "future"},
            "urls": {
                "api": {
                    "public": "https://testnet.binancefuture.com/fapi/v1",
                    "private": "https://testnet.binancefuture.com/fapi/v1",
                },
            },
        })
        binance.set_sandbox_mode(True)

if bybit_config["ENABLED"]:
    bybit = ccxt.bybit({
        "apiKey": bybit_config["API_KEY"],
        "secret": bybit_config["API_SECRET"],
        "enableRateLimit": True,
    })

def create_order(exchange, symbol, side, amount, price=None):
    if price:
        return exchange.create_order(symbol, "limit", side, amount, price)
    else:
        return exchange.create_order(symbol, "market", side, amount)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = json.loads(request.data)

    exchange_name = data["exchange"]
    symbol = data["symbol"]
    side = data["side"]
    amount = data["amount"]
    price = data.get("price", None)

    if exchange_name == "BINANCE-FUTURES" and use_binance_futures:
        order = create_order(binance, symbol, side, amount, price)
    elif exchange_name == "BYBIT" and bybit_config["ENABLED"]:
        order = create_order(bybit, symbol, side, amount, price)
    else:
        return "Invalid exchange name or exchange is not enabled", 400

    return json.dumps(order), 200

if __name__ == "__main__":
    app.run()
