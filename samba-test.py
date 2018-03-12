#!/usr/bin/python

from nmb.NetBIOS import NetBIOS
from smb.SMBConnection import SMBConnection
from pprint import pprint

f = open('TimeSplit.xlsx', 'w')

user = 'cpmpa'
passw = 'smoGG33y'
client_machine_name = 'kronotop'

server_name = 'DESKTOP-61IG81O'
server_ip = '192.168.1.25'

domain_name = ''

conn = SMBConnection(user, passw, client_machine_name, server_name, server_ip)

conn.connect(server_ip)

shares = conn.listShares()
for share in shares:
	if not share.isSpecial and share.name not in ['NETLOGON', 'SYSVOL', 'HP Deskjet 6940 series']:
		sharedfiles = conn.listPath(share.name, '/')
		for sharedfile in sharedfiles:
			print(type(sharedfile))
			print(sharedfile.filename)

conn.retrieveFile('Random', '/TimeSplit.xlsx', f)


conn.close()
