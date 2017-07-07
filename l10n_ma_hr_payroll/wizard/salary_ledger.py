# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import time

import calendar
from datetime import timedelta

import math

class hr_salary_ledger(models.TransientModel):
    _name = 'hr.salary.ledger'

    fiscalyear_id = fields.Many2one(
        'date.range', string=u'Année', required=False, domain=[('type_id.fiscal_year', '=', True),('active', '=', True)])
    period_id = fields.Many2one(
        'date.range', string=u'Période', required=False)
    date_from = fields.Date(string=u'Date début',  required=False)
    date_to = fields.Date(string=u'Date fin',  required=False)

    departments_id = fields.Many2many(
        'hr.department', 'salary_ledger_department_rel', 'declaration_id', 'department_id', string=u'Limiter les départements', )

    payslip_state = fields.Selection([
        ('all', 'All'),
        ('done', 'Terminé'),
    ], string=u'État', required=True, default='done')

    company_child = fields.Boolean(string=u'Filiales', default=False,)
    company_parent = fields.Boolean(string=u'Sociétés mères', default=False,)

    cotisation = fields.Selection([
        ('g', 'Groupe'),
        ('s', 'Salariale'),
        ('p', 'Patronale'),
        ('sp', 'Salariale et Patronale'),
    ], string=u'Cotisations',  required=True, default='sp',)

    @api.onchange('company_child', 'company_parent')
    def _onchange_company_child_parent(self):
        ids = []
        if self.company_child:
            companies = self.env['res.company'].search(
                [('parent_id', '!=', False)])
            if companies:
                ids += companies.mapped('id')
        if self.company_parent:
            companies = self.env['res.company'].search(
                [('parent_id', '=', False)])
            if companies:
                ids += companies.mapped('id')
        if not self.company_child and not self.company_parent:
            ids = self.env['res.company'].search([]).mapped('id')
        self.company_ids = self.env['res.company'].browse(ids)

    company_ids = fields.Many2many(
        'res.company', string=u'Sociétés',  required=True, default=lambda self: self.env['res.company'].search([]),)

    @api.onchange('fiscalyear_id')
    def _onchange_fiscalyear_id(self):
        self.period_id = False
        self.date_start = False
        self.date_end = False
        if self.fiscalyear_id:
            period_objs = self.env['date.range'].search(['&', ('date_start', '>=', self.fiscalyear_id.date_start), ('date_start', '<=', self.fiscalyear_id.date_end)])
#             date_start = [p.date_start for p in period_objs]
#             if date_start:
#                 self.date_start = min(date_start)
#             date_end = [p.date_end for p in period_objs]
#             if date_end:
#                 self.date_end = max(date_end)
            self.date_from = self.fiscalyear_id.date_start
            self.date_to = self.fiscalyear_id.date_end
            period_ids = [
                x.id for x in period_objs if x.active == True and x.type_id.fiscal_year == False]
#             print "period_ids    : ",period_ids
            return {
                'domain': {
                    'period_id': [('id', 'in', period_ids)]
                }
            }

    @api.onchange('period_id')
    def _onchange_period_id(self):
        self.date_from = False
        self.date_to = False
        if self.period_id:
            self.date_from = self.period_id.date_start
            self.date_to = self.period_id.date_end

    @api.multi
    def action_print(self):
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_salary_ledger')
    
    def get_periods(self):
        tab = []
        date_from = fields.Datetime.from_string(self.date_from)
        date_to = fields.Datetime.from_string(self.date_to)
        while date_from < date_to:
            month_range = calendar.monthrange(date_from.year, date_from.month)
            if date_from.year == date_to.year and date_from.month == \
                    date_to.month and month_range[1] > date_to.day:
                tab.append((date_from, date_to),)
                break
            dd = date_from.replace(day=date_from.day)
            df = date_from.replace(day=month_range[1])
            tab.append((dd, df),)
            date_from = df + timedelta(days=1)
        return [(fields.Datetime.to_string(x[0]), fields.Datetime.to_string(x[1]))
                for x in tab]

    def get_headers(self, period):
        dd = period[0][:10]
        df = period[1][:10]
        ctx = self._context.copy()
        ctx.update({'active_test': False, })
        department_ids = [x.id for x in self.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([]).ids
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('company_id', 'in', self.env['hr.common.report'].get_companies_ids(self)),
        ]
        if self.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if self.payslip_state != 'all':
            payslip_domain.append(('state', '=', self.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        # Rubriques
        rubriques = []
        for rubrique in self.env['hr.rubrique'].search_read([], ['name','show_on_ledger'], order='sequence asc'):
            if rubrique.get('show_on_ledger', False) == 'never':
                continue
            if rubrique.get('show_on_ledger', False) == 'always' or self.env['hr.dictionnary'].compute_value(
                code=False,
                date_start=dd,
                date_stop=df,
                employee_id=False,
                payslip_ids=payslip_ids,
                department_ids=self.departments_id and department_ids or False,
                state=self.payslip_state,
                rubrique_id=rubrique.get('id'),
                force_type='total',
            ):
                rubriques.append(rubrique)
        # Avantages
        avantages = []
        for avantage in self.env['hr.avantage'].search_read([], ['name','show_on_ledger'], order='sequence asc'):
            if avantage.get('show_on_ledger', False) == 'never':
                continue
            if avantage.get('show_on_ledger', False) == 'always' or self.env['hr.dictionnary'].compute_value(
                code=False,
                date_start=dd,
                date_stop=df,
                employee_id=False,
                payslip_ids=payslip_ids,
                department_ids=self.departments_id and department_ids or False,
                state=self.payslip_state,
                avantage_id=avantage.get('id'),
                force_type='total',
            ):
                avantages.append(avantage)
        # Avances
        avances = []
        for avance in self.env['hr.avance'].search_read([], ['name','show_on_ledger'], order='sequence asc'):
            if avance.get('show_on_ledger', False) == 'never':
                continue
            if avance.get('show_on_ledger', False) == 'always' or self.env['hr.dictionnary'].compute_value(
                code=False,
                date_start=dd,
                date_stop=df,
                employee_id=False,
                payslip_ids=payslip_ids,
                department_ids=self.departments_id and department_ids or False,
                state=self.payslip_state,
                avance_id=avance.get('id'),
                force_type='total',
            ):
                avances.append(avance)
        # Cotisations
        cotisation_ledgers = []
        for cotisation_ledger in self.env['hr.cotisation.ledger'].search_read([], ['name','show_on_ledger'], order='sequence asc'):
            if cotisation_ledger.get('show_on_ledger', False) == 'never':
                continue
            if self.cotisation in ['g','sp']:
                if cotisation_ledger.get('show_on_ledger', False) == 'always' or self.env['hr.dictionnary'].compute_value(
                    code=False,
                    date_start=dd,
                    date_stop=df,
                    employee_id=False,
                    payslip_ids=payslip_ids,
                    department_ids=self.departments_id and department_ids or False,
                    state=self.payslip_state,
                    cotisation_ledger_id=cotisation_ledger.get('id'),
                    force_type='total',
                ):
                    cotisation_ledgers.append(cotisation_ledger)
            if self.cotisation == 's':
                if cotisation_ledger.get('show_on_ledger', False) == 'always' or self.env['hr.dictionnary'].compute_value(
                    code=False,
                    date_start=dd,
                    date_stop=df,
                    employee_id=False,
                    payslip_ids=payslip_ids,
                    department_ids=self.departments_id and department_ids or False,
                    state=self.payslip_state,
                    cotisation_ledger_id=cotisation_ledger.get('id'),
                    force_type='total',
                    category_type='rs',
                ):
                    cotisation_ledgers.append(cotisation_ledger)
            if self.cotisation == 'p':
                if cotisation_ledger.get('show_on_ledger', False) == 'always' or self.env['hr.dictionnary'].compute_value(
                    code=False,
                    date_start=dd,
                    date_stop=df,
                    employee_id=False,
                    payslip_ids=payslip_ids,
                    department_ids=self.departments_id and department_ids or False,
                    state=self.payslip_state,
                    cotisation_ledger_id=cotisation_ledger.get('id'),
                    force_type='total',
                    category_type='rp',
                ):
                    cotisation_ledgers.append(cotisation_ledger)
        # Status
        holidays = []
        for holiday in self.env['hr.holidays.status'].search_read([('is_hs','=',True)], ['name','show_on_ledger'], order='sequence asc'):
            if holiday.get('show_on_ledger', False) == 'never':
                continue
            if holiday.get('show_on_ledger', False) == 'always' or self.env['hr.dictionnary'].compute_value(
                code=False,
                date_start=dd,
                date_stop=df,
                employee_id=False,
                payslip_ids=payslip_ids,
                department_ids=self.departments_id and department_ids or False,
                state=self.payslip_state,
                holiday_status_id=holiday.get('id'),
                force_type='quantity',
            ):
                holidays.append(holiday)
        return {
            'rubriques': rubriques,
            'avantages': avantages,
            'avances': avances,
            'cotisation_ledgers': cotisation_ledgers,
            'holidays': holidays,
        }
        
    def get_lines(self, dict_keys, employees_fields, payslip_fields, contract_type=False, period=False):
        return self.env['hr.common.report'].get_lines(dict_keys, employees_fields, payslip_fields, contract_type, period)
    
    def math(self,var):
        return math.ceil(var)
    
    def get_holiday(self, period, emp_id, holiday_id):
        dd = period[0][:10]
        df = period[1][:10]
        department_ids = [x.id for x in self.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([]).ids
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('employee_id', '=', emp_id),
            ('company_id', 'in', self.get_companies_ids(self)),
        ]
        if self.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if self.payslip_state != 'all':
            payslip_domain.append(('state', '=', self.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        return self.env['hr.dictionnary'].compute_value(
            code=False,
            date_start=dd,
            date_stop=df,
            employee_id=emp_id,
            payslip_ids=payslip_ids,
            department_ids=self.departments_id and department_ids or False,
            state=self.payslip_state,
            holiday_status_id=holiday_id,
            force_type='quantity',
        )

    def get_rubrique(self, period, emp_id, rubrique_id):
        dd = period[0][:10]
        df = period[1][:10]
        department_ids = [x.id for x in self.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([]).ids
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('employee_id', '=', emp_id),
            ('company_id', 'in', self.get_companies_ids(self)),
        ]
        if self.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if self.payslip_state != 'all':
            payslip_domain.append(('state', '=', self.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        return self.env['hr.dictionnary'].compute_value(
            code=False,
            date_start=dd,
            date_stop=df,
            employee_id=emp_id,
            payslip_ids=payslip_ids,
            department_ids=self.departments_id and department_ids or False,
            state=self.payslip_state,
            rubrique_id=rubrique_id,
            force_type='total',
        )

    def get_avance(self, period, emp_id, avance_id):
        dd = period[0][:10]
        df = period[1][:10]
        department_ids = [x.id for x in self.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([]).ids
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('employee_id', '=', emp_id),
            ('company_id', 'in', self.get_companies_ids(self)),
        ]
        if self.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if self.payslip_state != 'all':
            payslip_domain.append(('state', '=', self.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        return self.env['hr.dictionnary'].compute_value(
            code=False,
            date_start=dd,
            date_stop=df,
            employee_id=emp_id,
            payslip_ids=payslip_ids,
            department_ids=self.departments_id and department_ids or False,
            state=self.payslip_state,
            avance_id=avance_id,
            force_type='total',
        )

    def get_avantage(self, period, emp_id, avantage_id):
        dd = period[0][:10]
        df = period[1][:10]
        department_ids = [x.id for x in self.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([]).ids
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('employee_id', '=', emp_id),
            ('company_id', 'in', self.get_companies_ids(self)),
        ]
        if self.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if self.payslip_state != 'all':
            payslip_domain.append(('state', '=', self.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        return self.env['hr.dictionnary'].compute_value(
            code=False,
            date_start=dd,
            date_stop=df,
            employee_id=emp_id,
            payslip_ids=payslip_ids,
            department_ids=self.departments_id and department_ids or False,
            state=self.payslip_state,
            avantage_id=avantage_id,
            force_type='total',
        )

    def get_cotisation_ledger(self, period, emp_id, cotisation_ledger_id, cotisation):
        dd = period[0][:10]
        df = period[1][:10]
        department_ids = [x.id for x in self.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([]).ids
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('employee_id', '=', emp_id),
            ('company_id', 'in', self.get_companies_ids(self)),
        ]
        if self.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if self.payslip_state != 'all':
            payslip_domain.append(('state', '=', self.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        category_type = False
        if cotisation=='p':
            category_type='rp'
        if cotisation=='s':
            category_type='rs'
        return self.env['hr.dictionnary'].compute_value(
            date_start=dd,
            date_stop=df,
            employee_id=emp_id,
            payslip_ids=payslip_ids,
            department_ids=self.departments_id and department_ids or False,
            state=self.payslip_state,
            cotisation_ledger_id=cotisation_ledger_id,
            force_type='total',
            category_type=category_type,
        )