#!/usr/bin/python

from appJar import gui
from threading import Lock
from threading import Thread
import sambaThread
import time
from datetime import datetime
import dbfSqliter
import sqlite3

dbfLock = Lock()
BARCODE_URL = 'barcodes.db'
PRODUCT_FILES = ['BARCODES.dbf', 'LIQCODE.dbf']

class product:
	def __init__(self):
		self.brand = ''
		self.descrip = ''
		self.qty = None
		self.singlePrice = None
		self.casePrice = None
		self.price = None
		self.dep = False
		self.depAmt = None
		self.barcode = ''
		self.code_num = ''
		self.found = False

	def setSinglePrice(self, price):
		if not self.singlePrice:
			self.singlePrice = price
		
	def setPrice(self, price):
		if not self.price:
			if price:
				self.price = price

	def setCasePrice(self, price):
		if not self.casePrice:
			self.casePrice = price

	def setQty(self, qty):
		if not self.qty:
			if not qty <= 0:
				self.qty = qty
			else:
				self.qty = 1

	def setDep(self, d, amt):
		if d == 'Y':
			self.dep = True
			if amt != 0:
				self.depAmt = amt

	def makeProduct(self, bar):
		barcodeSel = 'SELECT * FROM BARCODES WHERE BARCODE = "'
		liqcodeSel = 'SELECT * FROM LIQCODE WHERE CODE_NUM = "'
		conn = sqlite3.connect(BARCODE_URL)
		conn.execute('PRAGMA read_uncommitted = true;')
		conn.row_factory = sqlite3.Row
		c = conn.cursor()			
		c.execute(barcodeSel+bar+'";')
		barc = c.fetchall()[-1]
		self.barcode = bar
		if barc and (not barc['DeletionFlag'] or barc['DeletionFlag']==0):
			self.found = True
			self.code_num = barc['CODE_NUM']
			self.setPrice(barc['PRICE'])
			c.execute(barcodeSel+'S'+bar+'";')
			barc = c.fetchone()
			if barc:
				self.setSinglePrice(barc['PRICE'])
			c.execute(barcodeSel+'C'+bar+'";')
			barc = c.fetchone()
			if barc:
				self.setCasePrice(barc['PRICE'])
			c.execute(liqcodeSel+self.code_num+'";')
			liqc = c.fetchone()
			if liqc and (not liqc['DeletionFlag'] or liqc['DeletionFlag']==0):
				self.brand = liqc['BRAND']
				self.descrip = liqc['DESCRIP']
				self.setQty(liqc['STD_QTY'])
				self.setPrice(liqc['PRICE'])
				self.setDep(liqc['DEPOSIT'], liqc['DEP_AMT'])
			else:
				self.found = False
		else:
			self.found = False
			
		conn.close()
		return


	def makePrice(self, price):
		if not price:
			return 'N/A'
		else:
			return '${:.2f}'.format(price)

	def makeQty(self):
		if not self.qty:
			return str(1)
		else:
			return str(self.qty)

	def makeDeposit(self):
		if self.dep:
			if not self.depAmt:
				return '${:.2f}'.format(int(self.makeQty())*0.05)
			else:
				return '${:.2f}'.format(int(self.makeQty())*self.depAmt)
		else:
			return 'N/A'

	def __str__(self):
		if not self.found:
			return('Product Not Found :(\nPlease ask associate for help\nBarcode: '+self.barcode)
		s = 'Brand: ' + self.brand + '\n'
		s += 'Description: ' + self.descrip + '\n'
		s += 'Qty: ' + self.makeQty() + '\n'
		s += 'Price: ' + self.makePrice(self.price) + '\n'
		s += 'Single Price: ' + self.makePrice(self.singlePrice) + '\n'
		s += 'Case Price: ' + self.makePrice(self.casePrice) + '\n'
		s += 'Deposit: ' + self.makeDeposit() + '\n'
		s += 'Barcode: ' + self.barcode + '\n'
		return s


def meter(meterPercent):
	app.queueFunction(app.showMeter, "progress")
	app.queueFunction(app.setMeter, "progress", meterPercent)
	if meterPercent == 100:
		app.queueFunction(app.hideMeter, "progress")


def findProduct():
	bar = app.getEntry("Barcode")
	prod = product()
	prod.makeProduct(bar)
	return(str(prod))

def updateMessage(mess):
	app.queueFunction(app.setMessage, "prod", mess)
	app.queueFunction(app.setEntry, "Barcode", "")

def entryFunc():
	app.threadCallback(findProduct, updateMessage)

def fileWorker():
	time.sleep(150)
	app.queueFunction(app.setStatusbar, "File Sync: Updating", field=0)
	with dbfLock:
		s = sambaThread.samb()
		status = s.getFile()
	if status: 
		app.queueFunction(app.setStatusbar, "File Sync: Updated", field=0)
	else:
		app.queueFunction(app.setStatusbar, "File Sync: Failed!", field=0)
	
	time.sleep(150)
	fileWorker()

def updateDB():
	app.queueFunction(app.setStatusbar, "DB Sync: Importing Products", field=1)
	for f in PRODUCT_FILES:
		with dbfLock:
			q = dbfSqliter.sqler()
			d = dbfSqliter.reader(f)
			if d.recordsAdded():
				print "Records added in "+f+", adding new entries to db..."
				q.insertRows(d)
				del d
				del q
			app.queueFunction(app.setStatusbar, "DB Sync: Imported "+f, field=1)
	app.queueFunction(app.setStatusbar, "DB Sync: Products Imported", field=1)
	time.sleep(300)

def updateDBDelete():
	hour = datetime.now().hour
	if not (hour >= 2 and hour <= 4):
		time.sleep((2 - hour) % 24)
	else:
		app.queueFunction(app.setStatusbar, "Checking Deleted Entries...", field=2)
		for f in PRODUCT_FILES:
			with dbfLock:
				q = dbfSqliter.sqler()
				d = dbfSqliter.reader(f)
				q.updateDelete(d)
				app.queueFunction(app.setStatusbar, "DB Delete: Updated "+f, field=2)
		app.queueFunction(app.setStatusbar, "DB Delete: Updated", field=2)

if __name__ == "__main__":
	app = gui("Downtown Wine & Spirits Price Scanner", "667x400")
	app.setSize("fullscreen")
	app.addLabel("testLabel", "Scan barcode")
	app.addMeter("progress")
	app.setMeterFill("progress", "green")
	app.addLabelEntry("Barcode")
	app.setEntryWidth('Barcode', 200)
	app.setEntryUpperCase("Barcode")
	app.setFocus("Barcode")
	app.setEntrySubmitFunction("Barcode", entryFunc)
	app.hideMeter("progress")
	app.addMessage("prod", "")
	app.setMessageAnchor('prod', 'center')
	app.setMessageSticky('prod', 'both')
	app.setMessageWidth('prod', 400)
	app.addStatusbar(fields=3, side="left")
	app.thread(fileWorker)
	app.thread(updateDB)
	app.thread(updateDBDelete)
	app.go()



