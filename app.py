import os
import json
import ccxt
from flask import Flask, request

app = Flask(__name__)

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

exchanges = {}
for name, settings in config['EXCHANGES'].items():
    if settings['ENABLED']:
        exchange_class = getattr(ccxt, name)
        exchange = exchange_class({
            'apiKey': settings['API_KEY'],
            'secret': settings['API_SECRET'],
            'enableRateLimit': True
        })
        if settings.get('TESTNET'):
            exchange.set_sandbox_mode(True)
        exchanges[name] = exchange

position_open = False

@app.route('/webhook', methods=['POST'])
def webhook():
    global position_open
    data = request.get_json()
    if data['type'] == 'closelong' or data['type'] == 'closeshort':
        close_position(data)
    elif not position_open:
        open_position(data)
    return '', 200

def open_position(data):
    global position_open
    side = 'long' if data['type'] == 'long' else 'short'
    amount = data['amount']
    for name, exchange in exchanges.items():
        # TODO: Calculate the amount based on your account balance and the percentage you want to use
        exchange.create_market_order('BTC/USDT', side, amount)
    position_open = True

def close_position(data):
    global position_open
    side = 'close_long' if data['type'] == 'closelong' else 'close_short'
    for name, exchange in exchanges.items():
        # TODO: Close the position based on the side
        pass
    position_open = False

if __name__ == '__main__':
    app.run()
