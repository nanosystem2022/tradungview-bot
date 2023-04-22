import ccxt
import json
from flask import Flask, request
from ccxt.base.errors import BadRequest

app = Flask(__name__)

with open("config.json") as config_file:
    config = json.load(config_file)

binance_config = config["EXCHANGES"]["binanceusdm"]
bybit_config = config["EXCHANGES"]["BYBIT"]

class FuturesTradingBot:
    def __init__(self, exchange, api_key, api_secret, testnet=False):
        self.exchange = exchange
        self.exchange.apiKey = api_key
        self.exchange.secret = api_secret
        self.exchange.set_sandbox_mode(enabled=testnet)
        self.current_position = None

    def get_margin_balance(self, symbol):
        margin_account = self.exchange.fetch_balance({'type': 'future'})
        margin_balance = margin_account['info']['availableMargin']
        return float(margin_balance)

    def place_order(self, symbol, side, percentage, type='market'):
        if self.current_position:
            return

        balance = self.get_margin_balance(symbol)
        amount = balance * percentage / 100

        order = {
            'symbol': symbol,
            'side': side,
            'type': type,
            'quantity': amount,
        }
        try:
            result = self.exchange.create_order(**order)
            self.current_position = result
            print(f"Opened {side} position: {result}")
        except BadRequest as e:
            print(f"Error placing order: {e}")

    def close_position(self, symbol):
        if not self.current_position:
            return

        side = 'buy' if self.current_position['side'] == 'sell' else 'sell'
        order = {
            'symbol': symbol,
            'side': side,
            'type': 'market',
            'quantity': self.current_position['info']['executedQty'],
        }
        try:
            result = self.exchange.create_order(**order)
            print(f"Closed position: {result}")
            self.current_position = None
        except BadRequest as e:
            print(f"Error closing position: {e}")

binance = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
    },
})

bybit = ccxt.bybit({
    'enableRateLimit': True,
})

binance_bot = FuturesTradingBot(binance, binance_config["API_KEY"], binance_config["API_SECRET"], testnet=binance_config["TESTNET"])
bybit_bot = FuturesTradingBot(bybit, bybit_config["API_KEY"], bybit_config["API_SECRET"])

@app.route('/webhook', methods=['POST'])
def webhook():
    data = json.loads(request.data)

    symbol = data['symbol']
    side = data['side']
    exchange = data['exchange'].lower()

    if side.lower() == 'closelong' or side.lower() == 'closeshort':
        if exchange == 'binanceusdm' and binance_config["ENABLED"]:
            binance_bot.close_position(symbol)
        elif exchange == 'bybit' and bybit_config["ENABLED"]:
            bybit_bot.close_position(symbol)
        elif exchange == 'both':
            if binance_config["ENABLED"]:
                binance_bot.close_position(symbol)
            if bybit_config["ENABLED"]:
                bybit_bot.close_position(symbol)
    else:
        percentage = data['percentage']

        if exchange == 'binanceusdm' and binance_config["ENABLED"]:
            binance_bot.place_order(symbol, side, percentage)
        elif exchange == 'bybit' and bybit_config["ENABLED"]:
            bybit_bot.place_order(symbol, side, percentage)
        elif exchange == 'both':
            if binance_config["ENABLED"]:
                binance_bot.place_order(symbol, side, percentage)
            if bybit_config["ENABLED"]:
                bybit_bot.place_order(symbol, side, percentage)

    return {
        'code': 'success',
        'message': 'Webhook received and processed'
    }

if __name__ == '__main__':
    app.run()
