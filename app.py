import os
import ccxt
import json
from flask import Flask, request

app = Flask(__name__)

# خواندن اطلاعات از فایل config.json
with open('config.json') as f:
    config = json.load(f)

exchanges = {}

# تنظیمات برای صرافی Bybit
if config['EXCHANGES']['BYBIT']['ENABLED']:
    exchanges['bybit'] = ccxt.bybit({
        'apiKey': config['EXCHANGES']['BYBIT']['API_KEY'],
        'secret': config['EXCHANGES']['BYBIT']['API_SECRET'],
    })

# تنظیمات برای صرافی Binance
if config['EXCHANGES']['binanceusdm']['ENABLED']:
    exchanges['binanceusdm'] = ccxt.binance({
        'apiKey': config['EXCHANGES']['binanceusdm']['API_KEY'],
        'secret': config['EXCHANGES']['binanceusdm']['API_SECRET'],
        'options': {
            'defaultType': 'future',
        },
    })
    if config['EXCHANGES']['binanceusdm']['TESTNET']:
        exchanges['binanceusdm'].set_sandbox_mode(True)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = json.loads(request.data)

    # دریافت اطلاعات سیگنال از وب هوک
    signal = data['signal']
    trading_pair = data['trading_pair']
    side = data['side']
    amount = data['amount']

    if signal in exchanges:
        place_order(signal, trading_pair, side, amount)

    return {
        "message": "Order placed successfully."
    }

def place_order(exchange, trading_pair, side, amount):
    # ایجاد سفارش در صرافی مورد نظر
    order = exchanges[exchange].create_order(
        symbol=trading_pair,
        side=side,
        type='market',
        amount=amount
    )
    print(f"{exchange.capitalize()} order: ", order)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
