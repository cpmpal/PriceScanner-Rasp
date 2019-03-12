# PriceScanner-Rasp

## What is it
Python based GUI scanner for LiquorPOS designed to run on a raspberry pi with both a touchscreen and standard barcode scanner in liquor stores

## Why
LiqourPOS owned by HeartlandPOS is an older point of sale system. It doesn't have afforded to it the modern conviences of Square, Toast, and other mobile point of sale systems. Among this it doesn't have support to have external devices access or read the database it's built on so nothing can actually view the prices without being a full fledged Windows XP machine; however, as LiquorPOS is an older system it also uses a standardized DBase file format, .dbf, which is plainly accessible and readable. The goal of this project is to make a simple gui that would enable a customer to scan a product barcode and see price details without having to do anything complicated, and more importantly without store management having to do anything complicated. By copying the BARCODES.dbf and LIQCODES.dbf we have access to all that data and need to cleanly optimize reading so the raspberry pi can handle that load

### Overall Design
We have three main functions of the PriceScanner:
1. Create a visual interface to input barcode and see price
2. Pull a copy of the product data from the server regularly so it stays up to date with new product
3. Read, in less than 1 second, product information so user can quickly make decisions and find product useful

The first and second objectives might seem hard but they are trivial incomparison to the third. For the first we use appJar as an off the shelf python gui library. We make sure that it provides messages but just very simply provides at least a text field to enter a barcode and a text field to display product data.

For the second we use a samba library from pysmb to grab the files. In our stores configuration, the dbf files are located in a folder off the main C: drive and have read/write access for everyone. (This is how the database is shared across the various computers using the software in the store.) All we need is to download the file to the pi at a daily interval when the files are not being worked on i.e. the store is closed.

For the third objective, we need a DBMS. I tried experimentally to see if the pi could handle sequential reading of the dbf files, and it takes on the order of tens of seconds to minutes on the pi. With a dbms of some kind we drastically reduce read and write times, but pimarily read times. This makes it possible to use for a customer who is looking not only to see a product but compare two fairly quickly.

### Files

#### ScannerGUI.py

This file is reponsible for both creating the GUI using appJar and the threading for: reading a product, getting new copies of the file, importing new changes, and making any necessary changes to the database. This is done through appJar's thread method which is essentially a wrapper to spin off threads.

 * fileWorker() downloads the latest copy of the product files off the server, after getting a lock for the files
 * updateDB() reads those new product files and checks to see if there were entries added (The size of the new one is larger than the old one) 
