import json
import ccxt
from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)

with open("config.json") as config_file:
    config = json.load(config_file)

def init_exchange(exchange_id, exchange_config):
    if exchange_config.get("TESTNET"):
        if exchange_id == "binance":
            exchange = ccxt.binance({
                "apiKey": exchange_config["API_KEY"],
                "secret": exchange_config["API_SECRET"],
                "options": {
                    "defaultType": "future"
                },
                "urls": {
                    "api": {
                        "fapiPublic": "https://testnet.binancefuture.com/fapi/v1",
                        "fapiPrivate": "https://testnet.binancefuture.com/fapi/v1"
                    }
                }
            })
        else:
            raise ValueError(f"Testnet not supported for '{exchange_id}'")
    else:
        exchange = getattr(ccxt, exchange_id)(exchange_config)

    return exchange

exchanges = {
    exchange_id: init_exchange(exchange_id, exchange_config)
    for exchange_id, exchange_config in config["EXCHANGES"].items()
    if exchange_config["ENABLED"]
}

def exchange_configured(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        exchange = exchanges.get(request.args.get("exchange_id"))
        if exchange is None:
            return jsonify({"error": "Exchange not configured"}), 400
        return f(exchange, *args, **kwargs)
    return decorated_function

@app.route("/webhook", methods=["POST"])
@exchange_configured
def webhook(exchange):
    signal = request.json
    try:
        order = execute_order(exchange, signal)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(order.info)

def execute_order(exchange, signal):
    order_type = signal['order_type']
    side = signal['side']
    symbol = signal['symbol']
    amount = signal['amount']
    leverage = signal.get('leverage', None)

    if leverage:
        if hasattr(exchange, "set_leverage"):
            exchange.set_leverage(leverage, symbol)
        else:
            raise ValueError("The exchange does not support setting leverage.")

    if order_type == 'market':
        if side == 'buy' or side == 'long':
            order = exchange.create_market_buy_order(symbol, amount)
        elif side == 'sell' or side == 'short':
            order = exchange.create_market_sell_order(symbol, amount)
        else:
            raise ValueError(f"Invalid side '{side}' in signal")
    elif order_type == 'limit':
        price = signal['price']
        if side == 'buy' or side == 'long':
            order = exchange.create_limit_buy_order(symbol, amount, price)
        elif side == 'sell' or side == 'short':
            order = exchange.create_limit_sell_order(symbol, amount, price)
        else:
            raise ValueError(f"Invalid side '{side}' in signal")
    else:
        raise ValueError(f"Invalid order type '{order_type}' in signal")

    return order

if __name__ == "__main__":
    app.run()
