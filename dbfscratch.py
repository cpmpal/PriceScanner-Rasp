#!/usr/bin/python
from simpledbf import Dbf5
from sqlalchemy import create_engine
from sqlalchemy import Table
from sqlalchemy import select
from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

dbf = Dbf5('LIQCODE.dbf', codec='latin-1')
dbf.mem(chunksize=1000)

dbf = dbf.to_pandassql('sqlite:///barcodes.db', if_exists='replace')

dbf2 = Dbf5('BARCODES.dbf', codec='latin-1')
dbf2.mem(chunksize=1000)

dbf2 = dbf2.to_pandassql('sqlite:///barcodes.db', if_exists='replace')

eng = create_engine('sqlite:///barcodes.db')
conn = eng.connect()

meta = MetaData(eng, reflect=True)
liqcode = Table('LIQCODE', meta, autoload=True)
barcode = Table('BARCODES', meta, autoload=True)

select_st = select([liqcode.c.CODE_NUM, liqcode.c.BARCODE, liqcode.c.BARCODE2, liqcode.c.BRAND, liqcode.c.DESCRIP, liqcode.c.TYPE, liqcode.c.SIZE, liqcode.c.PRICE, liqcode.c.STD_QTY, liqcode.c.DEPOSIT]).where(liqcode.c.CODE_NUM == '9237')
res = conn.execute(select_st)

for row in res: print(row)


'''
for c in liqcode.columns:
	print c.name 

for c in barcode.columns:
	print c.name
'''

'''
select_st = select([table]).where(table.c.CODE_NUM == '9237')
res = conn.execute(select_st)
for _row in res: print(_row)

print(Base._decl_class_registry.values())

for c in Base._decl_class_registry.values():
	if hasattr(c, '__tablename__') and c.__tablename__ == 'LIQCODE':
		print c

'''
