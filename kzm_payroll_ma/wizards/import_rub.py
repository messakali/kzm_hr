# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import except_orm, Warning, RedirectWarning
import base64
import xlrd


class WizardRub(models.TransientModel):
    _name = 'payroll.rub.import.wizard'
    _description = 'Payroll Rub Import Wizard'

    file_id = fields.Binary(string="Fichiers",required=True)
    rub_id = fields.Many2one(comodel_name='hr.payroll_ma.rubrique',string='Rubrique:', company_dependent=True, required=True)


    def action_add_rub(self):
        emp_obj = self.env['hr.employee']
        paie_obj = self.env['hr.payroll_ma']
        contract_obj = self.env['hr.contract']
        try:
            file_content_decoded = base64.decodestring(self.file_id)
        except IOError:
            raise except_orm('Error !', 'Merci de donner un chemin valide!')

        wb = xlrd.open_workbook(file_contents=file_content_decoded)
        for sheet in wb.sheets():
            for row in range(sheet.nrows):
                mat = sheet.cell(row, 0).value
                amount = sheet.cell(row, 1).value
                emp_id = emp_obj.search([('matricule','=',mat)])
                if not emp_id:
                    raise except_orm('Error !', 'Erreur marticule: '+str(mat)+'!')
                else:
                    paie =paie_obj.browse(self.env.context['active_id'])
                    data={
                        'rubrique_id' : self.rub_id.id,
                        'id_contract': emp_id.contract_id.id,
                        'montant' : amount,
                        'taux' : self.rub_id.pourcentage or 1,
                        'period_id': paie.period_id.id,
                        'permanent' : False,
                        'date_start': paie.period_id.date_start,
                        'date_stop': paie.period_id.date_end,
                    }
                    emp_id.contract_id.rubrique_ids.create(data)
        return True
