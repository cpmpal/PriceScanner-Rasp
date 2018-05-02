#!/usr/bin/python
import sqlite3
import os
import struct
import datetime
import time
import sys


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

	def makeProduct(self, bar, conn):
		barcodeSel = 'SELECT * FROM BARCODES WHERE BARCODE = "'
		liqcodeSel = 'SELECT * FROM LIQCODE WHERE CODE_NUM = "'
		conn.row_factory = sqlite3.Row
		c = conn.cursor()			
		c.execute(barcodeSel+bar+'";')
		barc = c.fetchone()
		if barc:
			self.barcode = bar
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
			if liqc:
				self.brand = liqc['BRAND']
				self.descrip = liqc['DESCRIP']
				self.setQty(liqc['STD_QTY'])
				self.setPrice(liqc['PRICE'])
				self.setDep(liqc['DEPOSIT'], liqc['DEP_AMT'])
		else:
			self.found = False
			
		conn.close()
		return


	def makePrice(self, price):
		if not price:
			return 'N/A'
		else:
			return str(price)

	def makeQty(self):
		if not self.qty:
			return str(1)
		else:
			return str(self.qty)

	def makeDeposit(self):
		if self.dep:
			if not self.depAmt:
				return str(int(self.makeQty())*0.05)
			else:
				return str(int(self.makeQty())*self.depAmt)
		else:
			return 'N/A'

	def __str__(self):
		s = 'Brand: ' + self.brand + '\n'
		s += 'Description: ' + self.descrip + '\n'
		s += 'Qty: ' + self.makeQty() + '\n'
		s += 'Price: ' + self.makePrice(self.price) + '\n'
		s += 'Single Price: ' + self.makePrice(self.singlePrice) + '\n'
		s += 'Case Price: ' + self.makePrice(self.casePrice) + '\n'
		s += 'Deposit' + self.makeDeposit() + '\n'
		s += 'Barcode: ' + self.barcode + '\n'
		return s

class reader:

	def __init__(self, dbf, codec='latin-1'):			
		self._enc = codec
		path, name = os.path.split(dbf)
		self.dbf = name
		self.f = open(dbf, 'rb')
		self.numrec, self.lenheader, self.recsize = struct.unpack('<xxxxLHH20x', self.f.read(32))
		self.numrec += 1
		if not os.path.isfile(self.dbf+'.size'):
			self.writeNewRecordSize()
		else:
			self.readOldRecordSize()    
		self.numfields = (self.lenheader - 33) // 32
		# The first field is always a one byte deletion flag
		fields = [('DeletionFlag', 'C', 1),]
		for fieldno in range(self.numfields):
		    name, typ, size = struct.unpack('<11sc4xB15x', self.f.read(32))
		    # eliminate NUL bytes from name string  
		    name = name.strip(b'\x00')
		    fields.append((name.decode(self._enc), typ.decode(self._enc), size))
		self.fields = fields
		# Get the names only for DataFrame generation, skip delete flag
		self.columns = [f[0] for f in self.fields[1:]]

		terminator = self.f.read(1)
		assert terminator == b'\r'
		#eat last byte of header
		self.f.read(1)

		# Make a format string for extracting the data. In version 5 DBF, all
		# fields are some sort of structured string
		self.fmt = ''.join(['{:d}s'.format(fieldinfo[2]) for
				    fieldinfo in self.fields])
		self.fmtsiz = struct.calcsize(self.fmt)

	def writeNewRecordSize(self):
		q = open(self.dbf+'.size', 'w')
		q.write(str(self.numrec)+'\n')
		q.close()
		self.oldnum = 0

	def readOldRecordSize(self):
		q = open(self.dbf+'.size', 'r')
		self.oldnum = int(q.readline())
		return self.oldnum

	def recordsAdded(self):
		return self.numrec != self.oldnum
	
	def readRecord(self, delete=False, onceThrough=True):
		if not self.recordsAdded():
			yield None
		else:
			recordDelta = self.numrec - self.oldnum - 1
			recordDelta = (-recordDelta*self.recsize)-1
			if abs(recordDelta) < self.lenheader:
				self.f.seek(self.lenheader, 0)
			else:
				self.f.seek(recordDelta, 2)
			for i in range(self.oldnum, self.numrec):
				test = self.f.read(self.fmtsiz)
				if b'\x1a' in test or len(test) != self.recsize: 
					break
				record = struct.unpack(self.fmt, test)
				self._dtypes = {}
				result = []
				for idx, value in enumerate(record):
					name, typ, size = self.fields[idx]
					# String (character) types, remove excess white space
					if typ == "C":
					    if name == 'DeletionFlag':
						value = (value == '*')
						if name not in self._dtypes:
							self._dtypes[name] = "bool"
					    else:
						    if name not in self._dtypes:
							self._dtypes[name] = "str"
						    value = value.strip()
						   # Convert empty strings to NaN
						    if value == b'':
							value = None
						    else:
							value = value.decode(self._enc)
					# Escape quoted characters
					# Numeric type. Stored as string
					elif typ == "N":
					    # A decimal should indicate a float
					    if b'.' in value:
						if name not in self._dtypes:
						    self._dtypes[name] = "float"
						value = float(value)
						# No decimal, probably an integer, but if that fails,
						# probably NaN
					    else:
						    try:
							if name not in self._dtypes:
								self._dtypes[name] = "int"

							value = int(value)
						    except:
							 # I changed this for SQL->Pandas conversion
							 # Otherwise floats were not showing up correct
							 value = float('nan')

					# Date stores as string "YYYYMMDD", convert to datetime
					elif typ == 'D':
					    
					    try:
						if name not in self._dtypes:
						    self._dtypes[name] = "date"
						y, m, d = int(value[:4]), int(value[4:6]), int(value[6:8])
					    except:
						value = None
					    else:
						value = datetime.date(y, m, d)

					# Booleans can have multiple entry values
					elif typ == 'L':
					    if name not in self._dtypes:
						self._dtypes[name] = "bool"
					    if value in b'TyTt':
						value = True
					    elif value in b'NnFf':
						value = False
					    # '?' indicates an empty value, convert this to NaN
					    else:
						value = float('nan')

					# Floating points are also stored as strings.
					elif typ == 'F':
					    if name not in self._dtypes:
						self._dtypes[name] = "float"
					    try:
						value = float(value)
					    except:
						value = float('nan')

					#Memo field not implemented
					elif typ == 'M':
						value = None
						if name not in self._dtypes:
							self._dtypes[name] = "None"
					else:
					    print(name)
					    err = 'Column type "{}" not yet supported.'
					    raise ValueError(err.format(value))
					result.append(value)
				if not onceThrough:
					self.f.seek(-1*self.fmtsiz, 1)
					onceThrough = True
					yield tuple(result[1:])
					continue
				else:
					yield tuple(result[1:])	
			   
	def readDelete(self):
		#Just read every delete flag, and skip the contents of the record
		for i in range(self.numrec):
			test = self.f.read(self.recsize)
			if b'\x1a' not in test and len(test) == self.recsize: 	
				codeBytes = self.fields[1][2]
				junkBytes = (self.recsize-1) - codeBytes
				strucString = '<c'+str(codeBytes)+'s'+str(junkBytes)+'x'
				flag, code = struct.unpack(strucString, test)
				yield tuple([(flag == '*'), code])
			else:
				break


class sqler:
	

	def __init__(self):
		self.url = 'barcodes.db'
		self.conn = None

	def connect(self):
		self.conn = sqlite3.connect(self.url)
		self.conn.execute('PRAGMA read_uncommitted = true;')
	
	def rowName(self, field, dtype):
		t = ''
		if dtype == 'bool':
			t = 'BOOLEAN'	
		elif dtype == 'date':
			t = 'DATE'
		elif dtype == 'int':
			t = 'INTEGER'
		elif dtype == 'float':
			t = 'FLOAT'
		elif dtype == 'str':
			t = 'TEXT'
		else:
			t = 'NONE'
		return(field[0] + ' ' + t)
	
	def createTable(self, dbf):
		#read 1 row to build the types dictionary
		dbf.readRecord(onceThrough=False).next()
		createStmt = 'CREATE TABLE IF NOT EXISTS '+dbf.dbf[:-4]+' ('
		#Create deletion flag column
		createStmt += self.rowName(dbf.fields[0], dbf._dtypes[dbf.fields[0][0]]) + ', '
		if dbf.dbf.startswith('BARCODES'):
			createStmt += self.rowName(dbf.fields[1], dbf._dtypes[dbf.fields[1][0]]) + ', '
		

		else:
			createStmt += self.rowName(dbf.fields[1], dbf._dtypes[dbf.fields[1][0]]) + ' PRIMARY KEY, '
		

		for field in dbf.fields[2:]:
			createStmt += self.rowName(field, dbf._dtypes[field[0]]) +', '
		createStmt = createStmt[:-2]
		if dbf.dbf.startswith('BARCODES'):
			createStmt += ', PRIMARY KEY (' + dbf.fields[1][0]+', '+dbf.fields[2][0]+') '
		createStmt += ');'
		self.conn.execute(createStmt)
		self.conn.commit()
	
	def insertRows(self, dbf):
		#Build table schema once
		#Generator stutter step reads one line and then rereads all lines
		self.connect()
		self.createTable(dbf)
		#skip deletion flag and update deletions seperately
		insertStmt = 'INSERT OR IGNORE INTO ' + dbf.dbf[:-4] + ' (' 
		for field in dbf.fields[1:]:
			insertStmt += field[0]+', '
		insertStmt = insertStmt[:-2] +') '
		insertStmt += 'VALUES ('
		for f in range(dbf.numfields):
			insertStmt +='?, '
		insertStmt = insertStmt[:-2] + ');'
		self.conn.executemany(insertStmt, dbf.readRecord())
		self.conn.commit()
		self.conn.close()
		dbf.writeNewRecordSize()

	def updateDelete(self, dbf):
		self.connect()
		updateStmt = 'UPDATE ' + dbf.dbf[:-4] + ' SET '
		updateStmt += 'DeletionFlag = (?) WHERE CODE_NUM = (?)'
		a = dbf.readDelete()
		self.conn.executemany(updateStmt, a)
		self.conn.commit()
		self.conn.close()

	def findProduct(self, bar):
		prod = product()
		self.connect()
		prod.makeProduct(bar, self.conn)
		print(prod)

	@staticmethod
	def getProduct(bar):
		prod = product()
		con = sqlite3.connect('barcodes.db')
		prod.makeProduct(bar, con)
		con.close()
		return(prod)

if __name__ == '__main__':
	t1 = time.time()
	d = reader('BARCODES.dbf')
	print d.fields
	test = sqler()
	if d.recordsAdded():
		test.insertRows(d)
		del d
	d = reader('BARCODES.dbf')
	test.updateDelete(d)
	d = reader('LIQCODE.dbf')
	test = sqler()
	if d.recordsAdded():
		test.insertRows(d)
		del d
	d = reader('LIQCODE.dbf')
	test.updateDelete(d)
	t2 = time.time()
	print(t2-t1)
	while True:
		try:
			bar = raw_input("Enter barcode:\n")
			test.findProduct(bar)
		except KeyboardInterrupt:
			break	
