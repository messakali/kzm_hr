# encoding: utf-8

from odoo import models, api, fields, _
from odoo.exceptions import Warning


class res_partner_bank(models.Model):
    _inherit = 'res.partner.bank'

    acc_number = fields.Char( )

    @api.one
    @api.constrains('acc_number')
    def _check_acc_number(self):
        if len(self.acc_number) != 24:
            raise Warning(_('The length sould be 24 number not %s') % len(self.acc_number))
