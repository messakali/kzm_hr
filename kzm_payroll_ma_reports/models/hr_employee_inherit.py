# -*- coding: utf-8 -*-
from pprint import pprint

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrEmployeeInherit(models.AbstractModel):
    _inherit = 'hr.employee.base'

    company_virement_bank_id = fields.Many2one('res.bank', string='Banque de virement sociéte')


