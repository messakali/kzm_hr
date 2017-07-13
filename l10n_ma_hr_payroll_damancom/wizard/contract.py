# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from ..models.variables import *


class hr_contract_close(models.TransientModel):
    _inherit = 'hr.contract.close'

    situation = fields.Selection(SITUATION, string=u'Situation',)

    @api.multi
    def action_generate(self):
        res = super(hr_contract_close, self).action_generate()
        contracts = self.env['hr.contract'].browse(
            self._context.get('active_ids', []))
        for contract in contracts:
            if self.situation:
                domain = [
                    ('employee_id', '=', contract.employee_id.id),
                    ('date', '=', self.date),
                    ('contract_id', '=', contract.id),
                ]
                line = self.env['hr.employee.situation'].search(domain)
                if line:
                    line.name = self.situation
                else:
                    line.create({
                        'name': self.situation,
                        'employee_id': contract.employee_id.id,
                        'contract_id': contract.id,
                        'date': self.date,
                    })
        return res
