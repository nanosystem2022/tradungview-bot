import os
import ccxt
import json
from flask import Flask, request, render_template

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

open_order = None

@app.route('/webhook', methods=['POST'])
def webhook():
    global open_order
    data = json.loads(request.data)

    # دریافت اطلاعات سیگنال از وب هوک
    signal = data['signal']
    trading_pair = data['trading_pair']
    side = data['side']
    percent_of_balance = data['percent_of_balance']

    if signal == "closelong" or signal == "closeshort":
        close_order()
        return {
            "message": "Open order closed."
        }

    if open_order is None:
        if signal in exchanges:
            open_order = place_order(signal, trading_pair, side, percent_of_balance)
            return {
                "message": "Order placed successfully."
            }
    else:
        return {
            "message": "An order is already open. Waiting for it to close."
        }

def place_order(exchange, trading_pair, side, percent_of_balance):
    global open_order

    # دریافت موجودی کاربر
    balance = exchanges[exchange].fetch_balance()

    # محاسبه مقدار معامله بر اساس درصد موجودی
    asset = trading_pair.split('/')[0]  # ارز اصلی (مثلا BTC در BTC/USDT)
    asset_balance = balance['total'][asset]
    amount = asset_balance * percent_of_balance / 100

    # تعیین نوع معامله بر اساس side
   
    if side.lower() == "long":
        order_type = "buy"
    elif side.lower() == "short":
        order_type = "sell"
    else:
        raise ValueError("Invalid side value. It must be 'long' or 'short'.")

    # ایجاد سفارش در صرافی مورد نظر
    order = exchanges[exchange].create_order(
        symbol=trading_pair,
        side=order_type,
        type='market',
        amount=amount
    )
    print(f"{exchange.capitalize()} order: ", order)
    return order

def close_order():
    global open_order
    if open_order is not None:
        exchange = open_order['info']['exchange']
        order_id = open_order['id']
        symbol = open_order['symbol']
        exchanges[exchange].cancel_order(order_id, symbol)
        open_order = None
        print(f"Closed order on {exchange.capitalize()}: ", order_id)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0')
