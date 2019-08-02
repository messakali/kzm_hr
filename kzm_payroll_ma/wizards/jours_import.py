# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import except_orm, Warning, RedirectWarning
import base64
import xlrd


class Wizard_Jours(models.TransientModel):
    _name = 'payroll.jours.import.wizard'

    file_id = fields.Binary(string="Fichier",required=True)

    @api.multi
    def action_add_jours(self):
        emp_obj = self.env['hr.employee']
        bulletin_obj = self.env['hr.payroll_ma.bulletin']
        try:
            file_content_decoded = base64.decodestring(self.file_id)
        except IOError:
            raise except_orm('Error !', 'Merci de donner un chemin valide!')

        wb = xlrd.open_workbook(file_contents=file_content_decoded)
        for sheet in wb.sheets():
            for row in range(sheet.nrows):
                mat = sheet.cell(row, 0).value
                j = sheet.cell(row, 1).value

                days = int(j)
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

                        bulletin.write({'working_days':int(d)})
        return  True
