import os
import json
from flask import Flask, request, render_template
import ccxt

app = Flask(__name__)

# خواندن تنظیمات از فایل config.json
with open("config.json") as config_file:
    config = json.load(config_file)

# ایجاد نمونه‌های ccxt برای صرافی‌ها
exchanges = {}
open_orders = {}
for exchange_name, exchange_config in config["EXCHANGES"].items():
    if exchange_config["ENABLED"]:
        params = {}
        if exchange_name.lower() == "binance" and exchange_config["TESTNET"]:
            params = {
                'options': {'defaultMarket': 'future'},
                'rateLimit': 200,
                'enableRateLimit': True,
                'urls': {
                    'api': {
                        'public': 'https://testnet.binancefuture.com/fapi/v1',
                        'private': 'https://testnet.binancefuture.com/fapi/v1',
                        'v2Public': 'https://testnet.binancefuture.com/fapi/v2',
                        'v2Private': 'https://testnet.binancefuture.com/fapi/v2'
                    }
                }
            }
        exchanges[exchange_name.lower()] = getattr(ccxt, exchange_name.lower())({
            'apiKey': exchange_config["API_KEY"],
            'secret': exchange_config["API_SECRET"],
            **params
        })
        open_orders[exchange_name.lower()] = None

def get_usdt_balance(exchange):
    balance = exchange.fetch_balance(params={"type": "future"})
    usdt_balance = balance.get('USDT', {}).get('free', 0)
    return usdt_balance

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    # پردازش سیگنال‌های تریدینگ ویو
    exchange = data['exchange']
    command = data.get('command', 'open')
    
    if exchange in exchanges:
        if command in ['closelong', 'closeshort']:
            if open_orders[exchange] is not None:
                order_id = open_orders[exchange]
                exchanges[exchange].cancel_order(order_id)
                open_orders[exchange] = None
                return f"معامله {order_id} بسته شد"
            else:
                return "هیچ معامله‌ای برای بستن وجود ندارد"
        elif command == 'open':
            if open_orders[exchange] is None:
                symbol = data['symbol']
                side = data['side']
                amount = get_usdt_balance(exchanges[exchange])
                order = exchanges[exchange].create_market_order(side, symbol, amount)
                open_orders[exchange] = order['id']
                return f"معامله باز شده: {order}"
            else:
                return "معامله‌ای در حال انجام است. لطفا قبل از باز کردن معامله جدید، معامله قبلی را ببندید"
    else:
        return "صرافی نامعتبر است"

# این تابع خطای 404 را مدیریت می‌کند
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

# این تابع خطای 500 را مدیریت می‌کند
@app.errorhandler(500)
def internal_error(error):
    # اینجا می‌توانید کدی برای ثبت خطا در سیستم خود اضافه کنید
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run()
