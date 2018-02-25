# Small script to show PostgreSQL and Pyscopg together
#

import psycopg2

try:
	# conn = psycopg2.connect("dbname='ISANA_DEMO_MINI' user='admin' host='localhost' password='admin'")
	# conn = psycopg2.connect("dbname='template1' user='dbuser' host='localhost' password='dbpass'")
	db = psycopg2.connect("dbname='ISANA_DEMO_MINI'")
	# cr2 = openerp.sql_db.db_connect(partner.database).cursor()
	cur = db.cursor()
	try:
		cur.execute("""SELECT name from res_partner""")
		rows = cur.fetchall()
		print "\nShow me the databases:\n"
		for row in rows:
			print "   ", row[0]
		# cur.execute("""DROP DATABASE foo_test""")
	except:
		print "I can't drop our test database!"
except:
	print "I am unable to connect to the database"

