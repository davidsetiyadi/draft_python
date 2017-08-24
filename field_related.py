# 'move_status':fields.related('move_ids','state',type='selection',selection=[('draft', 'New'),
#                                    ('cancel', 'Cancelled'),
#                                    ('waiting', 'Waiting Another Move'),
#                                    ('confirmed', 'Waiting Availability'),
#                                    ('assigned', 'Available'),
#                                    ('done', 'Done'),
#                                    ],string='Move Status'),
		# 'invoice_number':fields.related('invoice_lines','invoice_id',type='many2one',relation='account.invoice',string='Invoice Number'),
		