from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp import workflow,netsvc



class wizard_sgeede_stock_request(osv.osv_memory):
	_name = 'wizard.sgeede.stock.request'
	_description = 'Stock Request'

	_columns = {
		'name': fields.char('Description'),
		
	}   
	_defaults = {
		# 'date_start': lambda *a: time.strftime('%Y-%m-%d'),
		# 'date_end': lambda *a: time.strftime('%Y-%m-%d'),
	}
	def _prepare_internal_transfer_accumulation(self, cr, uid, warehouse, context=None):
		date_now= datetime.today().strftime('%Y-%m-%d %H:%M:%S')
		return {
			'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.internal.transfer'),
			'date': date_now,
			'source_warehouse_id': warehouse.default_resupply_wh_id.id,
			'dest_warehouse_id': warehouse.id,
			'state':'draft',
			}
	def _prepare_internal_transfer(self, cr, uid, orderpoint, context=None):
		date_now= datetime.today().strftime('%Y-%m-%d %H:%M:%S')
		return {
			'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.internal.transfer'),
			'date': date_now,
			'source_warehouse_id': orderpoint.warehouse_id.default_resupply_wh_id.id,
			'dest_warehouse_id': orderpoint.warehouse_id.id,
			'state':'draft',
			
		}
	def _prepare_internal_transfer_line(self, cr, uid, orderpoint, product_qty,transfer_id, context=None):
		product = self.pool.get('product.product').browse(cr, uid, orderpoint.product_id.id, context=context)

		product_uom_id = product.uom_id and product.uom_id.id or False
		return {
			'product_id': orderpoint.product_id.id,
			'product_qty': product_qty,
			'product_uom_id': product_uom_id,
			'transfer_id':transfer_id,
			'state':'draft',
			
		}
	def _prepare_internal_transfer_line_accumulation(self, cr, uid, product_id, product_qty,transfer_id, context=None):
		product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)

		product_uom_id = product.uom_id and product.uom_id.id or False
		return {
			'product_id': product_id,
			'product_qty': product_qty,
			'product_uom_id': product_uom_id,
			'transfer_id':transfer_id,
			'state':'draft',
			
		}
	def _product_virtual_get(self, cr, uid, order_point):
		product_obj = self.pool.get('product.product')
		return product_obj._product_available(cr, uid,
				[order_point.product_id.id],
				context={'location': order_point.location_id.id})[order_point.product_id.id]['virtual_available']

	def _product_qty_get(self, cr, uid, order_point):
		product_obj = self.pool.get('product.product')
		return product_obj._product_available(cr, uid,
				[order_point.product_id.id],
				context={'location': order_point.location_id.id})[order_point.product_id.id]['qty_available']
	
	def _make_po(self, cr, uid, product_ids,partner_id, context=None):
		""" Resolve the purchase from procurement, which may result in a new PO creation, a new PO line creation or a quantity change on existing PO line.
		Note that some operations (as the PO creation) are made as SUPERUSER because the current user may not have rights to do it (mto product launched by a sale for example)

		@return: dictionary giving for each procurement its related resolving PO line.
		"""
		res = {}
		company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
		po_obj = self.pool.get('purchase.order')
		po_line_obj = self.pool.get('purchase.order.line')
		seq_obj = self.pool.get('ir.sequence')
		# select distinct ps.name from product_supplierinfo ps inner join product_product pp on pp.product_tmpl_id = ps.product_tmpl_id where pp.id = 416;
		return True

	def _action_confirm(self, cr, uid, internal_id, context):
		type_obj = self.pool.get('stock.picking.type')
		picking_obj = self.pool.get('stock.picking')
		company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
		company = self.pool.get('res.company').browse(cr, uid, company_id)
		transfer = self.pool.get('stock.internal.transfer').browse(cr, uid, internal_id)
		source_location_id = transfer.source_warehouse_id.lot_stock_id.id
		dest_location_id = company.transit_location_id.id
		if transfer.state == 'draft':
			backorders = []
			user_list = []
			user_ids = transfer.source_warehouse_id.user_ids
			if user_ids == False:
				raise osv.except_osv(_('Warning !'),_('You are not authorized to send or receive products !'))
			if user_ids :
				for user in user_ids :
					user_list.append(user.id)
				if uid not in user_list:
					raise osv.except_osv(_('Warning !'),_('You are not authorized to send or receive products !'))

				type_ids = type_obj.search(cr, uid, [('default_location_src_id', '=', transfer.source_warehouse_id.lot_stock_id.id),
					('code', '=', 'outgoing')])

				if type_ids:
					types = type_obj.browse(cr, uid, type_ids[0])					
					picking_id = picking_obj.create(cr, uid, {
						'picking_type_id' : types.id,
						'transfer_id' : internal_id,
						'origin':transfer.name,
					})
				else:
					raise osv.except_osv(_('Error!'), _('Unable to find source location in Stock Picking.'))

				move_obj = self.pool.get('stock.move')
				for line in transfer.line_ids:
					move_obj.create(cr,uid,{
						'name' : 'Stock Internal Transfer',
						'product_id' : line.product_id.id,
						'product_uom' : line.product_uom_id.id,
						'product_uom_qty' : line.product_qty,
						'location_id' : source_location_id,
						'location_dest_id' : dest_location_id,
						'picking_id' : picking_id,
					})
				picking_obj = self.pool.get('stock.picking')
				picking_obj.action_confirm(cr, uid, picking_id)
				# picking_obj.force_assign(cr, uid, picking_id)
				#picking_obj.action_assign(cr, uid, picking_id)
				

				wkf_service = netsvc.LocalService('workflow')
				wkf_service.trg_validate(uid, 'stock.internal.transfer', internal_id, 'action_send', cr)
				
			
		return True

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
		current_date = time.strftime('%Y-%m-%d %H:%M:%S')		
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
		
		# warehouse_ids = warehouse_obj.search(cr,uid,[('default_resupply_wh_id','!=',False)])
		warehouse_ids = warehouse_obj.search(cr,uid,[])
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
				interval = warehouse_id.interval_number
				date_before = datetime.today() + timedelta(days = -interval)
				date_before = date_before.strftime('%Y-%m-%d %H:%M:%S')
				date_start = datetime.strptime(date_before,'%Y-%m-%d %H:%M:%S')
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
				params = ( str(date_start),str(date_end),stock_location)
				query_product_ids = "( SELECT sm.product_id FROM stock_move sm INNER JOIN stock_picking sp ON sm.picking_id = sp.id "\
				 					"INNER JOIN pos_order po on sp.id = po.picking_id inner join pos_session ps on "\
				 					"po.session_id = ps.id inner join pos_config pc on ps.config_id = pc.id "\
				 					"where po.date_order between"
				query_product_ids2= "group by sm.product_id)"			 						

				if warehouse_id.request_method == 'purchase_order':
					cr.execute("SELECT distinct ps.name from product_supplierinfo ps "\
						"inner join product_product pp on pp.product_tmpl_id = ps.product_tmpl_id "\
						" where pp.id IN "+query_product_ids+" %s and %s and pc.stock_location_id = %s "+ query_product_ids2+ "", params)
					partner_ids = cr.fetchall()
					print partner_ids,'partner_idssss'
					# cari product berdasarkan partnerrrrrrrr
					# Group by partner >> dapat partner , ambil min_qty dari product product_supplierinfo
					
					self._make_po(cr,uid,product_ids,partner_id)
					
					return True

				for product_id,qty in results:
					internal_transfer_line_obj.create(cr, uid,
										self._prepare_internal_transfer_line_accumulation(cr, uid, product_id, qty,internal_id, context=context),
										context=context)

		return True







# ================================================
# New feature can request from minimum qty or accumulation sale
# Hi David,

# meanwhile we use your module in both of our stores and our warehouse and it works really good. :)

# We have a new customization request and I'd be happy to receive your offer. :) 

# I want to add orderpoints (OP) to the two store's "warehouses" for some products that we always want to have in our stores that create a SIT from the main warehouse to refill.

# Example:
# - Store has an OP "testproduct minimum quantity = 1"
# - 1 "testproduct" is sold, so quantity in stock "store" = 0
# - User hits a button (or via cron job?) and a SIT is created that requests 1 Testproduct from the main warehouse.

# Each warehouse's configuration needs a field where we can define wether it should be refilled from a main warehouse and from which one.

# The store's warehouses will be only filled from the main warehouse and need not create purchase orders.

# The OP's that we defined for the main warehouse are always executed in the "regular Odoo behaviour" (-> they create purchase orders)

# Hope you can roughly understand what we need and I'm looking forward to receive your offer. :)

# Warm regards

# Sebastian
