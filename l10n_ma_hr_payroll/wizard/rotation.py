# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
class hr_employee_current_wizard(models.TransientModel):
    _name = 'hr.employee.current.wizard'
    _description = 'Current employees'

    date = fields.Date(string=u'Date', default=lambda self: fields.Date.today() , required=True,    )

    @api.multi
    def action_open_window(self):
        view_id = self.env.ref('l10n_ma_hr_payroll.view_res_company_nbr_employees_tree').id
        ctx =dict(self.env.context, date=self.date)
        return {
            'view_mode': 'tree',
            'view_id': view_id,
            'view_type': 'tree',
            'res_model': 'res.company',
            'type': 'ir.actions.act_window',
            'domain': "[]",
            'context': ctx,
        }
