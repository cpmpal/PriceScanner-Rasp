#!/usr/bin/python
from smb.SMBConnection import SMBConnection
from nmb.NetBIOS import NetBIOS
from threading import Thread
from threading import Lock
from simpledbf import Dbf5
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy_utils import create_database, database_exists
import time

dbfLock = Lock()

class samba:

	def __init__(self):
		self.server_ip = None
		self.server_name = 'DOWTOWNSERVER1'

	def getServerIP(self):
		q = NetBIOS()
		self.server_ip = q.queryName(self.server_name)[0]
		q.close()	

	def getFiles(self):
		self.user = ''
		self.password = ''
		self.client_machine_name = 'raspScanner'

		try:
			self.getServerIP()
			files = ['BARCODES.dbf', 'LIQCODE.DBF', 'LIQCODE.DBT']
			conn = SMBConnection(self.user, self.password, self.client_machine_name, self.server_name, self.server_ip)
			with dbfLock:
				conn.connect(self.server_ip)
				for file in files:
					f = open(file, 'w')
					conn.retrieveFile("LPOSDATA", "/"+file, f)	
					f.close()
				conn.close()			
			return(True)
		except:
			return(False)	


class Barcode:
	
	def __init__(self, bar, liq):
		self.eng_string = 'sqlite:///barcodes.db'
		self.liq = Dbf5(liq, codec='latin-1')
		self.bar = Dbf5(bar, codec='latin-1')
		self.liq.mem(chunksize=1000)
		self.bar.mem(chunksize=1000)
		self.eng = None
		self.conn = None
		#self.barcodes = self.db['BARCODES']
		#self.liqcode = self.db['LIQCODE']
		self.tables = {'BARCODES' : self.bar, 'LIQCODE' : self.liq}

	def getTable(self, tab):
		meta = MetaData(self.eng, reflect=True)
		return Table(tab, meta, autoload=True)

	def connect(self):
		self.conn = self.eng.connect()
	
	def createDb(self):
		t0 = None
		t1 = None
		self.eng = create_engine(self.eng_string)
		if not database_exists(self.eng_string):
			print "DB Does Not Exist"
			create_database(self.eng_string)
			self.connect()
			t0 = time.time()
			for tab in self.tables.keys():
				self.tables[tab].to_pandassql(self.eng_string, table=tab, if_exists='replace')
			t1 = time.time()
			self.conn.close()
		else:
			print "DB Exists"
			self.connect()
			t2 = time.time()
			for tab in self.tables.keys():
				print(self.tables[tab])
				self.tables[tab].to_pandassql(self.eng_string, table='temp'+tab, if_exists='replace')
				t0 = time.time()
				res =self.conn.execute("INSERT OR IGNORE INTO "+tab+" SELECT * FROM temp"+tab)
				t1 = time.time()
			t3 = time.time()
			print(t3-t2)
			self.conn.close() 
		print(t1-t0)







b = Barcode('BARCODES.dbf', 'LIQCODE.dbf')
b.createDb()
for d in b.getTable('Barcodes').c:
	print d.name

















