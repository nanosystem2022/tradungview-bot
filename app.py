import os
import json
from flask import Flask, request , render_template
import ccxt
from ccxt import binance, bybit

app = Flask(__name__)

position_open = False

with open("config.json") as file:
    config = json.load(file)

binance_exchange = ccxt.binance({
    'apiKey': config['EXCHANGES']['binanceusdm']['API_KEY'],
    'secret': config['EXCHANGES']['binanceusdm']['API_SECRET'],
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
    },
    'urls': {
        'api': {
            'public': 'https://testnet.binance.vision/api',
            'private': 'https://testnet.binance.vision/api',
            'fapiPublic': 'https://testnet.binancefuture.com/fapi',
            'fapiPrivate': 'https://testnet.binancefuture.com/fapi'
        }
    }
})

bybit_exchange = ccxt.bybit({
    'apiKey': config['EXCHANGES']['BYBIT']['API_KEY'],
    'secret': config['EXCHANGES']['BYBIT']['API_SECRET'],
    'enableRateLimit': True,
})

if config['EXCHANGES']['binanceusdm']['TESTNET']:
    binance_exchange.set_sandbox_mode(True)

def get_future_balance(exchange, symbol):
    if exchange == "binance":
        balance = binance_exchange.fetch_balance({'type': 'future'})
    elif exchange == "bybit":
        balance = bybit_exchange.fetch_wallet_balance()

    base_currency = symbol.split("/")[0]
    return balance['free'][base_currency]

@app.route('/')
def home():
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    global position_open
    data = json.loads(request.data)
    signal = data['signal']
    symbol = data['symbol']
    exchanges = data['exchanges']

    amount_binance = get_future_balance('binance', symbol)
    amount_bybit = get_future_balance('bybit', symbol)

    responses = []

    if signal == 'closeshort' or signal == 'closelong':
        if position_open:
            position_open = False
            if 'binance' in exchanges:
                responses.append(binance_exchange.create_market_order(symbol, signal.replace("close", ""), amount_binance))
            if 'bybit' in exchanges:
                responses.append(bybit_exchange.create_market_order(symbol, signal.replace("close", ""), amount_bybit))
        else:
            responses.append("هیچ معامله‌ای برای بستن وجود ندارد.")
    elif signal == 'buy' or signal == 'sell':
        if position_open:
            responses.append("یک معامله در حال حاضر باز است. لطفاً ابتدا معامله فعلی را ببندید.")
        else:
            position_open = True
            if 'binance' in exchanges:
                responses.append(binance_exchange.create_market_order(symbol, signal, amount_binance))
            if 'bybit' in exchanges:
                responses.append(bybit_exchange.create_market_order(symbol, signal, amount_bybit))

    return str(responses)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
