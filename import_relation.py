voucher_rel_query = "SELECT * FROM rel_extended_voucher_line WHERE voucher_id = %s" % (voucher_id)
							cr_db.execute(voucher_rel_query)
							cr_voucher_rel_fetch = cr_db.fetchall()

							cr.execute(""" SELECT id FROM account_extended_voucher ORDER BY id DESC LIMIT 1 """)
							last_id = cr.fetchall()

							if cr_voucher_rel_fetch:
								for voucher_rel in cr_voucher_rel_fetch:
									voucher_id = "'%s_sgeede_voucher_%s'" % (imports.database, voucher_rel['voucher_id'])
									model_voucher_query = "SELECT res_id FROM ir_model_data WHERE name=%s" % (voucher_id)
									cr.execute(model_voucher_query)
									voucher_id = cr.fetchall()

									if voucher_id:
										voucher_rel['voucher_id'] = voucher_id[0][0]

									move_line_id = "'%s_sgeede_move_line_%s'" % (imports.database, voucher_rel['line_id'])
									model_move_line_query = "SELECT imd.res_id FROM ir_model_data imd INNER JOIN account_move_line aml ON aml.id = imd.res_id WHERE imd.name=%s" % (move_line_id)
									cr.execute(model_move_line_query)
									move_line_id = cr.fetchall()

									if move_line_id:
										voucher_rel['line_id'] = move_line_id[0][0]
									else:
										move_line_id = "'%s_sgeede_move_line_%s'" % (imports.database, voucher_rel['line_id'])
										cr.execute(""" DELETE FROM ir_model_data WHERE name=%s """ % (move_line_id))
										continue

									voucher_rel_tuple = tuple(voucher_rel)
									voucher_rel_dumps = json.dumps(voucher_rel_tuple)
									voucher_rel_strip_query = voucher_rel_dumps.strip('[]')
									voucher_rel_quote_query = voucher_rel_strip_query.replace('"', '\'')

									insert_voucher_rel = " INSERT INTO rel_extended_voucher_line VALUES (%s) " % (voucher_rel_quote_query)
									cr.execute(insert_voucher_rel)