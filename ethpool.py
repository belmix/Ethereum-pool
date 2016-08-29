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
    'eth_hashrate',
    'eth_accounts',
]
import poloniex


# Начальные параметры
SECRET = "CHANGETHIS"
# адрес веб интерфейса должен совпадать с указаным в 
# /usr/local/lib/python2.7/dist-packages/flask/app.py
SERVER_NAME = "localhost:5000"
# адрес пула для подключения майнеров
SERVER_POOL = "localhost:5082"
# базы данных
DBSHARE_FILE = "ethshares.db"
DBPAYOUT_FILE = "ethpayout.db"
# объём блока, количество монет
BLOCK_REWARD = 5.00
# комиссия пула, остаётся на кошельке пула
FEE = 0.2
# адрес кошелька пула
COINBASE = "0x88059a92c6a5777e015b432b11120abc26ae8bfe"
polo = poloniex.Poloniex()
# время запроса курса валют с polonex
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
# функция index возвращает шаблон index.html c переменными курса валют от BTC и USD
# ЧТО НЕ СДЕЛАНО!
# НЕОБХОДИМО РЕАЛИЗОВАТЬ ПОЛУЧЕНИЕ ИНФОРМАЦИИ О КОЛИЧЕСТВЕ WORKERS НА ПУЛЕ ВЫВЕСТИ ТАБЛИЦУ ТОП 10 МАЙНЕРОВ ПО HASHRATE, 
# СДЕЛАТЬ ВЫВОД ОСТАВШЕГОСЯ ВРЕМЕНИ ДО ОБНОВЛЕНИЯ DAG
def index():
	# price курс BTC_ETH
	ticker = polo.api('returnTicker')
	allprice = (ticker['BTC_ETH'])
	price1 = allprice['last']
	price = price1[0:6]
	# priceUSD курс USDT_ETH
	ticker2 = polo.api('returnTicker')
	allprice2 = (ticker2['USDT_ETH'])
        price2 = allprice2['last']
	priceUSD = price2[0:5]
	# запрос хэшрейтинга пула и количества блоков сети
	c = EthJsonRpc('localhost', 8545)
	Hashrate = c.eth_hashrate()
	Blocks = c.eth_blockNumber()
	return render_template('index.html', price=price, priceUSD=priceUSD, Hashrate=Hashrate, Blocks=Blocks, cround=cround, server=SERVER_POOL)

# маршрут блоки возвращает blocks.html
@app.route("/blocks")
# функция blocks возвращает шаблон blocks.html в настоящее время не реализована

def blocks ():
	# ЧТО НЕ СДЕЛАНО!
	# Необходимо сформировать вывод таблицы найденных пулом блоков
	return render_template('blocks.html',cround=cround, server=SERVER_POOL)

# маршрут статистика возвращает stats.html
@app.route("/stats")
# функция stats возвращает шаблон stats.html в настоящее время не реализована
def stats ():
	# ЧТО НЕ СДЕЛАНО!
	# Необходимо сформировать вывод графика за 24 часа по Хэшретйнгу и Найденным блокам
	return render_template('stats.html', cround=cround, server=SERVER_POOL)

# маршрут справка возвращает faq.html
@app.route("/faq")
# функция faqs возвращает шаблон faq.html реализован
def faq ():
	# ЧТО НЕ СДЕЛАНО!
	# Необходимо прописать свои настроки в справке для подлючения
	return render_template('faq.html', cround=cround, server=SERVER_POOL)

# маршрут кредиты возвращает шаблон credits.html
@app.route("/credits")
# функция credits возвращает шаблон credits.html
def credits ():
	reward = BLOCK_REWARD - FEE
	accounts = {}
	totshare = 0
        c = EthJsonRpc('localhost', 8545)
	posts = c.eth_accounts()
	conn = sqlite3.connect(DBSHARE_FILE)
	db = conn.cursor()
	for row in db.execute('SELECT miner, sum(diff) FROM share GROUP BY miner'):
	 	accounts [row [0]] = row [1]
		totshare += row [1]
	for acc in accounts:
		racc = accounts[acc] * reward / float (totshare)
	conn.commit ()
	conn.close ()
	return render_template('credits.html', cround=cround, posts=posts, accounts=accounts, totshare=totshare, server=SERVER_POOL)
	# ЧТО НЕ СДЕЛАНО!
	# Необходимо сформировать таблицу аккаунт, хэшрейт, шары (аккаунт - шары сделано)

# маршрут майнер возвращает шаблон miner.html с переменными аккаунт, выплаты, шары
@app.route("/miner", methods=['POST'])
# функция miner возвращает шаблон miner.html
def miner ():
	# ЧТО НЕ СДЕЛАНО!
	# Необходимо вывести количество workers, общий хэшрейт майнера
	# Необходимо сформировать таблицу название workers,, хэшрейт workers, усреднённый хэшрейт workers, шары workers
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
	
# Функция выплаты  используються две переменные address - адрес куда отправить и value сколько
# tx составная переменная для запроса на выплату, COINBASE константа указывается ранее c этого адреса уходит перевод
# функция node_request запрос в geth на выплату в соотвествии с указанными в строке параметрами

def sendTransaction (address, value):

	tx = { 'from': COINBASE, 'to': address, 'value': value }
  
	node_request ('eth_sendTransaction', [tx])


# Поток приложения работает как служба ожидая условий для выполнения
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

		# Событие найден блок
		if bl:
			bl = False
			bllock.realease ()
			# Обнуляем переменные адреса и шар
			accounts = {}
			totshare = 0
			# Вычитаем из полученого блока коммисию пула
			reward = BLOCK_REWARD - FEE
			# Запрашиваем из базы данных адреса майнеров и количество отправленных шар
			for row in db.execute('SELECT miner, sum(share) FROM share GROUP BY miner'):
				accounts [row [0]] = row [1]
				totshare += row [1]

			# totshare : reward = sharegianni : rewardpergianni
			# Делаем разблокировку выплат
			paylock.acquire ()
			# Побдключаемся к базе данных выплат для записи данных о платежах
			conn2 = sqlite3.connect(DBPAYOUT_FILE)
			db2 = conn2.cursor()
			# запускаем цикл перевода майнерам
			for acc in accounts:
				racc = accounts[acc] * reward / float (totshare)
				# Вызов функции оплаты
				sendTransaction (acc, racc)
				# Запись в базу выплат информации об оплате
				db2.execute ('INSERT INTO payout VALUES (?,?,?,?)', [acc, accounts[acc], totshare, racc, str (time.time ())])	
			conn2.commit ()
			# отключаемся от базы
			conn2.close ()
			#  Закрываем возможность выплат, защита пула
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
	elif sys.argv[1] == 'start':
		dbt = Thread(target=db_thread, args=())
		dbt.start()

		with app.app_context():
			url_for('static', filename='bootstrapflatly.min.css')
			url_for('static', filename='font-awesome.min.css')
		app.run(threaded=True)
