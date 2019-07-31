# -*- coding: utf-8 -*-

from odoo import fields, models, api


class HrPayroll_ma(models.Model):
    _inherit = 'hr.payroll_ma'

    penalite = fields.Float(string=u'Penalité')
    majoration = fields.Float(string='Majoration')
    ref_payment = fields.Char(string=u'Référence de paiement')
    num_quittance = fields.Char(string=u'Numéro de quittance')
