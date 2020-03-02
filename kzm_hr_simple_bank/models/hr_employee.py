# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrEmployee(models.AbstractModel):
    _inherit = "hr.employee.base"

    bank_id = fields.Many2one('res.bank', string="Bank")
    rib = fields.Char(string="RIB")
    agency = fields.Char(string="Agency")

    @api.constrains("rib")
    def _check_rib(self):
        for record in self:
            if record.rib:
                new_rib = record.rib.replace(" ", "")
                if not len(new_rib) == 24:
                    raise ValidationError(_('The value of RIB is not correct !.'))

    @api.onchange('bank_account_id')
    def onchange_bank_account_id(self):
        for r in self:
            r.bank_id = False
            r.rib = False
            if r.bank_account_id:
                r.bank_id = r.bank_account_id.bank_id.id
                r.rib = r.bank_account_id.acc_number
