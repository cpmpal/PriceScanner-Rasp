#!/usr/bin/python

from nmb.NetBIOS import NetBIOS
from smb.SMBConnection import SMBConnection

class samb:
	server_ip = None
	server_name = 'DOWTOWNSERVER1'

	def getServerIP(self):
		q = NetBIOS()
		self.server_ip = q.queryName(self.server_name)[0]
		q.close()

	def getFile(self):
		try:
			user = ''
			password = ''
			client_machine_name = 'raspScanner'
			self.getServerIP()
			files = ['BARCODES.dbf', 'LIQCODE.dbf', 'LIQCODE.dbt'] 

			conn = SMBConnection(user, password, client_machine_name, self.server_name, self.server_ip)
			conn.connect(self.server_ip)
			print('connected')
			for file in files:
				f = open(file, 'w')
				conn.retrieveFile("LPOSDATA", "/"+file, f)
				f.close()
			print('files retrieved')
			conn.close()
			return(True)
		except:
			return(False)

	def getFiles(self):
		try:
			self.server_ip = getServerIP()
			print(self.server_ip)
			self.getFile()
			print('test')
			return(True)
		except:
			return(False)

if __name__ == '__main__':
	server_ip = getServerIP()
	print(server_ip)
	getFile()


