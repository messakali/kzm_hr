# encoding: utf-8

from odoo import models, fields, api, _


class job(models.Model):
    _inherit = 'hr.job'

    code = fields.Char(string=u'Code', size=64,)
