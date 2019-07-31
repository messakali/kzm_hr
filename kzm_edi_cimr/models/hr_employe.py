# -*- coding: utf-8 -*-

from odoo import fields, models


class HrEmployee(models.Model):
        _inherit = 'hr.employee'

        cimr = fields.Char(string=u'N° CIMR')
