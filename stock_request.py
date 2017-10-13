def button_generate(self, cr, uid, ids, context=None):
		"""
		 To get the date and print the report
		 @param self: The object pointer.
		 @param cr: A database cursor
		 @param uid: ID of the user currently logged in
		 @param context: A standard dictionary
		 @return : retrun report
		"""
		date_now 	= datetime.today().strftime('%Y-%m-%d %H:%M:%S')
		date_before = datetime.today() + timedelta(days = -1)
		date_before = date_before.strftime('%Y-%m-%d %H:%M:%S')
		current_date = time.strftime('%Y-%m-%d %H:%M:%S')
		date_start = datetime.strptime(date_before,'%Y-%m-%d %H:%M:%S')
		date_end = datetime.strptime(date_now,'%Y-%m-%d %H:%M:%S')

		if context is None:
			context = {}
		orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
		internal_transfer_obj = self.pool.get('stock.internal.transfer')
		internal_transfer_line_obj = self.pool.get('stock.internal.transfer.line')
		user_obj = self.pool.get('res.users')
		warehouse_obj = self.pool.get('stock.warehouse')
		company_id = user_obj.browse(cr, uid, uid, context=context).company_id.id
		dom = company_id and [('company_id', '=', company_id)] or []
		# orderpoint_ids = orderpoint_obj.search(cr, uid, dom)
		
		warehouse_ids = warehouse_obj.search(cr,uid,[('default_resupply_wh_id','!=',False)])
		for warehouse_id in warehouse_obj.browse(cr,uid,warehouse_ids):
			if warehouse_id.request_type == 'minimum_qty':
				# print 'minimum_qty'
				orderpoint_ids = orderpoint_obj.search(cr, uid, [('warehouse_id','=',warehouse_id.id)])

				if orderpoint_ids:
					order_points = orderpoint_obj.browse(cr,uid,orderpoint_ids[0],context=context)
					if not order_points.warehouse_id.default_resupply_wh_id:
						continue
					internal_id = internal_transfer_obj.create(cr, uid,
										self._prepare_internal_transfer(cr, uid, order_points, context=context),
										context=context)
					for op in orderpoint_obj.browse(cr, uid, orderpoint_ids, context=context):
						qty = 0
						# prods = self._product_virtual_get(cr, uid, op)
						prods = self._product_qty_get(cr, uid, op)
						if prods is None:
							continue

						if not op.warehouse_id.default_resupply_wh_id:
							continue
						if prods < op.product_min_qty:
							qty = max(op.product_min_qty, op.product_max_qty) - prods
							if qty <= 0:
								continue
							if qty > 0:
								internal_line_id = internal_transfer_line_obj.create(cr, uid,
										self._prepare_internal_transfer_line(cr, uid, op, qty,internal_id, context=context),
										context=context)
				# if internal_id:
					# self._action_confirm(cr, uid, internal_id, context=context) #FOR CONFIRM
			else:
				# print 'accumulation'
				stock_location = warehouse_id.lot_stock_id.id #for location Store by warehouse
				internal_id = internal_transfer_obj.create(cr, uid,
										self._prepare_internal_transfer_accumulation(cr, uid, warehouse_id, context=context),
										context=context)
				cr.execute("""SELECT sm.product_id,sum(sm.product_uom_qty) AS 
				 qty FROM stock_move sm INNER JOIN stock_picking sp ON sm.picking_id = sp.id 
				 INNER JOIN pos_order po on sp.id = po.picking_id inner join pos_session ps on 
				 po.session_id = ps.id inner join pos_config pc on ps.config_id = pc.id 
				 where po.date_order between %s and %s  and pc.stock_location_id = %s 
				 group by sm.product_id""",( str(date_start),str(date_end),stock_location))
				 #				
				results = cr.fetchall()
				for product_id,qty in results:
					internal_transfer_line_obj.create(cr, uid,
										self._prepare_internal_transfer_line_accumulation(cr, uid, product_id, qty,internal_id, context=context),
										context=context)

		return True