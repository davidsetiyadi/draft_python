from datetime import date, datetime
from dateutil import relativedelta
import json
import time
from _common import ceiling

from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
from openerp.tools.float_utils import float_round, float_compare
from openerp.osv.orm import browse_record_list, browse_record, browse_null

import logging


_logger = logging.getLogger(__name__)
#--------------------------------------
class stock_quant(osv.osv):
	"""
	Quants are the smallest unit of stock physical instances
	"""
	_inherit = "stock.quant"

	_columns = {
		'use_date': fields.related('lot_id', 'use_date', type='date',string='Expired Date'),
	}

class stock_picking(osv.osv):
	_inherit = "stock.picking"
	_columns = {
		'is_return':fields.char('Return'),
		'purchase_id':fields.many2one('purchase.order','Purchase Order'),
		'lane'		:fields.char('Lane'),
	}
	_defaults = {
		'is_return' : False,
	}
	@api.cr_uid_ids_context
	def open_barcode_interface(self, cr, uid, picking_ids, context=None):
		final_url="/barcode/web/#action=stock.ui&picking_id="+str(picking_ids[0])
		return {'type': 'ir.actions.act_url', 'url':final_url, 'target': 'new',}

	@api.multi
	def button_print(self):
		""" Print the invoice and mark it as sent, so that we can see more
			easily the next step of the workflow
		"""
		assert len(self) == 1, 'This option should only be used for a single id at a time.'
		self.sent = True
		return self.env['report'].get_action(self, 'isana_custom.report_return_purchase')

	@api.multi
	def button_print_return(self):
		""" Print the invoice and mark it as sent, so that we can see more
			easily the next step of the workflow
		"""
		assert len(self) == 1, 'This option should only be used for a single id at a time.'
		self.sent = True
		return self.env['report'].get_action(self, 'isana_custom.report_return_sale')

	def button_product_label(self, cr, uid, ids, context={}):
		product_id = []
		
		for picking in self.browse(cr, uid, ids, context=context):
			for move in picking.move_lines:
				product_id.append(move.product_id.id)
		datas = {'ids':product_id }
		res = self.read(cr, uid, ids, [], context=context)
		res = res and res[0] or {}
		datas['form'] = res
		
		return {
			'type': 'ir.actions.report.xml',
			'report_name': 'sgeede.product.label.report',
			'datas': datas,
			'context': context,
		}
	def button_update_price(self, cr, uid, ids, context={}):
		product_id = []
		update_price_obj = self.pool.get('isana.update.price.wizard')
		update_price_line_obj = self.pool.get('isana.update.price.line.wizard')
		update_id = update_price_obj.create(cr,uid,{})
		for picking in self.browse(cr, uid, ids, context=context):
			for move in picking.move_lines:
				product_id.append(move.product_id.id)
		# return True
				update_price_line_obj.create(cr,uid,{
					'product_id': move.product_id.id,
					'list_price': move.product_id.lst_price,
					'suggested_price': move.product_id.suggested_price,
					'standard_price': move.product_id.standard_price,
					'profit_percentage': move.product_id.categ_id.profit_percentage,
					'profit_amount': move.product_id.categ_id.profit_amount,
					'update_price_id':update_id,
					})
		return {
			'name'          : 'Suggest Update Price',
			'view_type'     : 'form',
			'view_mode'     : 'form',
			'view_id'		:  False,
			'res_model'     : 'isana.update.price.wizard',
			'type'          : 'ir.actions.act_window',
			'res_id' 		: update_id,
			'target'		: 'new',
			'context'       : context,                  
				}

	
	def button_not_include(self, cr, uid, ids, context={}):
		product_id = []
		product_obj = self.pool.get('product.product')
		move_obj = self.pool.get('stock.move')
		cr.execute("""SELECT pp.id from product_product pp 
			inner join stock_move sm on sm.product_id = pp.id 
			inner join stock_picking sp on sp.id = sm.picking_id 
			WHERE picking_id = %s group by pp.id""",(ids))
		query_product_id = cr.fetchall()
		if query_product_id:
			product_id += [product[0] for product in query_product_id]
		if len(product_id) == 0 :
			product_ids = product_obj.search(cr,uid, [])
		elif len(product_id) == 1 :
			product_ids = product_obj.search(cr,uid, [('id','!=',product_id),])
		else:
			product_ids = product_obj.search(cr,uid, [('id','not in',product_id),])
		context = {'tree_view_ref': 'product.product_product_tree_view'}
		domain = [('id', 'in', product_ids)]
		return {
			'name': _('Not Include Inventory Loss'),
			'domain': domain,
			'res_model': 'product.product',
			'type': 'ir.actions.act_window',
			'context': context,
			'view_id': False,
			'view_mode': 'tree',
			'view_type': 'form',
			# 'limit': 20
		}


	def _prepare_pack_ops(self, cr, uid, picking, quants, forced_qties, context=None):
			""" returns a list of dict, ready to be used in create() of stock.pack.operation.

			:param picking: browse record (stock.picking)
			:param quants: browse record list (stock.quant). List of quants associated to the picking
			:param forced_qties: dictionary showing for each product (keys) its corresponding quantity (value) that is not covered by the quants associated to the picking
			"""
			def _picking_putaway_apply(product):
				location = False
				# Search putaway strategy
				if product_putaway_strats.get(product.id):
					location = product_putaway_strats[product.id]
				else:
					location = self.pool.get('stock.location').get_putaway_strategy(cr, uid, picking.location_dest_id, product, context=context)
					product_putaway_strats[product.id] = location
				return location or picking.location_dest_id.id

			pack_obj = self.pool.get("stock.quant.package")
			quant_obj = self.pool.get("stock.quant")
			picking_obj = self.pool.get("")
			vals = []
			qtys_grouped = {}
			#for each quant of the picking, find the suggested location
			quants_suggested_locations = {}
			product_putaway_strats = {}
			for quant in quants:
				if quant.qty <= 0:
					continue
				suggested_location_id = _picking_putaway_apply(quant.product_id)
				quants_suggested_locations[quant] = suggested_location_id

			#find the packages we can movei as a whole
			top_lvl_packages = self._get_top_level_packages(cr, uid, quants_suggested_locations, context=context)
			# and then create pack operations for the top-level packages found
			for pack in top_lvl_packages:
				pack_quant_ids = pack_obj.get_content(cr, uid, [pack.id], context=context)
				pack_quants = quant_obj.browse(cr, uid, pack_quant_ids, context=context)
				vals.append({
						'picking_id': picking.id,
						'package_id': pack.id,
						'product_qty': 1.0,
						'location_id': pack.location_id.id,
						'location_dest_id': quants_suggested_locations[pack_quants[0]],
					})
				#remove the quants inside the package so that they are excluded from the rest of the computation
				for quant in pack_quants:
					del quants_suggested_locations[quant]

			# Go through all remaining reserved quants and group by product, package, lot, owner, source location and dest location
			for quant, dest_location_id in quants_suggested_locations.items():
				key = (quant.product_id.id, quant.package_id.id, quant.lot_id.id, quant.owner_id.id, quant.location_id.id, dest_location_id)
				if qtys_grouped.get(key):
					qtys_grouped[key] += quant.qty
				else:
					qtys_grouped[key] = quant.qty

			# Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
			# Multiple dictionari in forced_qties
			# 0 for product_qty 1 for product_uom_qty
			for product, qty in forced_qties.items():
				if qty[0] <= 0:
					continue
				suggested_location_id = _picking_putaway_apply(product[0])
				key = (product[0].id, False, False, False, picking.location_id.id, suggested_location_id,product[1].id)
				if qtys_grouped.get(key):
					qtys_grouped[key] += qty[0],qty[1]
				else:
					qtys_grouped[key] = qty[0],qty[1]

			# Create the necessary operations for the grouped quants and remaining qtys
			
			for key, qty in qtys_grouped.items():
				quant = 0
				quant_uom = 0
				uom_id = False
				if type(qty) == float:
					quant = qty
					quant_uom = qty
				else :
					quant = qty[1]
					quant_uom = qty[0]
				if len(key) == 7:
					uom_id = key[6]
				else:
					uom_id = self.pool.get("product.product").browse(cr, uid, key[0], context=context).uom_id.id,
				vals.append({
					'picking_id': picking.id,
					'product_qty': quant_uom,
					'product_id': key[0],
					'package_id': key[1],
					'lot_id': key[2],
					'owner_id': key[3],
					'location_id': key[4],
					'location_dest_id': key[5],
					'product_uom_id': self.pool.get("product.product").browse(cr, uid, key[0], context=context).uom_id.id,#self.pool.get("product.product").browse(cr, uid, key[0], context=context).uom_id.id,
					'ic_product_uom_qty':quant,
					'ic_uom_id':uom_id,
					# 'ean13':self.pool.get("product.product").browse(cr, uid, key[0], context=context).ean13,
				})  
			return vals

	@api.cr_uid_ids_context
	def do_prepare_partial(self, cr, uid, picking_ids, context=None):
		context = context or {}
		pack_operation_obj = self.pool.get('stock.pack.operation')
		#used to avoid recomputing the remaining quantities at each new pack operation created
		ctx = context.copy()
		ctx['no_recompute'] = True

		#get list of existing operations and delete them
		existing_package_ids = pack_operation_obj.search(cr, uid, [('picking_id', 'in', picking_ids)], context=context)
		if existing_package_ids:
			pack_operation_obj.unlink(cr, uid, existing_package_ids, context)
		for picking in self.browse(cr, uid, picking_ids, context=context):
			forced_qties = {}  # Quantity remaining after calculating reserved quants
			picking_quants = []
			#Calculate packages, reserved quants, qtys of this picking's moves
			for move in picking.move_lines:
				if move.state not in ('assigned', 'confirmed'):
					continue
				move_quants = move.reserved_quant_ids
				picking_quants += move_quants
				forced_qty = (move.state == 'assigned') and move.product_qty - sum([x.qty for x in move_quants]) or 0
				forced_uom_qty = (move.state == 'assigned') and move.product_uom_qty - sum([x.qty for x in move_quants]) or 0
				#if we used force_assign() on the move, or if the move is incomming, forced_qty > 0
				if forced_qty:
					# if forced_qties.get(move.product_id):
						# forced_qties[move.product_id,move.product_uom] += forced_qty
					# else:
					# Add multiple dictionary to passing uom and qty 
					forced_qties[move.product_id,move.product_uom] = forced_qty,forced_uom_qty
			for vals in self._prepare_pack_ops(cr, uid, picking, picking_quants, forced_qties, context=context):
				pack_operation_obj.create(cr, uid, vals, context=ctx)
		#recompute the remaining quantities all at once
		self.do_recompute_remaining_quantities(cr, uid, picking_ids, context=context)
		self.write(cr, uid, picking_ids, {'recompute_pack_op': False}, context=context)

	def _prepare_values_extra_move(self, cr, uid, op, product, remaining_qty, context=None):
		"""
		Creates an extra move when there is no corresponding original move to be copied
		"""
		picking = op.picking_id
		res = {
			'picking_id': picking.id,
			'location_id': picking.location_id.id,
			'location_dest_id': picking.location_dest_id.id,
			'product_id': product.id,
			'product_uom': op.product_uom_id.id,
			'product_uom_qty': remaining_qty,
			'name': _('Extra Move: ') + product.name,
			'state': 'draft',
			'ic_remark':op.ic_remark,
			}
		return res


	@api.cr_uid_ids_context
	def do_transfer(self, cr, uid, picking_ids, context=None):
		"""
			If no pack operation, we do simple action_done of the picking
			Otherwise, do the pack operations
		"""
		if not context:
			context = {}
		stock_move_obj = self.pool.get('stock.move')
		operation_obj = self.pool.get('stock.pack.operation')
		operation_link_obj = self.pool.get('stock.move.operation.link')
		for picking in self.browse(cr, uid, picking_ids, context=context):
			if not picking.pack_operation_ids:
				self.action_done(cr, uid, [picking.id], context=context)
				continue
				# SGEEDE Sebastian
				

			# SGEEDE Sebastian
			else:
				need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(cr, uid, picking, context=context)
				#create extra moves in the picking (unexpected product moves coming from pack operations)
				todo_move_ids = []
				if not all_op_processed:
					todo_move_ids += self._create_extra_moves(cr, uid, picking, context=context)

				picking.refresh()
				#split move lines eventually

				# SGEEDE Sebastian  #modified 21 march 17
				picking_type_id = self.pool.get('stock.picking.type').search(cr, uid,[('code', '=', 'incoming'),('warehouse_id','=',picking.transfer_id.dest_warehouse_id.id)])
				#cari parent warehouse nya sama dengan warehouse tujuan
				pickings_id = self.pool.get('stock.picking.type').browse(cr, uid, picking_type_id).id
				transfer_obj = self.pool.get('stock.internal.transfer')
				transfers = transfer_obj.browse(cr, uid, context=context)
				if picking.picking_type_id.code == 'outgoing' and picking.transfer_id:
					picking_id = self.pool.get('stock.picking').create(cr,uid,{
						'picking_type_id': pickings_id,
						'transfer_id': picking.transfer_id.id,
						'origin':picking.name,#modified 21 march 17 source document
						})
		
			# SGEEDE Sebastian

				toassign_move_ids = []
				for move in picking.move_lines:
					remaining_qty = move.remaining_qty
				
					if move.state in ('done', 'cancel'):
						#ignore stock moves cancelled or already done
						continue
					elif move.state == 'draft':
						toassign_move_ids.append(move.id)
					if remaining_qty == 0:
						if move.state in ('draft', 'assigned', 'confirmed'):
							todo_move_ids.append(move.id)
						
					elif remaining_qty > 0 and remaining_qty < move.product_qty:
						new_move = stock_move_obj.split(cr, uid, move, remaining_qty, context=context)
						operation_ids = operation_link_obj.search(cr,uid,[('move_id','=',move.id)])
						for operations in operation_link_obj.browse(cr,uid,operation_ids):
							operation_id = operations.operation_id
							ic_remark = operation_obj.browse(cr,uid,operation_id.id).ic_remark
							if ic_remark:
								stock_move_obj.write(cr,uid,move.id,{'ic_remark':ic_remark})
						todo_move_ids.append(move.id)
						#Assign move as it was assigned before
						toassign_move_ids.append(new_move)
				if need_rereserve or not all_op_processed: 
					if not picking.location_id.usage in ("supplier", "production", "inventory"):
						self.rereserve_quants(cr, uid, picking, move_ids=todo_move_ids, context=context)
					self.do_recompute_remaining_quantities(cr, uid, [picking.id], context=context)
				
				if todo_move_ids and not context.get('do_only_split'):
					for todo_move_id in todo_move_ids:  #modified 5 april 2017
						sb_move = stock_move_obj.browse(cr,uid,todo_move_id)
						if picking.picking_type_id.code == 'outgoing' and picking.transfer_id:
							self.pool.get('stock.move').create(cr,uid,{
								'name' : 'Delivery Order',
								'product_id' : sb_move.product_id.id,
								'product_uom' : sb_move.product_uom.id,
								'product_uom_qty' : sb_move.product_uom_qty,
								'location_id' : sb_move.location_dest_id.id,
								'location_dest_id' : picking.transfer_id.dest_warehouse_id.lot_stock_id.id,
								'picking_id' : picking_id,

									 })
							
							picking_obj = self.pool.get('stock.picking')
							picking_obj.action_confirm(cr, uid, picking_id)
							picking_obj.force_assign(cr,uid,picking_id)
						if picking.picking_type_id.code == 'incoming' and picking.transfer_id:
							sb_sit = transfer_obj.browse(cr,uid,picking.transfer_id.id)
							sb_out_qty = 0
							sb_in_qty = 0
							for sb_line in sb_sit.line_ids:
								sb_out_qty += sb_line.product_qty
							for sb_pick in sb_sit.picking_ids:
								if sb_pick.picking_type_id.code == 'incoming':
									for sb_moves in sb_pick.move_lines:
										sb_in_qty += sb_moves.product_uom_qty
							if sb_in_qty == sb_out_qty:#if all product has been move change state done
								transfer_obj.write(cr,uid,picking.transfer_id.id,{'state':'done'})
					print 'todo_move_ids',todo_move_ids,'action_doneeee'
					self.pool.get('stock.move').action_done(cr, uid, todo_move_ids, context=context)
				elif context.get('do_only_split'):
					context = dict(context, split=todo_move_ids)
			picking.refresh()
			self._create_backorder(cr, uid, picking, context=context)
			if toassign_move_ids: 
				print 'toassign_move_ids',toassign_move_ids
				stock_move_obj.action_assign(cr, uid, toassign_move_ids, context=context)
			
		return True


	def action_done_from_ui(self, cr, uid, picking_id, context=None):
		""" called when button 'done' is pushed in the barcode scanner UI """
		#write qty_done into field product_qty for every package_operation before doing the transfer
		pack_op_obj = self.pool.get('stock.pack.operation')
		for operation in self.browse(cr, uid, picking_id, context=context).pack_operation_ids:
			from_unit = operation.ic_uom_id
			to_unit = operation.product_id.uom_id
			qty_done = float_round(operation.qty_done/from_unit.factor, precision_rounding=from_unit.rounding)
			if to_unit:
				qty_done = qty_done * to_unit.factor
				if round:
					qty_done = ceiling(qty_done, to_unit.rounding)
			pack_op_obj.write(cr, uid, operation.id, {'ic_product_uom_qty':operation.qty_done,'product_qty': qty_done}, context=context)
		self.do_transfer(cr, uid, [picking_id], context=context)
		#return id of next picking to work on
		return self.get_next_picking_for_ui(cr, uid, context=context)

	@api.cr_uid_ids_context
	def open_barcode_interface(self, cr, uid, picking_ids, context=None):
		final_url="/barcode/web/#action=stock.ui&picking_id="+str(picking_ids[0])
		return {'type': 'ir.actions.act_url', 'url':final_url, 'target': 'new',}

	
	def process_barcode_from_ui(self, cr, uid, picking_id, barcode_str, visible_op_ids, context=None):
		'''This function is called each time there barcode scanner reads an input'''
		lot_obj = self.pool.get('stock.production.lot')
		package_obj = self.pool.get('stock.quant.package')
		product_obj = self.pool.get('product.product')
		stock_operation_obj = self.pool.get('stock.pack.operation')
		stock_location_obj = self.pool.get('stock.location')
		product_uom_price_obj = self.pool.get('product.uom.price')
		multi_barcode_obj = self.pool.get('product.multi.barcode')
		answer = {'filter_loc': False, 'operation_id': False}
		context = context or {}
		#check if the barcode correspond to a location
		matching_location_ids = stock_location_obj.search(cr, uid, [('loc_barcode', '=', barcode_str)], context=context)
		if matching_location_ids:
			#if we have a location, return immediatly with the location name
			location = stock_location_obj.browse(cr, uid, matching_location_ids[0], context=None)
			answer['filter_loc'] = stock_location_obj._name_get(cr, uid, location, context=None)
			answer['filter_loc_id'] = matching_location_ids[0]
			return answer
		#check if the barcode correspond to a product
		# print 'barcodestr',barcode_str
		matching_product_ids = product_obj.search(cr, uid, ['|', ('ean13', '=', barcode_str), ('default_code', '=', barcode_str)], context=context)
		if matching_product_ids:
			context['from_barcode']= True
			# print 'suksesprocessbarcode'
			op_id = stock_operation_obj._search_and_increment(cr, uid, picking_id, [('product_id', '=', matching_product_ids[0])], filter_visible=True, visible_op_ids=visible_op_ids, increment=True, context=context)
			answer['operation_id'] = op_id
			return answer
		#check if barcode correspond to uom price
		matching_uom_ids = product_uom_price_obj.search(cr, uid, [('name','=',barcode_str)])
		if matching_uom_ids:
			context['from_barcode']= True
			product_id = product_uom_price_obj.browse(cr, uid, matching_uom_ids[0]).product_id
			op_id = stock_operation_obj._search_and_increment(cr, uid, picking_id, [('product_id', '=', product_id.id)], filter_visible=True, visible_op_ids=visible_op_ids, increment=True, context=context)
			answer['operation_id'] = op_id
			return answer

		#check if barcode correspond to multiple barcode
		matching_multibarcode_ids = multi_barcode_obj.search(cr, uid, [('name','=',barcode_str)])
		if matching_multibarcode_ids:
			context['from_barcode']= True
			product_id = multi_barcode_obj.browse(cr, uid, matching_multibarcode_ids[0]).product_id
			op_id = stock_operation_obj._search_and_increment(cr, uid, picking_id, [('product_id', '=', product_id.id)], filter_visible=True, visible_op_ids=visible_op_ids, increment=True, context=context)
			answer['operation_id'] = op_id
			return answer

		#check if the barcode correspond to a lot
		matching_lot_ids = lot_obj.search(cr, uid, [('name', '=', barcode_str)], context=context)
		if matching_lot_ids:
			lot = lot_obj.browse(cr, uid, matching_lot_ids[0], context=context)
			op_id = stock_operation_obj._search_and_increment(cr, uid, picking_id, [('product_id', '=', lot.product_id.id), ('lot_id', '=', lot.id)], filter_visible=True, visible_op_ids=visible_op_ids, increment=True, context=context)
			answer['operation_id'] = op_id
			return answer
		#check if the barcode correspond to a package
		matching_package_ids = package_obj.search(cr, uid, [('name', '=', barcode_str)], context=context)
		if matching_package_ids:
			op_id = stock_operation_obj._search_and_increment(cr, uid, picking_id, [('package_id', '=', matching_package_ids[0])], filter_visible=True, visible_op_ids=visible_op_ids, increment=True, context=context)
			answer['operation_id'] = op_id
			return answer
		return answer

	def do_merge(self, cr, uid, ids, context=None):
		"""
		To merge similar type of Inventory Loss.
		Orders will only be merged if:
		* Stock Pickings are in draft
		* Stock Pickings belong to the same partner
		* Stock Pickings are have same stock location,
		Lines will only be merged if:
		* Order lines are exactly the same except for the quantity and unit

		 @param self: The object pointer.
		 @param cr: A database cursor
		 @param uid: ID of the user currently logged in
		 @param ids: the ID or list of IDs
		 @param context: A standard dictionary

		 @return: new stock picking id

		"""
		#TOFIX: merged move line should be unlink
		def make_key(br, fields):
			list_key = []
			for field in fields:
				field_val = getattr(br, field)
				if field in ('product_id', 'account_analytic_id'):
					if not field_val:
						field_val = False
				if isinstance(field_val, browse_record):
					field_val = field_val.id
				elif isinstance(field_val, browse_null):
					field_val = False
				elif isinstance(field_val, browse_record_list):
					field_val = ((6, 0, tuple([v.id for v in field_val])),)
				list_key.append((field, field_val))
			list_key.sort()
			return tuple(list_key)

		context = dict(context or {})

		# Compute what the new picking should contain
		new_pickings = {}
		move_lines_to_move = []
		move_obj = self.pool.get('stock.move')

		for spicking in [picking for picking in self.browse(cr, uid, ids, context=context) if picking.state == 'draft']:
			order_key = make_key(spicking, ('partner_id','source_location'))
			new_order = new_pickings.setdefault(order_key, ({}, []))
			new_order[1].append(spicking.id)
			order_infos = new_order[0]
			# print 'order_infos',order_infos
			move_data = []
			if not order_infos:				
				order_infos.update({
					'origin': spicking.origin,
					'date': spicking.date,
					'partner_id': spicking.partner_id.id,
					'picking_type_id': spicking.picking_type_id.id,
					'location_id': spicking.location_id.id,
					'source_location':spicking.source_location.id,
					'state': 'draft',
					'move_lines':{},
					'note': '%s' % (spicking.note or '',),
					'lane': '%s' % (spicking.lane or '',),
				})
			else:
				if spicking.date < order_infos['date']:
					order_infos['date'] = spicking.date
				if spicking.note:
					order_infos['note'] = (order_infos['note'] or '') + ('\n%s' % (spicking.note,))
				if spicking.origin:
					order_infos['origin'] = (order_infos['origin'] or '') + ' ' + spicking.origin
				if spicking.lane:
					order_infos['lane'] = (order_infos['lane'] or '') + (', %s' % (spicking.lane,))
			for move_lines in spicking.move_lines:
				move_lines_to_move += [move_lines.id]
				#Merge all move line

		allpickings = []
		orders_info = {}
		for order_key, (picking_data, old_ids) in new_pickings.iteritems():
			# skip merges with only one order
			if len(old_ids) < 2:
				allpickings += (old_ids or [])
				continue

			# cleanup order line data
			for key, value in picking_data['move_lines'].iteritems():
				del value['uom_factor']
				value.update(dict(key))
			
			move_ids = []
			for move in move_lines_to_move:
				picking_id = move_obj.browse(cr,uid,move).picking_id
				if picking_id.id in old_ids:
					move_ids.append(move)
			picking_data['move_lines'] = [(6, 0, move_ids)]

			# create the new order
			newpicking_id = self.create(cr, uid, picking_data)
			orders_info.update({newpicking_id: old_ids})
			allpickings.append(newpicking_id)
			pickings = self.browse(cr,uid,newpicking_id)
			note = 'Merge with ' + pickings.name
			# make triggers pointing to the old orders point to the new order
			for old_id in old_ids:
				self.action_cancel(cr,uid,old_id,context)
				self.write(cr, uid, [old_id], {'note': note}, context=context)
				self.unlink(cr,uid,[old_id])
		return orders_info

class stock_move(osv.osv):
	_inherit = "stock.move"
	_columns = {
		'ic_remark'	:fields.char('Remark'),
	}
	def write(self, cr, uid, ids, vals, context=None):
		if isinstance(ids, (int, long)):
			ids = [ids]
		res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
		from openerp import workflow
		if vals.get('state') in ['done', 'cancel']:
			for move in self.browse(cr, uid, ids, context=context):
				if move.purchase_line_id and move.purchase_line_id.order_id:
					order_id = move.purchase_line_id.order_id.id
					if self.pool.get('purchase.order').test_moves_done(cr, uid, [order_id], context=context):
						workflow.trg_validate(uid, 'purchase.order', order_id, 'picking_done', cr)
					else:
						workflow.trg_validate(uid, 'purchase.order', order_id, 'picking_partial', cr)
					if self.pool.get('purchase.order').test_moves_except(cr, uid, [order_id], context=context):
						workflow.trg_validate(uid, 'purchase.order', order_id, 'picking_cancel', cr)
		return res

	def onchange_inventory_loss(self, cr, uid, ids, prod_id, product_qty_now, product_qty,parent_location=False):
		product = self.pool.get('product.product').browse(cr, uid, [prod_id])
		user = self.pool.get('res.users').browse(cr, uid, uid)
		move_obj = self.pool.get('stock.move')
		picking_obj = self.pool.get('stock.picking')
		picking = move_obj.browse(cr,uid,ids).picking_id
		
		if product_qty > product_qty_now :
			result= {
			'product_uom_qty':product_qty-product_qty_now,
			'lost_qty':product_qty_now-product_qty,
			'location_dest_id': parent_location,
			'location_id': user.company_id.destination_location.id,
			}

		if product_qty <= product_qty_now :
			result= {
				'product_uom_qty':product_qty_now-product_qty,
				'lost_qty':product_qty_now-product_qty,
				'location_id': parent_location,
				'location_dest_id': user.company_id.destination_location.id,
			}

		return {'value': result}
	def onchange_product_id_inventory_loss(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False, parent_location=False, context={}):
		if not prod_id:
			return {}
		user = self.pool.get('res.users').browse(cr, uid, uid)
		move_obj = self.pool.get('stock.move')
		picking_obj = self.pool.get('stock.picking')
		picking = picking_obj.browse(cr,uid,ids)
		lang = user and user.lang or False
		if partner_id:
			addr_rec = self.pool.get('res.partner').browse(cr, uid, partner_id)
			if addr_rec:
				lang = addr_rec and addr_rec.lang or False
		ctx = {'lang': lang}
		if parent_location:
			ctx['location'] = parent_location
		# print ctx
		product = self.pool.get('product.product').browse(cr, uid, [prod_id], context=ctx)[0]
		product_template = self.pool.get('product.template').browse(cr, uid, [product.product_tmpl_id.id], context=ctx)[0]
		if product_template:
			uos_id = product.uos_id and product.uos_id.id or False
			result = {
				'name': product.partner_ref,
				'product_uom': product.uom_id.id,
				'product_uom_alt': product.uom_id.id,
				'product_qty':product.qty_available,
				'product_qty_now':product.qty_available,
				'product_qty_current':product.qty_available,
				'current_stock':product.qty_available,
				'product_uos': uos_id,
				'product_uom_qty': 0,
				'product_uos_qty': self.pool.get('stock.move').onchange_quantity(cr, uid, ids, prod_id, 1.00, product.uom_id.id, uos_id)['value']['product_uos_qty'],
				'price_unit': product_template.standard_price,
				# 'location_id':picking.source_location.id,
			}
		if 'inventory_loss_create' in context:
			if context['inventory_loss_create']:
				if not user.company_id.source_location:
					raise osv.except_osv(_('Error!'), _('Source Location Stock in configuration is empty, Please Setup first.'))
				result['location_id'] = parent_location
			
			if not user.company_id.source_location:
				raise osv.except_osv(_('Error!'), _('Destination Location Stock in configuration is empty, Please Setup first.'))
			result['location_dest_id'] = user.company_id.destination_location.id
		return {'value': result}
class stock_pack_operation(osv.osv):
	_inherit = "stock.pack.operation"
	_description = "Packing Operation"

	def _get_ic_product_qty(self, cr, uid, ids, name, arg, context=None):
		context = context or {}
		res = {}
		for operation in self.browse(cr, uid, ids):
			amount = 0
			product_id = operation.product_id.id
			from_unit = operation.product_uom_id
			to_unit = operation.product_id.uom_id
			product_qty = operation.ic_product_uom_qty
			# res[operation.id] = move.product_qty_now
			if from_unit:
				amount = float_round(product_qty/from_unit.factor, precision_rounding=from_unit.rounding)
				if from_unit:
					amount = amount * to_unit.factor
					if round:
						amount = ceiling(amount, to_unit.rounding)
			res[operation.id] = amount
		return res
	def _get_ic_ean13(self, cr, uid, ids, name, arg, context=None):
		context = context or {}
		res = {}
		product_uom_price_obj = self.pool.get('product.uom.price')
		multi_barcode_obj = self.pool.get('product.multi.barcode')
		for operation in self.browse(cr, uid, ids):
			barcode = ''
			matching_uom_ids = product_uom_price_obj.search(cr, uid, [('product_id','=',operation.product_id.id)])
			matching_multibarcode_ids = multi_barcode_obj.search(cr, uid, [('product_id','=',operation.product_id.id)])
			if operation.product_id.ean13:
				barcode += operation.product_id.ean13 +' '
			if matching_uom_ids:
				for uom in product_uom_price_obj.browse(cr, uid, matching_uom_ids):
					barcode += uom.name +' '
			if matching_multibarcode_ids:
				for multi in multi_barcode_obj.browse(cr, uid, matching_multibarcode_ids):
					barcode += multi.name +' '
			res[operation.id] = barcode
		return res
	_columns = {
		'ic_product_qty': fields.function(_get_ic_product_qty,  method=True, type='float', string='Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
		'ic_product_uom_qty': fields.float( string='Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
		'ic_uom_id':fields.many2one('product.uom','Product UOm'),
		'ic_ean13':fields.function(_get_ic_ean13, method=True, type='char', string='Barcode'),
		'ic_remark':fields.char('Remark'),
		'reason_id':fields.many2one('isana.reason','Reason'),
	}
	_defaults = {
		'ic_remark' : '-',
	}

	def isana_js_change_uom(self, cr, uid, id, uom, context=None):
		''' Used by barcode interface to create a new lot and assign it to the operation
		'''
		obj = self.browse(cr,uid,id,context)
		uom_obj = self.pool.get('product.uom')
		uom_ids = uom_obj.search(cr, uid, [('name','=',uom)])
		if uom_ids:
			to_product_uom_id = uom_obj.browse(cr, uid, uom_ids[0])
		else:
			to_product_uom_id = obj.product_uom_id
		
		from_unit = obj.product_uom_id
		to_unit = to_product_uom_id		
		if obj.product_uom_id.category_id.id != to_product_uom_id.category_id.id:
			raise orm.except_orm(_('Warning'), _('Please use the same UOM Category in Product for replace Product Unit of Measure.'))
			
		quantity = obj.product_qty / from_unit.factor * to_unit.factor		
		self.write(cr, uid, id, {'ic_product_uom_qty': quantity,'ic_uom_id':uom_ids[0]}, context=context)
		

	def action_drop_down(self, cr, uid, ids, context=None):
		''' Used by barcode interface to say that pack_operation has been moved from src location 
			to destination location, if qty_done is less than product_qty than we have to split the
			operation in two to process the one with the qty moved
		'''
		processed_ids = []
		qty_done = 0
		move_obj = self.pool.get("stock.move")
		for pack_op in self.browse(cr, uid, ids, context=None):
			if pack_op.product_id and pack_op.location_id and pack_op.location_dest_id:
				move_obj.check_tracking_product(cr, uid, pack_op.product_id, pack_op.lot_id.id, pack_op.location_id, pack_op.location_dest_id, context=context)
			op = pack_op.id
			from_unit = pack_op.ic_uom_id
			to_unit = pack_op.product_uom_id			
			qty_done = float_round(pack_op.qty_done/from_unit.factor, precision_rounding=from_unit.rounding)
			if to_unit:
				qty_done = qty_done * to_unit.factor
				if round:
					qty_done = ceiling(qty_done, to_unit.rounding)
			# We convert from UOM Display to UOM product
			if pack_op.qty_done < pack_op.ic_product_uom_qty:
				# we split the operation in two
				op = self.copy(cr, uid, pack_op.id, {'product_qty': qty_done, 'qty_done': pack_op.qty_done,'ic_product_uom_qty':pack_op.qty_done}, context=context)
				self.write(cr, uid, [pack_op.id], {'ic_product_uom_qty':pack_op.ic_product_uom_qty - pack_op.qty_done,'product_qty': pack_op.product_qty - qty_done, 'qty_done': 0, 'lot_id': False}, context=context)
			processed_ids.append(op)
		self.write(cr, uid, processed_ids, {'processed': 'true'}, context=context)


	def _search_and_increment(self, cr, uid, picking_id, domain, filter_visible=False, visible_op_ids=False, increment=True, context=None):
		'''Search for an operation with given 'domain' in a picking, if it exists increment the qty (+1) otherwise create it

		:param domain: list of tuple directly reusable as a domain
		context can receive a key 'current_package_id' with the package to consider for this operation
		returns True
		'''
		if context is None:
			context = {}
		#if current_package_id is given in the context, we increase the number of items in this package
		package_clause = [('result_package_id', '=', context.get('current_package_id', False))]
		existing_operation_ids = self.search(cr, uid, [('picking_id', '=', picking_id)] + domain + package_clause, context=context)
		todo_operation_ids = []
		if existing_operation_ids:
			if filter_visible:
				todo_operation_ids = [val for val in existing_operation_ids if val in visible_op_ids]
			else:
				todo_operation_ids = existing_operation_ids
		if todo_operation_ids:
			#existing operation found for the given domain and picking => increment its quantity
			operation_id = todo_operation_ids[0]
			# op_obj = self.browse(cr, uid, operation_id, context=context)
			op_obj = self.read(cr, uid, operation_id, ['qty_done', 'ic_product_uom_qty','product_qty'],context=context)
			# qty = op_obj.qty_done
			qty = op_obj['qty_done']
			if increment:
				qty += 1
				if 'from_barcode' in context:
					if context['from_barcode']:
						# qty = op_obj.ic_product_uom_qty
						qty = op_obj['ic_product_uom_qty']
			else:
				qty -= 1 if qty >= 1 else 0
				if qty == 0 and op_obj['product_qty'] == 0:
					#we have a line with 0 qty set, so delete it
					self.unlink(cr, uid, [operation_id], context=context)
					return False
			self.write(cr, uid, [operation_id], {'qty_done': qty}, context=context)
		else:
			#no existing operation found for the given domain and picking => create a new one
			picking_obj = self.pool.get("stock.picking")
			picking = picking_obj.browse(cr, uid, picking_id, context=context)
			values = {
				'picking_id': picking_id,
				'product_qty': 0,
				'location_id': picking.location_id.id, 
				'location_dest_id': picking.location_dest_id.id,
				'qty_done': 1,
				}
			for key in domain:
				var_name, dummy, value = key
				uom_id = False
				if var_name == 'product_id':
					uom_id = self.pool.get('product.product').browse(cr, uid, value, context=context).uom_id.id
				update_dict = {var_name: value}
				if uom_id:
					update_dict['product_uom_id'] = uom_id
				values.update(update_dict)
			operation_id = self.create(cr, uid, values, context=context)
		return operation_id

class isana_reason(osv.osv):
	_name = "isana.reason"
	_columns = {
		'name':fields.char('Reason'),
	}


#Notes#=====================================================
#===========================================================
#	# amount = float_round(qty/from_unit.factor, precision_rounding=from_unit.rounding)
#         if to_unit:
#             amount = amount * to_unit.factor
#             if round:
#                 amount = ceiling(amount, to_unit.rounding)
#
#  if product.uom_id.uom_type == 'bigger' and product.uom_id.factor != 1:
#  				qty = qty * product.uom_id.factor
#===========================================================

# class stock_move_operation_link(osv.osv):
#     """
#     Table making the link between stock.moves and stock.pack.operations to compute the remaining quantities on each of these objects
#     """
#     _inherit = "stock.move.operation.link"
#     _description = "Link between stock moves and pack operations"

#     _columns = {
#         'ic_remark': fields.char('Remark', help="Remark from stock pack operation"),
#         }
