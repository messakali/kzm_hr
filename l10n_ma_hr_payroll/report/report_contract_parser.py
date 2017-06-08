# -*- coding: utf-8 -*-

import time
from odoo import models, fields, api, _
from odoo.report import report_sxw
from odoo.osv import osv
from odoo.addons.kzm_base.controllers.tools import convert_txt2amount
from odoo.addons.l10n_ma_hr_payroll.models.variables import *
from odoo.exceptions import Warning



numeral_map = zip(
    (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
    ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
)

def int_to_roman(i):
    result = []
    for integer, numeral in numeral_map:
        count = int(i / integer)
        result.append(numeral * count)
        i -= integer * count
    return ''.join(result)

class contract_parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(contract_parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'int_to_roman': int_to_roman,
            'sp': self._get_space,
                'formuleSalaire': self._get_formule_salaire,
            'text': convert_txt2amount,
            'check': self._check,
            'index': self._get_index,
        })
        self.nbr = 0

    def _get_formule_salaire(self, contract):
        symbol = contract.company_id.main_company_id.currency_id.symbol
        fl = self.localcontext.get('formatLang')
        if contract.based_on == FIXED_DAYS:
            return _("Salaire net de %s %s par mois") % (fl(contract.salary_net_effectif), symbol)
        if contract.based_on == FIXED_HOURS:
            return _("Salaire net de %s %s par mois") % (fl(contract.salary_net_effectif), symbol)
        if contract.based_on in [WORKED_DAYS, ATTENDED_DAYS]:
            return _("Salaire journalier de %s %s par jour") % (fl(contract.salary_by_day), symbol)
        if contract.based_on in [WORKED_HOURS, ATTENDED_HOURS]:
            return _("Salaire horaire de %s %s par heure") % (fl(contract.salary_by_hour), symbol)
        if contract.based_on == TIMESHEET_DAYS:
            return _("Salaire journalier de %s %s par heure basé sur les feuilles de temps") % (fl(contract.salary_by_day), symbol)
        if contract.based_on == TIMESHEET_HOURS:
            return _("Salaire horaire de %s %s par heure basé sur les feuilles de temps") % (fl(contract.salary_by_hour), symbol)

    def _get_space(self):
        return '...........'

    def _get_index(self):
        self.nbr += 1
        return self.nbr

    def _check(self, c):
        root_company = c.company_id.main_company_id
        current_company = c.company_id
        """
        manager id
        job id of manager id
        cnss company
        employee cin
        forme Juridique
        """
        if not root_company.manager_id:
            raise Warning(_('Veuillez configurer le gérant de la société [%s]') % root_company.name)
        if not root_company.forme_juridique_id:
            raise Warning(_('Veuillez configurer la forme juridique de la société [%s]') % root_company.name)
        if not root_company.manager_id.job_id:
            raise Warning(_('Veuillez définir le poste du gérant [%s]') % root_company.manager_id.name)
        if not root_company.cnss:
            raise Warning(_('Veuillez définir le numéro d\'affiliation CNSS de la société [%s]') % root_company.name)
        if not c.employee_id.cin:
            raise Warning(_('Veuillez définir le CIN de l\'employé [%s]') % c.employee_id.name)
        if not current_company.activity:
            raise Warning(_('Veuillez définir l\'activité de la société [%s]') % current_company.name)
        return True





class report_contract(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_contract'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_contract'
    _wrapped_report_class = contract_parser
