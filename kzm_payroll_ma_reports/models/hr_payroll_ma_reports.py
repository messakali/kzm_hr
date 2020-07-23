# -*- coding: utf-8 -*-
from pprint import pprint

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayrollMaReports(models.Model):
    _inherit = "hr.payroll_ma"

    def get_rubriques_departments(self):

        dict_departements = {
        }
        for rec in self:

            #     lines = self.env['hr.payroll_ma.bulletin.line'].search([
            #         ('hr_payroll_ma_id','=',rec.id),('department_id','=',rec.)
            #     ])
            for bul in rec.bulletin_line_ids:
                for l in bul.salary_line_ids:
                    rub = l.name
                    dep = bul.employee_id.department_id
                    mon = l.subtotal_employee
                    if dict_departements.get(dep.name, False):
                        if dict_departements[dep.name].get(rub, False):
                            dict_departements[dep.name][rub] += mon
                        else:
                            dict_departements[dep.name][rub] = mon
                    else:
                        dict_departements[dep.name] = {}
                        dict_departements[dep.name][rub] = mon

        departement = []
        rubrique = []
        for v in dict_departements:
            departement.append(v)
            for d in dict_departements[v]:
                rubrique.append(d)
        rubrique = list(set(rubrique))
        departement = list(set(departement))

        # pprint(dict_departements)
        return dict_departements, rubrique, departement

    def calcul_total(self, rubrique):
        total = 0
        dict_rubriques = {
        }
        for rec in self:
            for bul in rec.bulletin_line_ids:
                for l in bul.salary_line_ids:
                    rub = l.name
                    dep = bul.employee_id.department_id
                    mon = l.subtotal_employee
                    if dict_rubriques.get(rub, False):
                        dict_rubriques[rub] += mon
                        # mon+=mon
                    else:
                        dict_rubriques[rub] = {}
                        dict_rubriques[rub] = mon

        pprint(dict_rubriques[rubrique])

        return dict_rubriques[rubrique]

    def split(self, arr, size):
        arrs = []
        while len(arr) > size:
            pice = arr[:size]
            arrs.append(pice)
            arr = arr[size:]
        arrs.append(arr)
        return arrs

    # def get_company_banks(self):
    #     dict_banks = {
    #     }
    #     pprint("--------------")
    #     for rec in self:
    #         for bul in rec.bulletin_line_ids:
    #             company_virement_bank = bul.employee_id.company_virement_bank_id
    #             employee_id = bul.employee_id
    #             l = []
    #             if not company_virement_bank :
    #                 dict_banks['Aucune banque'] = employee_id.name
    #             else:
    #                 if dict_banks.get(company_virement_bank, False):
    #                     dict_banks[company_virement_bank.name] += employee_id.name
    #                 else:
    #                     dict_banks[company_virement_bank.name] = {}
    #                     dict_banks[company_virement_bank.name] = employee_id.name
    #         pprint(dict_banks)
    #
    #     return dict_banks

    def get_company_banks(self):
        dict_banks = {
        }
        pprint("--------------")
        for rec in self:
            banks = []
            for bul in rec.bulletin_line_ids:
                company_virement_bank = bul.employee_id.company_virement_bank_id
                banks.append(company_virement_bank)
                data = {
                    'employee': bul.employee_id.name,
                    'banque': bul.employee_id.bank.name,
                    'n_compte': bul.employee_id.compte,
                    'montant': bul.salaire_net_a_payer,
                }
                # if not company_virement_bank :
                #     dict_banks['Aucune banque'].append(data)
                # else:
                if dict_banks.get(company_virement_bank, False):
                    dict_banks[company_virement_bank.name].append(data)
                else:
                    dict_banks[company_virement_bank.name] = []
                    dict_banks[company_virement_bank.name].append(data)
            banks = list(set(banks))
        pprint(dict_banks)
        # pprint(banks)
        pprint(sorted(banks, key = lambda r: r.id))
        # for v in dict_banks:
        #     banks.append(v)
        #     banks = list(set(banks))
        #     pprint(banks) <
        return dict_banks, sorted(banks, key = lambda r: r.id)
