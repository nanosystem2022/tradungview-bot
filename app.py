import os
import json
import ccxt
from flask import Flask, request, render_template
from errors import errors_bp

app = Flask(__name__)
app.register_blueprint(errors_bp)

# خواندن تنظیمات از فایل config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# ایجاد اتصال به صرافی‌ها
exchanges = {}
if config['EXCHANGES']['binanceusdm']['ENABLED']:
    exchange_config = {
        'apiKey': config['EXCHANGES']['binanceusdm']['API_KEY'],
        'secret': config['EXCHANGES']['binanceusdm']['API_SECRET'],
        'options': {'defaultType': 'future'},
        'enableRateLimit': True
    }
    if config['EXCHANGES']['binanceusdm']['TESTNET']:
        exchange_config['urls'] = {
            'api': {
                'public': 'https://testnet.binancefuture.com/fapi/v1',
                'private': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1'
            }
        }
    exchanges['binanceusdm'] = ccxt.binance(exchange_config)

if config['EXCHANGES']['BYBIT']['ENABLED']:
    exchanges['bybit'] = ccxt.bybit({
        'apiKey': config['EXCHANGES']['BYBIT']['API_KEY'],
        'secret': config['EXCHANGES']['BYBIT']['API_SECRET'],
        'enableRateLimit': True
    })

open_position = False

@app.route('/')
def index():
    return "Hello, World!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        print("دریافت سیگنال:", data)

        exchange = data['exchange'].lower()
        if exchange in exchanges:
            execute_trade(exchanges[exchange], data)
        else:
            print(f"صرافی {exchange} فعال نیست.")

        return {
            'status': 'success'
        }, 200
    except Exception as e:
        print(f"خطا در تابع webhook: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }, 500

def execute_trade(exchange, data):
    global open_position

    symbol = data['symbol']
    side = data['side']
    if 'percentage' in data:
        percentage = float(data['percentage'])
    price = float(data['price'])

    if side == 'closelong' or side == 'closeshort':
        if open_position:
            close_position(exchange, symbol, side)
            open_position = False
        else:
            print("هیچ معامله‌ای برای بستن وجود ندارد.")
    else:
        if not open_position:
            if 'percentage' in data:
                # دریافت موجودی کاربر
                balance = exchange.fetch_balance()

                # محاسبه مقدار معامله بر اساس درصد موجودی
                trade_amount = (balance['total']['USDT'] * percentage) / 100

                # باز کردن معامله
                open_position(exchange, symbol, side, trade_amount, price)
                open_position = True
            else:
                print("درصد موجودی در داده‌های دریافتی موجود نیست.")
        else:
            print("معامله‌ای در حال اجرا است و قادر به باز کردن معامله جدید نیستیم.")

def open_position(exchange, symbol, side, amount, price):
    try:
        order = exchange.create_order(symbol, 'limit', side, amount, price)
        print(f"معامله {side} باز شد: {order}")
    except Exception as e:
        print(f"خطا در باز کردن معامله: {e}")

def close_position(exchange, symbol, side):
    try:
        order = exchange.create_order(symbol, 'market', side, None)
        print(f"معامله {side} بسته شد: {order}")
    except Exception as e:
        print(f"خطا در بستن معامله: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
