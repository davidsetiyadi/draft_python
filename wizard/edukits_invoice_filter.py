# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, fields
import calendar
from openerp.tools.translate import _

class edukits_invoice_filter(osv.osv_memory):
	_name = 'edukits.invoice.filter'
	_description = 'invoice filter'

	
	_columns = {
		'model_id'		: fields.many2one('ir.model', 'Model', select=1),
		'date_from'		: fields.date('Date Start'),
		'date_to'		: fields.date('Date To'),
		'field_id'		: fields.many2one('ir.model.fields', 'Field', select=1,domain="[('ttype','in',('date','datetime'))]"),
		# 'so_discount_account_sgd': fields.related('company_id', 'so_discount_account_sgd', type='many2one', relation='account.account', string='Sale Discount Account SGD'),
	}

	_defaults = {
		'date_from': lambda *a: time.strftime('%Y-%m-01'),
		'date_to': lambda *a: time.strftime('%Y-%m-%d'),
		'model_id':lambda self,cr,uid,c: self.pool.get('ir.model').search(cr,uid, [('model','=','account.invoice')])[0],
	}
	
	def onchange_model_id(self,cr,uid,ids,model_id,context=None):
		domain = [('model_id','=',model_id),('ttype','in',('date','datetime'))]
		return {'domain':{'field_id':domain}}

	def filter_invoice(self, cr, uid, ids, context=None):
		"""
		 To get the date and print the report
		 @param self: The object pointer.
		 @param cr: A database cursor
		 @param uid: ID of the user currently logged in
		 @param context: A standard dictionary
		 @return : retrun report
		"""
	
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
		res = self.read(cr, uid, ids, ['date_from', 'date_to'], context=context)
		res = res and res[0] or {}		
		invoice_obj = self.pool.get('account.invoice')
		filters = self.browse(cr, uid, ids)
		model_obj = self.pool.get(filters.model_id.model) 
		if filters.field_id.ttype == 'date':
			model_ids = model_obj.search(cr, uid, [(filters.field_id.name,'>=',filters.date_from),(filters.field_id.name,'<=',filters.date_to)])
		else:
			model_ids = model_obj.search(cr, uid, [(filters.field_id.name,'>=',res['date_from']+' 00:00:00'),(filters.field_id.name,'<=',res['date_to']+' 23:59:59')])

		if len(model_ids) == 1:
			domain = [('id', '=', model_ids)]
		else:
			domain = [('id', 'in', model_ids)]

		res_model = filters.model_id.model
		# context.update({'tree_view_ref': 'account.invoice_tree','search_default_active_invoice': 1, })
		return {
			'name': _(str(filters.model_id.name)+': '+ str(filters.field_id.field_description)+' '+str(res['date_from'])+' to '+str(res['date_to'])),
			'view_id': False,
			'view_mode': 'tree,form',
			'view_type': 'form',
			'context': context,
			'create':"false",
			# 'limit': 20
			'domain': domain,
			'type': 'ir.actions.act_window',                    
			'res_model': res_model,
			
			
		}
