# -*- coding: utf-8 -*-

from odoo import fields, models, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ifu = fields.Char(string='IFU')
    n_ppr = fields.Char(string='PPR')
