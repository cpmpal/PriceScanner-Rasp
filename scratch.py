#!/usr/bin/python

import dataset
from dbfread import DBF

db = dataset.connect('sqlite:///:memory')
table = db['BARCODES']
print('table made')
b =  DBF('LIQCODE.dbf', load=True, encoding='latin-1')
print('dbf read')
table.insert_many(b.records, chunk_size=5000)
print('table updated')
print(table.find_one(CODE_NUM='2464'))
