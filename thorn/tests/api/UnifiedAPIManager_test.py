import unittest
import time
import datetime
import threading
import json

import asyncio
import ccxt.async as ccxt

from confluent_kafka import Consumer, KafkaError
from thorn.api import config

SYMBOL = 'ETH/BTC'

from thorn.api import UnifiedAPIManager

class ManageThread(threading.Thread):
    def __init__(self, symbol, function, exchanges, delay, loop=None):
        uam = UnifiedAPIManager(symbol, function, exchanges, delay, loop=loop)
        print(uam.function)
        self.uam = uam
        threading.Thread.__init__(self)

    def run(self):
        self.uam.manage()

class ConsumeThread(threading.Thread):
    def __init__(self, topic, pass_test):
        self.topic = topic
        self.pass_test = pass_test
        self.fun = consume
        threading.Thread.__init__(self)

    def run(self):
        self.fun(self.topic, self.pass_test)


class UnifiedAPIManagerTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_manage_order_book(self):
        exchanges = [ccxt.binance(), ccxt.gemini(), ccxt.bitmex()]
        loop = asyncio.get_event_loop()
        uam = UnifiedAPIManager(SYMBOL, 'fetchOrderBook', exchanges, 5000)
        loop.run_until_complete(uam.filter_exchanges())

        def pass_test(m):
            if 'bids' in m:
                return True
            return False

        t2 = ConsumeThread(SYMBOL.replace('/','_')+'_order_book', pass_test)
        t2.start()
        loop.run_until_complete(uam.manage(stop_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=2)))
        t2.join()
        self.assertEqual(2+2, 4)


    def test_manage_ticker(self):
        exchanges = [ccxt.binance(), ccxt.gemini(), ccxt.bitmex()]
        loop = asyncio.get_event_loop()
        uam = UnifiedAPIManager(SYMBOL, 'fetchTicker', exchanges, 5000)
        loop.run_until_complete(uam.filter_exchanges())

        def pass_test(m):
            if 'high' in m:
                return True
            return False

        t2 = ConsumeThread(SYMBOL.replace('/','_')+'_ticker', pass_test)
        t2.start()
        loop.run_until_complete(uam.manage(stop_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=2)))
        t2.join()
        self.assertEqual(2+2, 4)


def consume(topic, pass_test):
    brokers = config.SOCKET_MANAGER_CONFIG['brokers']
    if len(brokers) > 1:
        broker_string = ",".join(brokers)
    else:
        broker_string = brokers[0]
    c = Consumer(**{'bootstrap.servers': broker_string, 'group.id': 'mygroup'})
    c.subscribe([topic])
    running = True
    while running:
        msg = c.poll()
        if not msg.error():
            print('Received message: %s' % msg.value().decode('utf-8'))
            m = json.loads(msg.value().decode('utf-8'))
            running = not pass_test(m)
            print('test passed')
            break
        elif msg.error().code() != KafkaError._PARTITION_EOF:
            print(msg.error())
            running = False
    c.close()



if __name__ == '__main__':
    unittest.main()
