#!/usr/bin/python
import sqlite3
import os
import struct
import datetime
import time

class reader:

	def __init__(self, dbf, codec='latin-1'):			
		self._enc = codec
		path, name = os.path.split(dbf)
		self.dbf = name
		self.f = open(dbf, 'rb')
		self.numrec, self.lenheader = struct.unpack('<xxxxLH22x', 
			self.f.read(32))
		self.numrec += 1    
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

	def readRecord(self, delete=False):
		onceThrough = False	
		for i in range(self.numrec):
			test = self.f.read(self.fmtsiz)
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

					y, m, d = int(value[:4]), int(value[4:6]), \
						  int(value[6:8])
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
				if delete:
					yield tuple([result[0], result[1]])
				else:
					yield tuple(result[1:])
				continue
			if delete:
				yield tuple([result[0], result[1]])
			else:
				yield tuple(result[1:])
		    

class sqler:
	

	def __init__(self):
		self.url = 'barcodes.db'
		self.conn = None

	def connect(self):
		self.conn = sqlite3.connect(self.url)
	
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
		d.readRecord().next()
		createStmt = 'CREATE TABLE IF NOT EXISTS '+dbf.dbf[:-4]+' ('
		#Create deletion flag column
		createStmt += self.rowName(dbf.fields[0], dbf._dtypes[dbf.fields[0][0]]) + ', '
		createStmt += self.rowName(dbf.fields[1], dbf._dtypes[dbf.fields[1][0]]) + ' PRIMARY KEY, '
		

		for field in dbf.fields[2:]:
			createStmt += self.rowName(field, dbf._dtypes[field[0]]) +', '
		createStmt = createStmt[:-2]+');'
		c = self.conn.cursor()
		c.execute(createStmt)
		self.conn.commit()
	
	def insertRows(self, dbf):
		#Build table schema once
		#Generator stutter step reads one line and then rereads all lines
		self.connect()
		self.createTable(d)
		c = self.conn.cursor()
		#skip deletion flag and update deletions seperately
		insertStmt = 'INSERT OR IGNORE INTO ' + dbf.dbf[:-4] + ' (' 
		for field in dbf.fields[1:]:
			insertStmt += field[0]+', '
		insertStmt = insertStmt[:-2] +') '
		insertStmt += 'VALUES ('
		for f in range(d.numfields):
			insertStmt +='?, '
		insertStmt = insertStmt[:-2] + ')'
		c.executemany(insertStmt, d.readRecord())
		self.conn.commit()
		self.conn.close()

	def updateDelete(self, dbf):
		self.connect()
		c = self.conn.cursor()
		updateStmt = 'UPDATE ' + dbf.dbf[:-4] + ' SET '
		updateStmt += 'DeletionFlag = (?) WHERE CODE_NUM = (?)'
		a = d.readRecord(delete=True)
		c.executemany(updateStmt, a)
		self.conn.commit()
		self.conn.close()

	def findProduct(self, bar):
		self.connect()
		selectStmt = 'SELECT * from BARCODES WHERE BARCODE = "'+bar+'"'
		c = self.conn.cursor()
		c.execute(selectStmt)
		prod = c.fetchone()
		print(prod)
		self.conn.close()

if __name__ == '__main__':
	t1 = time.time()
	d = reader('BARCODES.dbf')
	test = sqler()
	test.insertRows(d)
	del d
	d = reader('BARCODES.dbf')
	test.updateDelete(d)
	d = reader('LIQCODE.dbf')
	test = sqler()
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
