
	#Add char in field function
	# def _get_invoice_number(self, cr, uid, ids, field_name, arg, context):
	# 	res = {}
	# 	for order_line in self.browse(cr, uid, ids):
	# 		invoice = ''
	# 		count = 0
	# 		for invoiced in order_line.invoice_lines:            
	# 			# print invoice.invoice_id.number,'print'
	# 			if invoiced.invoice_id.number:
	# 				if count == 0 :
	# 					invoice += invoiced.invoice_id.number
	# 				else:
	# 					invoice += ', '+invoiced.invoice_id.number
	# 			else:
	# 				if count == 0 :
	# 					invoice += 'Draft'
	# 				else:
	# 					invoice += ', '+'Draft'
	# 			count += 1
	# 		res[order_line.id] = invoice            
	# 	return res


	#Add Field selection in field function
	# def _get_move_status(self, cr, uid, ids, field_name, arg, context):
	# 	res = {}
	# 	states = {'draft': 'New','cancel': 'Cancelled','waiting': 'Waiting Another Move',
 #                'confirmed': 'Waiting Availability','assigned': 'Available','done': 'Done',}
	# 	for order_line in self.browse(cr, uid, ids):
	# 		status = ''
	# 		count = 0
	# 		for move in order_line.move_ids:        
	# 			state = str(move.state)
	# 			# print invoice.invoice_id.number,'print'
	# 			if count == 0 :
	# 				status += states[state]
	# 			else:
	# 				status += ', '+states[state]
	# 			count += 1
	# 			print status,'statusss'
	# 		res[order_line.id] = status            
	# 	return res
	# 	'invoice_number':fields.function(_get_invoice_number, string='Invoice Number',type='char' ),
	# 	'move_status':fields.function(_get_move_status,string='Transfer Status',type='char'),
	# 