import os
import ccxt
import json
from flask import Flask, request, jsonify

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
        # تنظیم آدرس API برای محیط TESTNET
        exchanges['binanceusdm'].urls['api'] = {
            'public': 'https://testnet.binancefuture.com/fapi/v1',
            'private': 'https://testnet.binancefuture.com/fapi/v1',
            'testnet': 'https://testnet.binancefuture.com/fapi/v1'
        }

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        data = request.get_json()
        
        if data is not None:
            signal = data.get('signal', None)
            trading_pair = data.get('trading_pair', None)
            side = data.get('side', None)
            percent_of_balance = data.get('percent_of_balance', None)

            if signal is not None and trading_pair is not None and side is not None and percent_of_balance is not None:
                if signal in exchanges:
                    place_order(signal, trading_pair, side, percent_of_balance)

                    return jsonify({"message": "Order placed successfully."})
                else:
                    return jsonify({"message": "Invalid signal."})
            else:
                return jsonify({"message": "Missing required data."})
        else:
            return jsonify({"message": "No data received."})

    return jsonify({"message": "Invalid request method."})

def place_order(exchange, trading_pair, side, percent_of_balance):
    # دریافت موجودی کاربر
    balance = exchanges[exchange].fetch_balance()

    # محاسبه مقدار معامله بر اساس درصد موجودی
    asset = trading_pair.split('/')[0]  # ارز اصلی (مثلا BTC در BTC/USDT)
    asset_balance = balance['total'][asset]
    amount = asset_balance * percent_of_balance / 100

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
