# -*- coding: utf-8 -*-

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    cimr = fields.Char(string=u'N° CIMR')
    cimr_category = fields.Char(string=u'N° Catégorie CIMR')
