
import time
from openerp.osv import osv
from openerp.report import report_sxw
import calendar

class sgeede_liquidityreports(report_sxw.rml_parse):

	def __init__(self, cr, uid, name, context):
		super(sgeede_liquidityreports, self).__init__(cr, uid, name, context=context)
		self.total = 0.0
		self.qty = 0.0
		self.subtotal = 0.0
		self.total_qtyex = 0.0
		self.total_amount = 0.0
		self.total_sale = 0.0
		self.grand_total_profit = 0.0
		self.localcontext.update({
			'time': time,
			'strip_name': self._strip_name,		
			'get_view': self._get_view,

		})
	
	
	
	def _get_view(self, form):
		company = self.pool.get('res.users').browse(self.cr, self.uid, self.uid).company_id
		content = ""
		journal_obj = self.pool.get('account.journal')
		partner_obj = self.pool.get('res.partner')
		total_debit = 0
		total_credit = 0
		month_string = ''
		self.cr.execute("""SELECT aml.journal_id,aml.date,aml.name,aml.ref,aml.partner_id,aa.name,aml.debit,aml.credit from account_move_line aml
							 inner join account_account aa on aml.account_id = aa.id where 
							 aml.date >= %s and aml.date <= %s and aa.type = 'liquidity'
						""",
						(form['date_from'] , form['date_to']))
		query_move_line = self.cr.fetchall()

		self.cr.execute("""SELECT distinct extract(month from date) from account_move_line where 
							date >= %s and date <= %s""",
						(form['date_from'] , form['date_to']))
		query_month = self.cr.fetchall()
		count = 0
		for month in query_month:
			if count > 0 :
				month_string +=', '+ calendar.month_name[int(month[0])]
			else:
				month_string += calendar.month_name[int(month[0])]
			count +=1
		if query_move_line:
			content +="""					
				<table class="table table-condensed">
                    <thead>                    	
                        <tr>
                            <th>Journal</th>                                    
                            <th>Date</th>
                            <th>Name</th>
                            <th>Reference</th>
                            <th>Partner</th>
                            <th>Account</th>
                            <th>Debit</th> 
                            <th>Credit</th>                        
                        </tr>
                    </thead>	               
				""" 				
			for journal_id,date,name,ref,partner_id,account_name,debit,credit in query_move_line:			
				journal = journal_obj.browse(self.cr,self.uid,journal_id)
				partner = partner_obj.browse(self.cr,self.uid,partner_id)
				total_debit += debit
				total_credit += credit
				content +="""
					<tr>
						<td><span>%s</span></td>
	                    <td><span>%s</span></td>
	                    <td><span>%s</span></td>
	                    <td><span>%s</span></td>
	                    <td><span>%s</span></td>
	                    <td><span>%s</span></td>
	                    <td class="text-right">
	                        <span>%s</span>
	                    </td>		                    
	                    <td class="text-right">
	                        <span>%s</span>
	                    </td>
	                </tr>

				""" % (journal.name, date, name, ref, partner.name, account_name,self.formatLang(debit, currency_obj=company.currency_id),self.formatLang(credit, currency_obj=company.currency_id))
			content += """
					<tr>
		                <td colspan="6"><strong>%s</strong></td>
		                
		                <td class="text-right">
		                    <strong>%s</strong>
		                </td>
		                <td class="text-right">
		                   <strong>%s</strong>
		                </td>
		            </tr> 
				"""% (month_string,self.formatLang(total_debit, currency_obj=company.currency_id),self.formatLang(total_credit, currency_obj=company.currency_id))

			content += """</table>"""		

		return content
	


class report_sale_profit_report(osv.AbstractModel):
	_name = 'report.sgeede_liquidity_report.sgeede_liquidity_reports'
	_inherit = 'report.abstract_report'
	_template = 'sgeede_liquidity_report.sgeede_liquidity_reports'
	_wrapped_report_class = sgeede_liquidityreports