# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime,timedelta
from odoo.exceptions import ValidationError


class Wizard_Attendencies_Reports(models.TransientModel):
    _name = 'zk_attendance.wizardattendenciesreports'
    _description = 'zk_attendance.wizardattendenciesreports'

    date = fields.Date("Date", required=True)


    def load_to_hr_attendance(self):
        date_min = fields.Datetime.to_string(fields.Datetime.from_string(self.date))
        date_max = fields.Datetime.to_string(fields.Datetime.from_string(self.date) + timedelta(days=1))
        attendancies = self.sudo().env['zk_attendance.attendance'].search([
            ('action', '=', 'sign_in'),
            ('company_id', '=', self.env.company.id),
            ('date', '<', date_max),
            ('date', '>=', date_min),
            ])
        t_remove = self.sudo().env['zk_attendance.attendance']
        N, M = 0, 0
        for r in attendancies:

            N+= 1
            r_company_id = r.sudo().company_id.id
            r_employee_id = r.sudo().employee_id.id
            # TODO
            if not r.sudo().employee_id:
                continue

            next_add_ids = self.sudo().env['zk_attendance.attendance'].search(
                [('employee_id', '=', r_employee_id), 
                 ('date', '>', str(r.date)),
                 ('date', '<', date_max),
                 ('date', '>=', date_min),
                 ('action', '=', 'sign_out'), 
                 ('company_id','=', r_company_id)], limit=1, order='date ASC')
            # print(next_add_ids,next_add_ids.employee_id.name ,next_add_ids.action)
            # in case of no next, continue

            if not next_add_ids or len(next_add_ids) < 1:
                continue

            if not r.sudo().employee_id.contract_id:
                raise ValidationError(" L'employée %s / %s n'a pas de contrat actif."%(
                    r.sudo().employee_id and r.sudo().employee_id.name, r.matricule))
                

            # IF check in and company and employee => ignore create
            alreadyregistred = self.env['hr.attendance'].search(
                [('employee_id', '=', r_employee_id),
                 ('check_in', '=', r.date),
                 #('check_out', '=', next_add_ids.date),
                 ('company_id','=', r_company_id),
                 ]
            )

            if not alreadyregistred and r.sudo().employee_id.contract_id :
                M += 1
                self.env['hr.attendance'].create({
                    'employee_id': r_employee_id,
                    'check_in': r.date,
                    'check_out': next_add_ids.date,
                    'check_in_machine': r.machine_id.name,
                    'check_out_machine': next_add_ids.machine_id.name,
                    'company_id': r_company_id,
                    'pointeuse_id': (r.machine_id and r.machine_id.id) or (next_add_ids.machine_id and next_add_ids.machine_id.id)
                })

            t_remove |= r + next_add_ids
            #print(t_remove)
        print("====N", M,'/',N)
        t_remove.unlink()
            
