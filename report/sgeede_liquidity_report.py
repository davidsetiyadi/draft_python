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

class sgeede_liquidity_report(osv.osv_memory):
	_name = 'sgeede.liquidity.report'
	_description = 'Liquidity Report'

	
	_columns = {
		'date_from'	: fields.date('Date Start'),
		'date_to'		: fields.date('Date To'),
	}

	_defaults = {
		'date_from': lambda *a: time.strftime('%Y-%m-01'),
		'date_to': lambda *a: time.strftime('%Y-%m-%d'),
	}

	def print_report(self, cr, uid, ids, context=None):
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
		
		datas['form'] = res
		# form = res[0]
		if res.get('id',False):
			datas['ids']=[res['id']]
		mobile_obj = self.pool.get('sgeede.liquidity.report.mobile')
		mobile_search = mobile_obj.search(cr,uid,[])        
		for mobile in mobile_search:
			mobile_unl=mobile_obj.unlink(cr, uid, mobile, context=context)

		
		count = 0
		date_starts = datetime.strptime(res['date_from'],"%Y-%m-%d")
		date_stops = datetime.strptime(res['date_to'],"%Y-%m-%d")
		date_starts = date_starts.replace(day=1)
		result = []
		while date_starts <= date_stops:
			result.append(date_starts)
			date_to = date_starts + relativedelta(months=1)
		
			cash_in = 0
			cash_out = 0
			month = '{:02d}'.format(date_starts.month)
			
			month_string = calendar.month_name[int(month)]
			cr.execute("""SELECT sum(aml.debit),sum(aml.credit) from account_move_line 
				aml inner join account_account aa on aml.account_id = aa.id 
				inner join account_account_type aat on aa.user_type = aat.id 
				where aat.code in ('bank','cash') AND aml.date >= %s and aml.date <= %s
				""",(date_starts , date_to))
			query_cash_in  = cr.fetchall()
			

			cr.execute("""SELECT sum(aml.debit),sum(aml.credit) from account_move_line 
				aml inner join account_account aa on aml.account_id = aa.id 
				inner join account_account_type aat on aa.user_type = aat.id 
				where aat.code = 'expense' AND aml.date >= %s and aml.date <= %s
				""",(date_starts , date_to))
			query_cash_out  = cr.fetchall()
			if query_cash_in:
				cash_in += query_cash_in[0][0] or 0
			if query_cash_out: 
				cash_out += query_cash_out[0][0] or 0

			total = mobile_obj.create(cr,uid,{
				'name'		:month_string ,
				'cash_in'	:cash_in or 0,
				'cash_out'	:cash_out or 0,
				'balance'	:cash_in - cash_out,
			})
			date_starts += relativedelta(months=1)

		# return self.pool['report'].get_action(cr, uid, [], 'sgeede_liquidity_report.sgeede_liquidity_reports', data=datas, context=context)
		return {
			'name': 'teste',#_('Liquidity ' +str(res[0]['date_from'])+' to '+str(res[0]['date_to'])),
			'view_id': False,
			'view_mode': 'tree',
			'view_type': 'form',
			'context': {'tree_view_ref': 'sgeede_liquidity_report.liquidity_report_mobile_tree_view'},
			# 'limit': 20
			# 'domain': domain,
			'type': 'ir.actions.act_window',                    
			'res_model': 'sgeede.liquidity.report.mobile',
			
			
		}


class sgeede_liquidity_report_mobile(osv.osv_memory):
	_name = 'sgeede.liquidity.report.mobile'
	_description = 'Liquidity Mobile'

	_columns = {
		'name': fields.char('Month'),
		'cash_in': fields.float('Cash In'),
		'cash_out': fields.float('Cash Out'),
		'balance':fields.float('Balance'),

	}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

