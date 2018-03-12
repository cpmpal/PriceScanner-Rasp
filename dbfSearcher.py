#!/usr/bin/python
from dbfread import DBF
'''

	BARCODES
	0 - Code Number
	1 - Barcode
	2 - Qty
	3 - Price
	4 - P_price
	5 - Start Prom
	6 - End Prom
	7 - Flat Tax
	8 - Price B
	...
	16 - Price J


	LIQCODES
	0 - Code Number
	1 - Barcode
	2 - Barcode 2
	3 - Brand
	4 - Description
	5 - Type
	6 - Size
	7 - Cost
	8 - Last Cost
	9 - Next Cost
	10 - Cost_2
	11 - Cost_3
	12 - Price
	37 - Taxable
	53 - Deposit
	54 - Deposit Amount
	45 - Case Price
	46 - Standard Quantity


'''

class Product:
	def __init__(self, barcode, barcodes, liqcode):
		self.price = None
		self.qty = None
		self.brand = ''
		self.desc = ''
		self.barcode = barcode.upper()
		self.codeNum = ''
		self.singlePrice = None
		self.casePrice = None
		self.barcodes = DBF(barcodes, encoding='latin-1')
		self.liqcode = DBF(liqcode, encoding='latin-1')
		self.deposit =  None
		self.dep = False
		self.found = False

	def priceFound(self):
		return self.price is None
	
	def getCodeNum(self):
		for b in self.barcodes:
			if b.items()[1][1] == self.barcode:
				self.codeNum = b.items()[0][1]
				self.qty = b.items()[2][1]
				self.price = b.items()[3][1]
				self.barcode = b.items()[1][1]
				self.found = True
			if b.items()[0][1] == self.codeNum and b.items()[1][1].startswith('S'):
				self.singlePrice = b.items()[3][1]
			if b.items()[0][1] == self.codeNum and b.items()[1][1].startswith('C'):
				self.casePrice = b.items()[3][1]
				return

	def getName(self):
		for l in self.liqcode:
			if l.items()[0][1] == self.codeNum:
				self.found = True
				self.brand = l.items()[3][1]
				self.desc = l.items()[4][1]
				if self.qty is None:
					self.qty = l.items()[58][1]
				if self.price is None:
					self.price = l.items()[12][1]
					self.dep = True if l.items()[53][1] == u'Y' else False
				if self.dep:
					self.deposit = self.qty * 0.05

	def getProduct(self):
		ScannerGUI.meterPercent = 5
		self.getCodeNum()
		ScannerGUI.meterPercent = 50
		self.getName()
		ScannerGui.meterPercent = 100
		
	def __str__(selfi):
		if not self.found:
			return "Product Not Found :("
		s = ''
		s+='Brand: '+self.brand+'\n'
		s+='Description: '+self.desc+'\n'
		if self.price is not None:
			s+='Price: %.2f' % self.price+'\n'
		else:
			s+='Price: N/A\n'
		s+='QTY: %i' % self.qty+'\n'
		s+='Barcode: '+self.barcode+'\n'
		if self.singlePrice is not None:
			s+='Single Price: %.2f' % self.singlePrice+'\n'
		else:
			s+='Single Price: N/A\n'
		if self.casePrice is not None:
			s+='Case Price: %.2f' % self.casePrice+'\n'
		else:
			s+='Case Price: N/A\n' 
		if self.dep:
			s+='Deposit: %.2f' % self.deposit+'\n'
		else:
			s+='Deposit: N/A\n'

		return s


def main():

	bar = raw_input('enter barcode:\n')

	prod = Product(bar, 'BARCODES.dbf', 'LIQCODE.dbf')
	prod.getCodeNum()
	prod.getName()
	print prod

if __name__ == "__main__":
	main()
