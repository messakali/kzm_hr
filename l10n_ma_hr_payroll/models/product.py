# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class product_template(models.Model):
    _inherit = 'product.template'

    payroll_type = fields.Selection([
        ('rubrique', 'Rubrique'),
        ('avantage', 'Avantage'),
        #('avance', 'Avance'),
        ('majoration_net', 'Majoration sur le salaire net'),
        ('retenu_net', 'Retenu sur le salaire net'),
    ], string=u'Type',)

    payroll_rubrique_id = fields.Many2one('hr.rubrique', string=u'Rubrique',)
    payroll_avance_id = fields.Many2one('hr.avance', string=u'Avance',)
    payroll_avantage_id = fields.Many2one('hr.avantage', string=u'Avantage',)
    default_expense_ok = fields.Boolean(
        string=u'Utiliser par défaut dans les note de frais', default=False,)
