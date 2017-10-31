# NEW ADD FOR VIEW REPORT pending due error with id passing
					# Get stock_history from other database					
					# cr_db = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
					# cr_db_query = "SELECT id,move_id,location_id,company_id,product_id,product_categ_id,quantity,date,price_unit_on_quant,source FROM stock_history WHERE date BETWEEN %s and %s ORDER BY date ASC" % (from_date, to_date)
					# cr_db.execute(cr_db_query)
					# cr_stock_history_fetch = cr_db.fetchall()	
					# if cr_stock_history_fetch:
					# 	create_stock_history = 0
					# 	for stock_history in cr_stock_history_fetch:
					# 		stock_history_id = "'%s_sgeede_stock_history_%s'" % (imports.database, str(stock_history['id']))
					# 		model_stock_history_query = "SELECT res_id FROM ir_model_data WHERE name=%s" % (stock_history_id)
					# 		cr.execute(model_stock_history_query)
					# 		stock_history_id = cr.fetchall()
					# 		print stock_history['id'],'stock_history'

					# 		if stock_history_id:
					# 			continue

					# 		create_stock_history += 1
					# 		print "create_stock_history"
					# 		product_id = "'%s_sgeede_product_product_%s'" % (imports.database, stock_history['product_id'])
					# 		model_product_query = "SELECT res_id FROM ir_model_data2 WHERE name=%s" % (product_id)
					# 		cr.execute(model_product_query)
					# 		product_id = cr.fetchall()

					# 		if product_id:
					# 			stock_history['product_id'] = product_id[0][0]
								
					# 		else:
					# 			product_id = "'%s_sgeede_product_product_%s'" % (imports.database, stock_history['product_id'])
					# 			model_product_query = "SELECT res_id FROM ir_model_data WHERE name=%s" % (product_id)
					# 			cr.execute(model_product_query)
					# 			product_id = cr.fetchall()

					# 			if product_id:
					# 				stock_history['product_id'] = product_id[0][0]

					# 			else:
					# 				product_id = "'sgeede_product_product_%s'" % (stock_history['product_id'])
					# 				model_product_query = "SELECT res_id FROM ir_model_data WHERE name=%s" % (product_id)
					# 				cr.execute(model_product_query)
					# 				product_id = cr.fetchall()

					# 				if product_id:
					# 					stock_history['product_id'] = product_id[0][0]
					# 		#FIND location_id
					# 		location_id = "'%s_sgeede_stock_location_%s'" % (imports.database, stock_history['location_id'])
					# 		model_lot_stock_query = "SELECT res_id FROM ir_model_data2 WHERE name=%s" % (location_id)
					# 		cr.execute(model_lot_stock_query)
					# 		location_id = cr.fetchall()

					# 		if location_id:
					# 			stock_history['location_id'] = location_id[0][0]
					# 		else:
					# 			location_id = "'%s_sgeede_stock_location_%s'" % (imports.database, stock_history['location_id'])
					# 			model_partner_query = "SELECT res_id FROM ir_model_data WHERE name=%s" % (location_id)
					# 			cr.execute(model_partner_query)
					# 			location_id = cr.fetchall()

					# 			if location_id:
					# 				stock_history['location_id'] = location_id[0][0]	
					# 			else:
					# 				location_id = "'sgeede_stock_location_%s'" % (stock_history['location_id'])
					# 				model_partner_query = "SELECT res_id FROM ir_model_data WHERE name=%s" % (location_id)
					# 				cr.execute(model_partner_query)
					# 				location_id = cr.fetchall()

					# 				if location_id:
					# 					stock_history['location_id'] = location_id[0][0]
					# 				else:
					# 					stock_history['location_id'] = None

					# 		#FIND TRUE PRODUCT CATEGORY
					# 		product_categ_id = "'%s_sgeede_product_category_%s'" % (imports.database, stock_history['product_categ_id'])
					# 		model_category_query = "SELECT res_id FROM ir_model_data2 WHERE name=%s" % (product_categ_id)
					# 		cr.execute(model_category_query)
					# 		product_categ_id = cr.fetchall()
					# 		if stock_history['product_categ_id'] and product_categ_id:
					# 			stock_history['product_categ_id'] = product_categ_id[0][0]
					# 		else:
					# 			product_categ_id = "'%s_sgeede_product_category_%s'" % (imports.database, stock_history['product_categ_id'])
					# 			model_category_query = "SELECT res_id FROM ir_model_data WHERE name=%s" % (product_categ_id)
					# 			cr.execute(model_category_query)
					# 			product_categ_id = cr.fetchall()
					# 			if product_categ_id:
					# 				stock_history['product_categ_id'] = product_categ_id[0][0]
					# 			else:
					# 				product_categ_id = "'sgeede_product_category_%s'" % (stock_history['product_categ_id'])
					# 				model_category_query = "SELECT res_id FROM ir_model_data WHERE name=%s" % (product_categ_id)
					# 				cr.execute(model_category_query)
					# 				product_categ_id = cr.fetchall()
					# 				if product_categ_id:
					# 					stock_history['product_categ_id'] = product_categ_id[0][0]
					# 				else:
					# 					stock_history['product_categ_id'] = None

					# 		#FIND STOCK MOVE
					# 		move_id = "'%s_sgeede_stock_move_%s'" % (imports.database, stock_history['move_id'])
					# 		model_move_query = "SELECT res_id FROM ir_model_data WHERE name=%s" % (move_id)
					# 		cr.execute(model_move_query)
					# 		move_id = cr.fetchall()

					# 		if move_id:
					# 			stock_history['move_id'] = move_id[0][0]
					# 		else:
					# 			stock_history['move_id'] = None	

					# 		stock_history_id = stock_history['id']
					# 		del stock_history[0]

					# 		stock_history_tuple = tuple(stock_history)
					# 		stock_history_dumps = json.dumps(stock_history_tuple)
					# 		stock_history_strip_query = stock_history_dumps.strip('[]')
					# 		stock_history_quote_query = stock_history_strip_query.replace('"', '\'')
					# 		#move_id << update
					# 		#location_id
					# 		#product_id << done
					# 		#product_categ_id
					# 		cr.execute(""" WITH rows AS 
					# 			(INSERT INTO stock_history (move_id,location_id,company_id,product_id,
					# 			product_categ_id,quantity,date,price_unit_on_quant,source) 
					# 			VALUES (%s) RETURNING id)
					# 			INSERT INTO ir_model_data (noupdate, name, module, model, res_id) VALUES 
					# 			(True, '%s_sgeede_stock_history_%s', 'isana_tax', 'stock.history', (SELECT id FROM rows)) """ 
					# 			% (stock_history_quote_query, imports.database, str(stock_history_id)))
