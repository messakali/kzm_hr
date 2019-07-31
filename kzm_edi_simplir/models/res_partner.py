# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    code_commune = fields.Char(string="Commune")
    taux_fp = fields.Char(string="Taux frais professionnels")
