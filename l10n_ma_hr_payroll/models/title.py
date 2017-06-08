# encoding: utf-8

from odoo import models, fields, api, _


class res_partner_title(models.Model):
    _inherit = 'res.partner.title'

    employee = fields.Boolean(string=u'Employé',  default=False)
    gender = fields.Selection([
        ('male', 'Masculin'),
        ('female', 'Féminin'),
    ], string=u'Sexe',)
