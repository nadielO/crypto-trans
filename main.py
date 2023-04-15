import asyncio
import logging
from firebase_admin import credentials, initialize_app, firestore
from web3 import HTTPProvider, Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account


# Set up Firebase
cred = credentials.Certificate("key.json")
initialize_app(cred)
db = firestore.client()

# Set up Web3 connection
w3 = Web3(HTTPProvider('https://mainnet.infura.io/v3/303f1ceb424844a4a1919910c7cac256'))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Set up accounts
private_key = '43cf6c1bb374a39fc5ed619f68f897e74cfc1c8105e21ea49e74fc96a9854134'
blocked_address = '0xf5c1a70f6739b92f97cd53c3160362c1305e91a8'
sending_address = '0x1412B8513067300edC25013a6b2c83218f8bfCd9'
sending_address_private_key = 'b4e567c69a9c721ffcb546fa11363f75a63495fb8ba5c6febcea31dd45f50446'

account = Account.from_key(private_key)
sending_account = Account.from_key(sending_address_private_key)

# Set up event filter for specific address
my_address = '0x7502A58DcbB3df0003669741A030BA1139952dad'
event_filter = w3.eth.filter({
    'fromBlock': 'latest',
    'toBlock': 'latest',
    'address': my_address
})

# Set up logging
logging.basicConfig(filename='app.log', filemode='w',
                    format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO)


async def handle_events():
    while True:
        for event in event_filter.get_new_entries():
            # Check if sending to blocked wallet
            if event['to'] == blocked_address:
                # Block transaction by sending to another wallet
                try:
                    tx_hash = w3.eth.send_transaction({
                        'to': sending_address,
                        'from': sending_account.address,
                        'value': event['value'],
                        'gas': 21000,
                        'gasPrice': w3.eth.gas_price,
                        'nonce': w3.eth.getTransactionCount(sending_account.address)
                    })
                    message = f'Transaction to {blocked_address} blocked. Sent to {sending_address} instead. Tx hash: {tx_hash.hex()}'
                    print(message)
                    logging.info(message)
                    db.collection('logs').add({
                        'message': message,
                        'timestamp': firestore.SERVER_TIMESTAMP
                    })
                except Exception as e:
                    message = f'Error blocking transaction: {str(e)}'
                    print(message)
                    logging.error(message)
                    db.collection('logs').add({
                        'message': message,
                        'timestamp': firestore.SERVER_TIMESTAMP
                    })
            else:
                message = f'Incoming transaction to {event["to"]} for {event["value"]} wei'
                print(message)
                logging.info(message)
                db.collection('logs').add({
                    'message': message,
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
        # Sleep for a short period to reduce CPU usage
        await asyncio.sleep(1)


async def main():
    await handle_events()

if __name__ == "__main__":
    asyncio.run(main())
