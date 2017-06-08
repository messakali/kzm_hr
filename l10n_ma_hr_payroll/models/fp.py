# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp


class l10n_ma_fp(models.Model):
    _name = 'l10n.ma.fp'
    _description = 'Frais professionels'

    @api.one
    @api.depends("name",  "rate")
    def _compute_display_name(self):
        self.display_name = ' - '.join([self.name, str(self.rate) + ' %'])

    display_name = fields.Char(
        string=u'Nom', size=64,  compute='_compute_display_name')
    name = fields.Char(string=u'Nom', size=64,  required=True)
    rate = fields.Float(
        string=u'Rate', digits_compute=dp.get_precision('Account'), required=True,)
