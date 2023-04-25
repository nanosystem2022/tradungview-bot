import json
from flask import Flask, request
import ccxt
from ccxt.base.errors import NetworkError, BadRequest, InsufficientFunds, RateLimitExceeded

app = Flask(__name__)

with open("config.json") as config_file:
    config = json.load(config_file)

exchanges = {
    "binanceusdm": ccxt.binanceusdm({
        "apiKey": config["EXCHANGES"]["binanceusdm"]["API_KEY"],
        "secret": config["EXCHANGES"]["binanceusdm"]["API_SECRET"],
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
        "test": config["EXCHANGES"]["binanceusdm"]["TESTNET"],
        "urls": {
            "api": {
                "public": "https://testnet.binancefuture.com/fapi/v1/",
                "private": "https://testnet.binancefuture.com/fapi/v1/"
            } if config["EXCHANGES"]["binanceusdm"]["TESTNET"] else {}
        }
    }),
    "bybit": ccxt.bybit({
        "apiKey": config["EXCHANGES"]["BYBIT"]["API_KEY"],
        "secret": config["EXCHANGES"]["BYBIT"]["API_SECRET"],
        "enableRateLimit": True,
    }),
}

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "side" not in data or "symbol" not in data or "price" not in data:
        return "Missing required data in the webhook payload", 400

    side = data["side"].lower()
    symbol = data["symbol"]
    price = float(data["price"])

    for exchange_id, exchange in exchanges.items():
        if config["EXCHANGES"][exchange_id]["ENABLED"]:
            try:
                market = exchange.load_markets()
                market_data = market[symbol]
                amount = calculate_amount(price, market_data)

                order = exchange.create_market_order(symbol, side, amount)
                print(f"Order placed on {exchange_id}: {order}")

            except (NetworkError, BadRequest, InsufficientFunds, RateLimitExceeded) as e:
                print(f"Error on {exchange_id}: {e}")

    return "OK", 200

def calculate_amount(price, market_data):
    min_cost = market_data["limits"]["cost"]["min"]
    amount = min_cost / price
    return max(amount, market_data["limits"]["amount"]["min"])

if __name__ == "__main__":
    app.run()
