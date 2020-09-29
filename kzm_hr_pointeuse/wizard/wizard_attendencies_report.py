# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import datetime
from odoo.exceptions import ValidationError


class Wizard_Attendencies_Reports(models.TransientModel):
    _name = 'zk_attendance.wizardattendenciesreports'


    def load_to_hr_attendance(self):
        attendancies = self.env['zk_attendance.attendance'].search([('action', '=', 'sign_in')])
        for r in attendancies:
            # TODO
            if not r.employee_id.contract_id:
                continue
            next_add_ids = self.env['zk_attendance.attendance'].search(
                [('employee_id', '=', r.employee_id.id), ('date', '>', str(r.date)),
                 ('action', '=', 'sign_out')], limit=1, order='date ASC')
            # print(next_add_ids,next_add_ids.employee_id.name_related ,next_add_ids.action)
            # in case of no next, continue
            if not next_add_ids:
                continue

            alreadyregistred = self.env['hr.attendance'].search(
                [('employee_id', '=', r.employee_id.id),
                 ('check_in', '=', r.date),
                 ('check_out', '=', next_add_ids.date)]
            )
            if not alreadyregistred and r.employee_id.contract_id :
                self.env['hr.attendance'].create({
                    'employee_id': r.employee_id.id,
                    'check_in': r.date,
                    'check_out': next_add_ids.date,
                    'check_in_machine': r.machine_id.name,
                    'check_out_machine': next_add_ids.machine_id.name,
                    'company_id': r.company_id.id,
                    'pointeuse_id': (r.machine_id and r.machine_id.id) or (next_add_ids.machine_id and next_add_ids.machine_id.id)
                })

            r.unlink()
            next_add_ids.unlink()
