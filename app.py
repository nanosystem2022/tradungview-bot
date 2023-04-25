import json
import ccxt
from flask import Flask, request

# بارگذاری تنظیمات از فایل config.json
with open('config.json', 'r') as f:
    config = json.load(f)

app = Flask(__name__)

# ساخت نمونه‌های ccxt برای صرافی‌های فعال
exchanges = {}
for exchange_id, exchange_config in config['EXCHANGES'].items():
    if exchange_config['ENABLED']:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'apiKey': exchange_config['API_KEY'],
            'secret': exchange_config['API_SECRET'],
            'enableRateLimit': True,
        })

        # افزودن حالت تستنت برای بایننس
        if exchange_id == 'binanceusdm' and exchange_config.get('TESTNET', False):
            exchange.set_sandbox_mode(True)
            exchange.urls['api'] = {
                'public': 'https://testnet.binancefuture.com/fapi/v1',
                'private': 'https://testnet.binancefuture.com/fapi/v1',
            }

        exchanges[exchange_id] = exchange

def get_usable_balance(exchange, symbol):
    try:
        balance = exchange.fetch_balance({'type': 'future'})
        base_currency = symbol.split('/')[0]
        quote_currency = symbol.split('/')[1]

        if exchange.id == 'binanceusdm':
            return balance['info']['assets'][0]['walletBalance']
        else:
            return balance[quote_currency]['free']

    except Exception as e:
        print(f"خطا در دریافت موجودی از {exchange.id}: {e}")
        return None

open_order = False

@app.route('/webhook', methods=['POST'])
def webhook():
    global open_order
    data = request.get_json(force=True)
    signal = data['signal']
    symbol = data['symbol']

    if signal == 'closelong' or signal == 'closeshort':
        # بستن معامله
        if not open_order:
            print("هیچ معامله‌ای برای بستن وجود ندارد.")
            return {"status": "no_open_order"}

        for exchange_id, exchange in exchanges.items():
            try:
                # بستن معامله در صرافی
                side = 'sell' if signal == 'closelong' else 'buy'
                response = exchange.create_market_order(symbol, side, 1)  # مقدار '1' را باید با مقدار معامله باز جایگزین کنید.
                print(f"معامله با موفقیت در {exchange_id} بسته شد: {response}")
                open_order = False
            except Exception as e:
                print(f"خطا در بستن معامله در {exchange_id}: {e}")

    else:
        if open_order:
            print("یک معامله باز است. معامله جدید باز نمی‌کنیم.")
            return {"status": "order_already_open"}

        side = data['side']
        percentage_of_balance = float(data['percentage_of_balance'])

        # انجام معامله در صرافی‌های فعال
        for exchange_id, exchange in exchanges.items():
            try:
                balance = get_usable_balance(exchange, symbol)
                if balance is None:
                    continue

                amount = (balance * percentage_of_balance) / 100
                market = exchange.markets[symbol]
                params = {'symbol': symbol, 'side': side, 'type': 'market', 'quantity': amount}
                response = exchange.create_order(**params)
                print(f"معامله با موفقیت در {exchange_id} انجام شد: {response}")
                open_order = True
            except Exception as e:
                print(f"خطا در انجام معامله در {exchange_id}: {e}")

    return {"status": "success"}

if __name__ == '__main__':
    app.run()
