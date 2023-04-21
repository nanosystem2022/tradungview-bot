import ccxt
import json
from flask import Flask, request, jsonify, render_template
from ccxt import binance, bybit
import ccxt

app = Flask(__name__)

# خواندن تنظیمات از فایل config.json
with open('config.json', 'r') as f:
    config = json.load(f)

# تنظیمات اکانت و API بای بیت
if config['EXCHANGES']['BYBIT']['ENABLED']:
    bybit = ccxt.bybit({
        'apiKey': config['EXCHANGES']['BYBIT']['API_KEY'],
        'secret': config['EXCHANGES']['BYBIT']['API_SECRET'],
    })

# تنظیمات اکانت و API بایننس
if config['EXCHANGES']['binanceusdm']['ENABLED']:
    binance_options = {
        'apiKey': config['EXCHANGES']['binanceusdm']['API_KEY'],
        'secret': config['EXCHANGES']['binanceusdm']['API_SECRET'],
    }

    if config['EXCHANGES']['binanceusdm']['TESTNET']:
        binance_options['urls'] = {
            'api': 'https://testnet.binancefuture.com',
            'www': 'https://testnet.binancefuture.com',
            'test': 'https://testnet.binancefuture.com',
            'stream': 'wss://stream.binancefuture.com/ws',
            'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
            'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
            'fapiData': 'https://testnet.binancefuture.com/futures/data',
        }

    binance = ccxt.binanceusdm(binance_options)

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
    data = request.get_json()
    action = data['action'].upper()
    exchange = data['exchange'].upper()
    symbol = data['symbol']
    side = data['side'].upper()
    percentage = float(data['percentage']) / 100
    open_positions = {
        'BINANCEUSDM': False,
        'BYBIT': False
    }

    if action == 'CLOSESHORT' or action == 'CLOSELONG':
        if open_positions['BINANCEUSDM']:
            close_order = binance.create_market_order(symbol, 'SELL' if action == 'CLOSELONG' else 'BUY', amount)
            open_positions['BINANCEUSDM'] = False

        if open_positions['BYBIT']:
            close_order = bybit.create_market_order(symbol, 'SELL' if action == 'CLOSELONG' else 'BUY', amount)
            open_positions['BYBIT'] = False

    elif action == 'OPEN':
        if not open_positions['BINANCEUSDM'] and not open_positions['BYBIT']:
            amount_binance = calculate_amount(binance, symbol, percentage)
            amount_bybit = calculate_amount(bybit, symbol, percentage)

            if config['EXCHANGES']['binanceusdm']['ENABLED']:
                open_order_binance = binance.create_market_order(symbol, side, amount_binance)
                open_positions['BINANCEUSDM'] = True

            if config['EXCHANGES']['BYBIT']['ENABLED']:
                open_order_bybit = bybit.create_market_order(symbol, side, amount_bybit)
                open_positions['BYBIT'] = True

            return jsonify({'status': 'success'})

@app.route('/balances')
def balances():
    all_balances = {}
    for exchange_name, exchange in exchanges.items():
        try:
            if config['EXCHANGES'][exchange_name]['FUTURES']:
                if exchange.name == 'binance':
                    balances_data = exchange.fapiPrivate_get_balance()
                elif exchange.name == 'bybit':
                    balances_data = exchange.private_get_wallet_balance()['result']

                balances = [
                    {
                        'currency': b['asset'] if exchange.name == 'binance' else b,
                        'amount': float(b['availableBalance']) if exchange.name == 'binance' else float(balances_data[b]['available_balance'])
                    }
                    for b in balances_data
                ]

                all_balances[exchange_name] = balances
            else:
                all_balances[exchange_name] = "Futures trading not enabled"
        except Exception as e:
            all_balances[exchange_name] = str(e)

    all_positions = {}
    for exchange_name, exchange in exchanges.items():
        all_positions[exchange_name] = get_positions(exchange)

    return render_template('balances.html', all_balances=all_balances, all_positions=all_positions)

def get_positions(exchange):
    if exchange.name == 'binance':
        try:
            positions = exchange.fapiPrivate_get_positionrisk()
            formatted_positions = [
                {
                    'symbol': position['symbol'],
                    'type': 'long' if float(position['positionAmt']) > 0 else 'short',
                    'amount': abs(float(position['positionAmt'])),
                    'entry_price': float(position['entryPrice']),
                    'pnl': float(position['unRealizedProfit'])
                }
                for position in positions if float(position['positionAmt']) != 0
            ]
            return formatted_positions
        except Exception as e:
            print(f"Error getting positions: {str(e)}")
            return []

    elif exchange.name == 'bybit':
        try:
            positions = exchange.private_get_position_list()['result']
            formatted_positions = [
                {
                    'symbol': position['symbol'],
                    'type': position['side'].lower(),
                    'amount': float(position['size']),
                    'entry_price': float(position['entry_price']),
                    'pnl': float(position['unrealised_pnl'])
                }
                for position in positions
            ]
            return formatted_positions
        except Exception as e:
            print(f"Error getting positions: {str(e)}")
            return []
    return []

@app.route("/")
def home():
    return render_template("index.html")

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html"), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
