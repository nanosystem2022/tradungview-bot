import ccxt
import json
import logging
from flask import Flask, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

with open("config.json") as f:
    config = json.load(f)

binance_config = {
    'apiKey': config["EXCHANGES"]["binanceusdm"]["API_KEY"],
    'secret': config["EXCHANGES"]["binanceusdm"]["API_SECRET"],
    'options': {
        'defaultType': 'future',  # Set the default type to 'future'
    },
}

USE_BINANCE_TESTNET = config["EXCHANGES"]["binanceusdm"]["TESTNET"]

if USE_BINANCE_TESTNET:
    binance_config.update({
        'urls': {
            'api': {
                'public': 'https://testnet.binancefuture.com/fapi/v1',
                'private': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1'
            }
        },
    })

binance = ccxt.binance(binance_config)

bybit_config = {
    'apiKey': config["EXCHANGES"]["BYBIT"]["API_KEY"],
    'secret': config["EXCHANGES"]["BYBIT"]["API_SECRET"],
}

bybit = ccxt.bybit(bybit_config)

def execute_order(exchange, order_type, symbol, percentage, price, side):
    balance = exchange.fetch_balance({'type': 'future'})
    base_currency = symbol.split('/')[0]
    
    if base_currency in balance['total']:
        total_balance = balance['total'][base_currency]
        quantity = total_balance * (percentage / 100)

        if order_type == 'market':
            if side == 'long':
                exchange.create_market_buy_order(symbol, quantity)
            elif side == 'short':
                exchange.create_market_sell_order(symbol, quantity)
        elif order_type == 'limit':
            if side == 'long':
                exchange.create_limit_buy_order(symbol, quantity, price)
            elif side == 'short':
                exchange.create_limit_sell_order(symbol, quantity, price)
        logging.info(f"{exchange.name}: {side} {order_type} order executed for {symbol} with quantity {quantity} and price {price}")
    else:
        logging.error(f"{exchange.name}: Unable to find balance for {base_currency}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    logging.info(f"Received data: {data}")

    try:
        symbol = data['symbol']
        trade_side = data['side']
        trade_type = data['type']
        percentage = data['percentage']
        price = data['price']

        execute_order(binance, trade_type, symbol, percentage, price, trade_side)
        execute_order(bybit, trade_type, symbol, percentage, price, trade_side)

    except Exception as e:
        logging.error(f"Error processing webhook data: {e}")
        return "error", 500

    return "success", 200

if __name__ == '__main__':
    app.run()
