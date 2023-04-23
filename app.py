import ccxt
import json
import logging
from flask import Flask, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

USE_BINANCE_TESTNET = True  # Set to False to use the real Binance environment

binance_config = {
    'apiKey': 'YOUR_BINANCE_API_KEY',
    'secret': 'YOUR_BINANCE_SECRET_KEY',
    'options': {
        'defaultType': 'future',  # Set the default type to 'future'
    },
}

if USE_BINANCE_TESTNET:
    binance_config.update({
        'urls': {
            'api': {
                'public': 'https://testnet.binancefuture.com',
                'private': 'https://testnet.binancefuture.com',
            }
        },
    })

binance = ccxt.binance(binance_config)

bybit = ccxt.bybit({
    'apiKey': 'YOUR_BYBIT_API_KEY',
    'secret': 'YOUR_BYBIT_SECRET_KEY',
})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    logging.info(f"Received data: {data}")

    try:
        symbol = data['symbol']
        trade_side = data['side']
        trade_type = data['type']
        quantity = data['quantity']
        price = data['price']

        if trade_type == 'market':
            execute_market_order(binance, symbol, quantity, trade_side)
            execute_market_order(bybit, symbol, quantity, trade_side)
        elif trade_type == 'limit':
            execute_limit_order(binance, symbol, quantity, price, trade_side)
            execute_limit_order(bybit, symbol, quantity, price, trade_side)

    except Exception as e:
        logging.error(f"Error processing webhook data: {e}")
        return "error", 500

    return "success", 200

def execute_market_order(exchange, symbol, quantity, side):
    try:
        if side == 'long':
            exchange.create_market_buy_order(symbol, quantity)
        elif side == 'short':
            exchange.create_market_sell_order(symbol, quantity)
        logging.info(f"{exchange.name}: {side} market order executed for {symbol} with quantity {quantity}")
    except Exception as e:
        logging.error(f"{exchange.name}: Error executing {side} market order for {symbol}: {e}")

def execute_limit_order(exchange, symbol, quantity, price, side):
    try:
        if side == 'long':
            exchange.create_limit_buy_order(symbol, quantity, price)
        elif side == 'short':
            exchange.create_limit_sell_order(symbol, quantity, price)
        logging.info(f"{exchange.name}: {side} limit order executed for {symbol} with quantity {quantity} and price {price}")
    except Exception as e:
        logging.error(f"{exchange.name}: Error executing {side} limit order for {symbol}: {e}")

if __name__ == '__main__':
    app.run()
