# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import except_orm, Warning, RedirectWarning
import base64


class Wizard_Hours(models.TransientModel):
    _name = 'payroll.hours.import.wizard'

    file_id = fields.Binary(string="Fichier",required=True)

    @api.multi
    def action_add_hours(self):
        emp_obj = self.env['hr.employee']
        bulletin_obj = self.env['hr.payroll_ma.bulletin']
        try:
            file_content_decoded = base64.decodestring(self.file_id)
        except IOError:
            raise except_orm('Error !', 'Merci de donner un chemin valide!')
        data = file_content_decoded.split('\n')
        for line in data[1:]:
           line_data = line.split(',')
           if len(line_data)>1:
                mat = line_data[0].replace('"', '').strip()
                hours = line_data[1].replace('"', '').strip()
                days = int(hours) * 26/192
                d=0
                if days > 26:
                    d=26
                else:
                    d=days
                emp_id = emp_obj.search([('matricule','=',mat)])
                if not emp_id:
                    raise except_orm('Error !', 'Erreur marticule: '+str(mat)+'!')
                else:
                    bulletin =bulletin_obj.search([('id_payroll_ma','=',self.env.context['active_id']),('employee_id','=',emp_id.id)])
                    if bulletin:
                        bulletin.write({'normal_hours':int(hours)})
                        bulletin.write({'working_days':int(d)})
        return True
