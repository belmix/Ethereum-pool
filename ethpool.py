# -*- coding: utf-8 -*-
import os
import logging
import time
import requests
import json
import sys
import signal
import sqlite3
from flask import Flask, render_template, url_for, request
from threading import Thread, Lock
import Queue
from ethjsonrpc import EthJsonRpc
methods = [
    'web3_clientVersion',
    'net_version',
    'net_peerCount',
    'net_listening',
    'eth_protocolVersion',
    'eth_syncing',
    'eth_coinbase',
    'eth_mining',
    'eth_hashrate',
    'eth_gasPrice',
    'eth_accounts',
    'eth_blockNumber',
    'eth_getCompilers',
    'eth_newPendingTransactionFilter',
    'eth_getWork',

]
import poloniex


# Начальные параметры
SECRET = "CHANGETHIS"
SERVER_NAME = "localhost:5000"
SERVER_POOL = "localhost:5082"
DBSHARE_FILE = "ethshares.db"
DBPAYOUT_FILE = "ethpayout.db"
BLOCK_REWARD = 5.00
FEE = 0.2
COINBASE = "0x88059a92c6a5777e015b432b11120abc26ae8bfe"
polo = poloniex.Poloniex()
polo.timeout = 2
# включение отладки в консоли
DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__) 
shqueue = Queue.Queue ()
bllock = Lock ()
bl = False
paylock = Lock ()
cround = {'shares': 0, 'accounts': {}, 'miners': 0}
croundlock = Lock ()

# Функция запроса к node
def node_request (command, args = []):
	payload = { "method": command, "params": args, "jsonrpc": "2.0", "id": 0 }
	try:
		return requests.post('http://localhost:8545', data=json.dumps(payload), headers={'content-type': 'application/json'}).json()['result']
	except:
		return None

# маршрут по умолчанию стартовая страница
@app.route("/")
# функция index возвращает шаблон index.html
def index():
	ticker = polo.api('returnTicker')
	allprice = (ticker['BTC_ETH'])
	price1 = allprice['last']
	price = price1[0:6]

	ticker2 = polo.api('returnTicker')
	allprice2 = (ticker2['USDT_ETH'])
        price2 = allprice2['last']
	priceUSD = price2[0:5]


	c = EthJsonRpc('localhost', 8545)
	Hashrate = c.eth_hashrate()
	Blocks = c.eth_blockNumber()
	return render_template('index.html', price=price, priceUSD=priceUSD, Hashrate=Hashrate, Blocks=Blocks, cround=cround, server=SERVER_POOL)

# маршрут по умолчанию стартовая блоки
@app.route("/blocks")
# функция blocks возвращает шаблон blocks.html
def blocks ():
        c = EthJsonRpc('localhost', 8545)
	r = c.eth_accounts()
	return render_template('blocks.html', r=r, cround=cround, server=SERVER_POOL)

# маршрут по умолчанию стартовая блоки
@app.route("/stats")
# функция blocks возвращает шаблон stats.html
def stats ():
        c = EthJsonRpc('localhost', 8545)
	r = c.eth_accounts()
	return render_template('stats.html', r=r, cround=cround, server=SERVER_POOL)

# маршрут по умолчанию стартовая блоки
@app.route("/faq")
# функция blocks возвращает шаблон faq.html
def faq ():
        c = EthJsonRpc('localhost', 8545)
	r = c.eth_accounts()
	return render_template('faq.html', r=r, cround=cround, server=SERVER_POOL)

# маршрут по умолчанию стартовая блоки
@app.route("/credits")
# функция blocks возвращает шаблон blocks.html
def credits ():
        c = EthJsonRpc('localhost', 8545)
	r = c.eth_accounts()
	r1 = c.eth_accounts()
	r2 = r1.pop(0)
	item = r.pop(1)
	return render_template('credits.html', r=r, r1=r1, r2=r2, item=item, cround=cround, server=SERVER_POOL)



@app.route("/miner", methods=['POST'])
def miner ():
	address = request.form['address'].replace ('0x', '')
	payouts = []
	paylock.acquire ()
	conn2 = sqlite3.connect(DBPAYOUT_FILE)
      	db2 = conn2.cursor()

	for row in db2.execute ('SELECT * FROM payout WHERE miner=?', [address]):
		payouts.append (row)

	conn2.commit ()
	conn2.close ()
	paylock.release ()

	if address in cround['accounts']:
		rshare = cround['accounts'][address]
	else:
		rshare = 0
	print rshare, cround




      
	return render_template('miner.html',  address=address, payouts=payouts, shares=rshare)



@app.route("/submit", methods=['POST'])
def submitShare ():
	data = request.form
	if data['secret'] == SECRET:
		shqueue.put ((data['miner'], data['mixdigest'], data['diff'], str (time.time ())))
	return ''

@app.route("/foundblock", methods=['POST'])
def foundBlock ():
	bllock.acquire ()
	bl = True
	bllock.release ()


def sendTransaction (address, value):

	tx = { 'from': COINBASE, 'to': address, 'value': value }
  
	node_request ('eth_sendTransaction', [tx])


def db_thread ():
	global cround, bl
	conn = sqlite3.connect(DBSHARE_FILE)
	db = conn.cursor()

	while True:	
		for x in range (10):
			item = shqueue.get()
			db.execute ('INSERT INTO share VALUES (?,?,?,?)', item)	
			shqueue.task_done()
			conn.commit ()

			croundlock.acquire ()
			cround['shares'] += int (item [2])
			if item[0] in cround['accounts']:
				cround['accounts'][item[0]] += int (item [2])
			else:
				cround['accounts'][item[0]] = int (item [2])
			cround['miners'] = len (cround['accounts'])
			croundlock.release ()
		bllock.acquire ()

		# New block, split the reward
		if bl:
			bl = False
			bllock.realease ()

			accounts = {}
			totshare = 0
			reward = BLOCK_REWARD - FEE
			for row in db.execute('SELECT miner, sum(share) FROM share GROUP BY miner'):
				accounts [row [0]] = row [1]
				totshare += row [1]

			# totshare : reward = sharegianni : rewardpergianni
			paylock.acquire ()
			conn2 = sqlite3.connect(DBPAYOUT_FILE)
			db2 = conn2.cursor()

			for acc in accounts:
				racc = accounts[acc] * reward / float (totshare)
				sendTransaction (acc, racc)
				db2.execute ('INSERT INTO payout VALUES (?,?,?,?)', [acc, accounts[acc], totshare, racc, str (time.time ())])	
			conn2.commit ()
			conn2.close ()
			paylock.release()

			db.execute ('DELETE FROM share')	

			croundlock.acquire ()
			cround = {'shares': 0, 'accounts': {}, 'miners': 0}
			croundlock.release ()
		else:
			bllock.realease ()

	conn.close ()

	

if __name__ == "__main__":
	if len (sys.argv) < 2:
		print 'usage:',sys.argv[0],'init|start'
	elif sys.argv[1] == 'init':
		try:
			conn = sqlite3.connect(DBSHARE_FILE)
			db = conn.cursor()
			db.execute('''CREATE TABLE share (miner text, mixdigest text, diff text, date text)''')
			conn.commit()
			conn.close()
		except:
			pass
		try:
			conn = sqlite3.connect(DBPAYOUT_FILE)
			db = conn.cursor()
			db.execute('''CREATE TABLE payout (miner text, shares int, roundshares int, amount real, time text)''')
			conn.commit()
			conn.close()
		except:
			pass
                try:
			conn = sqlite3.connect(DBMINER_FILE)
			db = conn.cursor()
			db.execute('''CREATE TABLE payout (miner text, hashrate int, workers int)''')
			conn.commit()
			conn.close()
		except:
			pass
	elif sys.argv[1] == 'start':
		dbt = Thread(target=db_thread, args=())
		dbt.start()

		with app.app_context():
			url_for('static', filename='bootstrapflatly.min.css')
			url_for('static', filename='font-awesome.min.css')
		app.run(threaded=True)
