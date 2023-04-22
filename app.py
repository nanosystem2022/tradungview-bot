import os
import json
from flask import Flask, request, jsonify, render_template
import ccxt

app = Flask(__name__)

# خواندن تنظیمات از فایل config.json
with open("config.json") as config_file:
    config = json.load(config_file)

# بررسی تنظیمات و ایجاد نمونه‌های صرافی‌ها
exchanges = {}
if config['EXCHANGES']['BYBIT']['ENABLED']:
    bybit = ccxt.bybit({
        'apiKey': config['EXCHANGES']['BYBIT']['API_KEY'],
        'secret': config['EXCHANGES']['BYBIT']['API_SECRET'],
    })
    exchanges['bybit'] = bybit

if config['EXCHANGES']['binanceusdm']['ENABLED']:
    binance_options = {
        'apiKey': config['EXCHANGES']['binanceusdm']['API_KEY'],
        'secret': config['EXCHANGES']['binanceusdm']['API_SECRET'],
        'options': {'defaultType': 'future'}
    }

    if config['EXCHANGES']['binanceusdm']['TESTNET']:
        binance_options['urls'] = {
            'api': {
                'public': 'https://testnet.binance.vision/api',
                'private': 'https://testnet.binance.vision/api',
                'fapiPublic': 'https://testnet.binancefuture.com/fapi',
                'fapiPrivate': 'https://testnet.binancefuture.com/fapi'
            }
        }

    binance = ccxt.binance(binance_options)
    exchanges['binance'] = binance

position_open = False

def calculate_amount(exchange, symbol, percentage):
    balance = exchange.fetch_balance()
    account_balance = balance['info']['totalWalletBalance']
    order_book = exchange.fetch_order_book(symbol)
    top_bid = order_book['bids'][0][0] if len(order_book['bids']) > 0 else None
    top_ask = order_book['asks'][0][0] if len(order_book['asks']) > 0 else None
    mid_price = (top_bid + top_ask) / 2
    amount = (account_balance * percentage) / mid_price
    return exchange.amount_to_precision(symbol, amount)

@app.route('/webhook', methods=['POST'])
def webhook():
    global position_open
    data = request.get_json()
    print(data)
    
    if position_open:
        if "closelong" in data['strategy.order.action']:
            close_position(data)
        elif "closeshort" in data['strategy.order.action']:
            close_position(data)
    else:
        if "long" in data['strategy.order.action']:
            open_position(data, "long")
        elif "short" in data['strategy.order.action']:
            open_position(data, "short")
            
    return jsonify({})

def open_position(data, side):
    global position_open
    
    symbol = data['ticker']
    exchange = data['exchange'].lower()
    percentage = 0.01  # به عنوان مثال، می‌توانید این مقدار را تغییر دهید
    
    if exchange in exchanges:
        ex = exchanges[exchange]
        amount = calculate_amount(ex, symbol, percentage)
        
        if side == "long":
            ex.create_market_buy_order(symbol, amount)
        elif side == "short":
            ex.create_market_sell_order(symbol, amount)
        
        position_open = True
        print(f"Opened {side} position on {exchange}: {symbol}")

def close_position(data):
    global position_open
    
    symbol = data['ticker']
    exchange = data['exchange'].lower()
    percentage = 1  # 100% of the position will be closed
    
    if exchange in exchanges:
        ex = exchanges[exchange]
        amount = calculate_amount(ex, symbol, percentage)
        
        if "long" in data['strategy.order.action']:
            ex.create_market_sell_order(symbol, amount)
        elif "short" in data['strategy.order.action']:
            ex.create_market_buy_order(symbol, amount)
            
        position_open = False
        print(f"Closed position on {exchange}: {symbol}")

@app.route('/')
def home():
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run()
