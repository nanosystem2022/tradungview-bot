import os
import json
from flask import Flask, request, jsonify, render_template
from ccxt import binance, bybit
import ccxt

app = Flask(__name__)

# بارگذاری پیکربندی از فایل
with open("config.json") as f:
    config = json.load(f)

exchanges = {
    'binance': ccxt.binance(config['EXCHANGES']['binanceusdm']),
    'bybit': ccxt.bybit(config['EXCHANGES']['BYBIT']),
}

for exchange_name, exchange in exchanges.items():
    if config['EXCHANGES'][exchange_name]['TESTNET']:
        exchange.set_sandbox_mode(True)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)
