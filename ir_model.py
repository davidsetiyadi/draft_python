from collections import defaultdict
import logging
import re
import time
import types

import openerp
from openerp import SUPERUSER_ID
from openerp import models, tools, api
from openerp.modules.registry import RegistryManager
from openerp.osv import fields, osv
from openerp.osv.orm import BaseModel, Model, MAGIC_COLUMNS, except_orm
from openerp.tools import config
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _

class ir_model_fields(osv.osv):
	_inherit = 'ir.model.fields'
	_description = "Fields"
		
	def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
		if context is None:
			context = {}
		if context.get('model_id'):
			args.append(('model_id', '=', context.get('model_id')) )
		return super(ir_model_fields,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)
	