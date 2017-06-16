# -*- coding: utf-8 -*-

import time
from . import abstract_report_xlsx
from odoo import models, fields, api, _
from odoo.report import report_sxw

class slip_report(abstract_report_xlsx.AbstractReportXslx):

    def __init__(self, name, table, rml=False, parser=False, header=True,
                 store=False):
        res = super(slip_report, self).__init__(
            name, table, rml, parser, header, store)
        
        self.localcontext= {
            'time': time,
            'lines': self.get_lines,
            'cumul': self.get_cumul,
            'current': self.get_current,
            'root_company': self.get_root_company,
        }

    def get_root_company(self, company):
        while company.parent_id:
            company = company.parent_id
        return company

    def get_lines(self, p, group, patronal, group_rubrique, rename={}, includes=[], excludes=[]):
        tab, cumul, special = p.get_slip_report_items(group, patronal, group_rubrique, rename, includes, excludes)
        res = {
            'lines': tab,
            'cumul': cumul,
            'special': special,
        }
        return res

    def get_cumul(self, p, code):
        return self.env['hr.dictionnary'].compute_value(
            code=code,
            year_of_date=p.date_from,
            date_start=False,
            date_stop=p.date_to,
            employee_id=p.employee_id.id,
            company_id=p.company_id.id,
        )

    def get_current(self, p, code):
        return self.env['hr.dictionnary'].compute_value(
            code=code,
            year_of_date=p.date_from,
            date_start=p.date_from,
            date_stop=p.date_to,
            employee_id=p.employee_id.id,
            contract_id=False,
            company_id=p.company_id.id,
        )

    
slip_report(
    'report.l10n_ma_hr_payroll.report_slip',
    'report_slip',
    parser=report_sxw.rml_parse
)

# class report_slip_standard(models.AbstractModel):
#     _name = 'report.l10n_ma_hr_payroll.report_slip'
#     _inherit = 'report.abstract_report'
#     _template = 'l10n_ma_hr_payroll.report_slip'
#     _wrapped_report_class = slip_report


class report_slip_simple(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_slip_simple'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_slip_simple'
    _wrapped_report_class = slip_report


class report_slip_patronal(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_slip_patronal'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_slip_patronal'
    _wrapped_report_class = slip_report

class report_slip_ir_brut(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_slip_ir_brut'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_slip_ir_brut'
    _wrapped_report_class = slip_report
