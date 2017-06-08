# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp


class hr_contribution_register(models.Model):
    _inherit = 'hr.contribution.register'

    @api.one
    def _get_company_currency(self):
        if self.company_id:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id
            
    
    partner_id = fields.Many2one(required=True, )
    debit = fields.Monetary(string=u'Débit', digits=dp.get_precision(
        'Account'), related='partner_id.debit',)
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')
