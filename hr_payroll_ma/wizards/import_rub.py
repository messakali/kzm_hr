# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import except_orm, Warning, RedirectWarning
import base64


class WizardRub(models.TransientModel):
    _name = 'payroll.rub.import.wizard'

    file_id = fields.Binary(string="Fichiers",required=True)
    rub_id = fields.Many2one(comodel_name='hr.payroll_ma.rubrique',string='Rubrique:',required=True)

    @api.multi
    def action_add_rub(self):
        emp_obj = self.env['hr.employee']
        paie_obj = self.env['hr.payroll_ma']
        contract_obj = self.env['hr.contract']
        try:
            file_content_decoded = base64.decodestring(self.file_id)
        except IOError:
            raise except_orm('Error !', 'Merci de donner un chemin valide!')
        data = file_content_decoded.split('\n')
        for line in data[1:]:
           line_data = line.split(',')
           if len(line_data)>1:
                mat = line_data[0].replace('"', '').strip()
                amount = line_data[1].replace('"', '').strip()
                emp_id = emp_obj.search([('matricule','=',mat)])
                if not emp_id:
                    raise except_orm('Error !', 'Erreur marticule: '+str(mat)+'!')
                else:
                    paie =paie_obj.browse(self.env.context['active_id'])
                    data={
                        'rubrique_id' : self.rub_id.id,
                        'id_contract': emp_id.contract_id.id,
                        'montant' : amount,
                        'taux' : 1,
                        'period_id': paie.period_id.id,
                        'permanent' : False,
                        'date_start': paie.period_id.date_start,
                        'date_stop': paie.period_id.date_stop,
                    }
                    emp_id.contract_id.rubrique_ids.create(data)
        return True
