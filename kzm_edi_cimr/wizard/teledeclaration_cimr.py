# -*- coding: utf-8 -*-

from odoo import api, fields, models
import base64
import datetime


class TeledeclarationCimr(models.TransientModel):
    _name = 'teledeclaration.cimr'

    file_export = fields.Binary(string=u'Fichier CIMR', readonly=True)
    name = fields.Char('Filename', readonly=True)
    state = fields.Selection(selection=(('choose', 'choose'), ('get', 'get')), default='choose')

    @api.multi
    def generate(self):
        rapport_cimr_id = self._context.get('active_id')
        rapport_cimr = self.env['rapport.cimr'].browse(rapport_cimr_id)
        for rec in self:
            company = rapport_cimr.company_id
            output = ''
            for line in rapport_cimr.rep_cimr_line_ids:
                birthday_date = datetime.datetime.strptime(line.employee_id.birthday, '%Y-%m-%d').strftime('%d-%m-%Y')
                date_in = datetime.datetime.strptime(line.employee_id.date, '%Y-%m-%d').strftime('%d-%m-%Y')
                contract_id = self.env['hr.contract'].search([('employee_id', '=', line.employee_id.id)])
                country_ma = self.env.ref('base.ma')
                nationality = 'M'
                if line.employee_id.country_id.id != country_ma.id:
                    nationality = 'A'
                if line.employee_id.gender == 'male':
                    gender = 'M'
                if line.employee_id.gender == 'female':
                    gender = 'F'
                if line.employee_id.marital == 'single':
                    marital = 'C'
                if line.employee_id.marital == 'married':
                    marital = 'M'
                if line.employee_id.marital == 'widower':
                    marital = 'V'
                if line.employee_id.marital == 'divorced':
                    marital = 'D'
                if line.employee_id.cimr:
                    cimr = line.employee_id.cimr.ljust(9, '0')
                else:
                    cimr = ''.ljust(9, '0')

                if line.employee_id.cin:
                    cin = str(line.employee_id.cin).ljust(10, '0')
                else:
                    cin = '0000000000'
                if line.employee_id.ssnid:
                    cnss = str(line.employee_id.ssnid)
                else:
                    cnss = '0000000000'

                if contract_id.state in ('pending', 'open'):
                    code = '2'
                    date_fin = '00000000'
                else:
                    code = '7'
                    date_fin = fields.Datetime.from_string(contract_id.date_end).strftime('%d-%m-%Y')
                    date_fin = str(date_fin).replace('-', '')

                nom_complet = (line.employee_id.name.upper()).replace(' ', '') + '' + (line.employee_id.prenom.upper()).replace(' ', '')

                l = str(code) + str(company.cimr) + str(company.cimr_category)[:2].rjust(2, '0') + str(cimr) \
                    + str(line.taux_emp).replace('.', '').rjust(3, '0').ljust(4, '0')\
                    + str(nom_complet[:20].ljust(20, '0')) + str(line.employee_id.matricule.ljust(6, '0'))\
                    + str(gender) + str(nationality) + str(date_in).replace('-', '').ljust(8, '0') \
                    + str(birthday_date).replace('-', '').ljust(8, '0') + str(marital) \
                    + str(line.employee_id.children)[:1] + str(line.base_calcul).replace('.', '').rjust(10,'0')\
                    + str(date_fin) + str(cin) + str(cnss) + '00000000000000' + '00000000000000000000000000000000000' + str(rapport_cimr.trimestre) + str(rapport_cimr.annee)
                output += l + '\n'
            out = base64.b64encode(bytes(output, 'utf-8'))
            rec.state = 'get'
            rec.file_export = out
            rec.name = 'cimr.txt'
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'teledeclaration.cimr',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': rec.id,
                'views': [(False, 'form')],
                'target': 'new',
            }
