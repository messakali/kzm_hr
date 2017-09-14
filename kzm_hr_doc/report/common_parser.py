# -*- coding: utf-8 -*-

import time
from odoo import models, fields, api, _
from odoo.report import report_sxw
from odoo.addons.kzm_base.controllers.tools import convert_txt2amount
from odoo.addons.l10n_ma_hr_payroll.models.dictionnary import transform_domain_to_where_tab

from odoo.exceptions import Warning

from dateutil.relativedelta import relativedelta

import calendar
import math

from datetime import timedelta


class common_parser(report_sxw.rml_parse):

    def __init__(self, name, table, rml=False, parser=False, header=True,
                 store=False):
        super(common_parser, self).__init__(name, table, rml, parser, header, store)
        self.localcontext.update({
            'time': time,
            'math': math,
            'lines': self.get_lines,
            'register_lines': self.get_register_lines,
            'lines_by_type': self.get_lines_by_type,
            'sstr': self.split_string,
            'main_company': self._get_main_company,
            'text': convert_txt2amount,
            'arrondi': self._arrondi,
            'cin_cs': self._get_cin_cs,
            'periods': self.get_periods,
            'headers': self.get_headers,
            'get_holiday': self.get_holiday,
            'get_avance': self.get_avance,
            'get_avantage': self.get_avantage,
            'get_rubrique': self.get_rubrique,
            'get_cotisation_ledger': self.get_cotisation_ledger,
            'structure_reference': self._get_structure_reference,
            'sp': self._get_space,
            'dt': self._get_date_space,
            'date_limit': self._get_date_limit,
            'structure_reference': self._get_structure_reference,
            'vat': self._get_vat,
            'tv': self._get_tv,
        })

    def get_register_lines(self, p):
        department_ids = [x.id for x in p.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([])
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', p.date_from),
            ('date_to', '<=', p.date_to),
            ('company_id', 'in', self.get_companies_ids(p)),
        ]
        if p.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if p.payslip_state != 'all':
            payslip_domain.append(('state', '=', p.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        payslips = self.env['hr.payslip'].browse(payslip_ids)
        registers = self.env['hr.contribution.register'].search_read([],['name'])
        registers = [[x.get('id'), x.get('name'), 0] for x in registers]
        for slip in payslips:
            for line in slip.details_by_salary_rule_category:
                if line.total > 0 and line.register_id:
                    for i, item in enumerate(registers):
                        if item[0] == line.register_id.id:
                            registers[i][2] += line.total
        return registers


    def _get_vat(self, o):
        vat = self._get_main_company(o).vat
        if not vat:
            raise Warning(_('Veuillez configurer l\'identifiant fiscal de la société'))
        return vat.strip().replace(' ', '').rjust(8, ' ')

    def _get_tv(self, o):
        new_value = u''
        for c in self.localcontext.get('formatLang')(o.ir_total_verse):
            if c.isdigit() or c in [',', '.', ';', "'"]:
                new_value += c
        return new_value.rjust(10, ' ')

    def _get_structure_reference(self, o):
        if not self._get_main_company(o).cnss:
            raise Warning(
                _(u'Veuillez définir l\'affiliation CNSS pour la société [%s]') % self._get_main_company(o).name)
        cnss = ''.join(
            [x for x in self._get_main_company(o).cnss if x.isdigit()])
        period = o.date_from[2:4] + o.date_from[5:7]
        ref_cnss, ref_amo = cnss + period + '01', cnss + period + '02'
        ref_cnss += str(int(cnss + period + '01') % 97).rjust(2, '0')
        ref_amo += str(int(cnss + period + '02') % 97).rjust(2, '0')
        return ref_cnss, ref_amo

    def _currency2text(self, currency):
        return "NotImplemented"

    def _get_space(self):
        return '...........'

    def _get_date_space(self):
        return '../../....'

    def _get_date_limit(self, o):
        date = fields.Datetime.from_string(
            o.date_from) + relativedelta(months=1)
        date = date.replace(day=self._get_main_company(o).cnss_day_limit)
        return fields.Datetime.to_string(date)

    def get_periods(self, p):
        tab = []
        date_from = fields.Datetime.from_string(p.date_from)
        date_to = fields.Datetime.from_string(p.date_to)
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

    def _arrondi(self, amount):
        return math.ceil(amount)

    def _get_cin_cs(self, p):
        company = self._get_main_company(p)
        if not company.simpleir_employee_id:
            raise Warning(
                _('Veuillez définir le contribuable pour la société %s') % company.name)
        emp = company.simpleir_employee_id
        res = emp.cin or emp.carte_sejour or '-'
        res = res.replace(' ', '')
        return res

    def _get_main_company(self, p):
        company = p.company_ids and p.company_ids[0] or self.browse(
            self.cr, self.uid, self.uid).company_id
        return company.sudo().main_company_id

    def split_string(self, text, nbr):
        if not text and not isinstance(text, (int, long)):
            text = ' '
        return str(text)[::-1].ljust(nbr, ' ')

    def get_lines(self, p, dict_keys, employees_fields, payslip_fields, contract_type=False, period=False):
        dd = p.date_from
        df = p.date_to
        if period:
            dd = period[0][:10]
            df = period[1][:10]
        department_ids = [x.id for x in p.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([])
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('company_id', 'in', self.get_companies_ids(p)),
        ]
        if contract_type:
            payslip_domain.append(
                ('contract_id.type_id.type', '=', contract_type),)
        if p.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if p.payslip_state != 'all':
            payslip_domain.append(('state', '=', p.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        payslips = self.env['hr.payslip'].browse(payslip_ids)
        employees = list(set([x.employee_id for x in payslips]))
        employees = sorted(employees, key=lambda x: x.otherid)
        tab = []
        for emp in employees:
            emp_payslips = payslips.filtered(
                lambda r: r.employee_id.id == emp.id)
            slip = emp_payslips[-1]
            line = {}
            line['tx'] = {}
            line['employee'] = {}
            line['cumul'] = {}
            line['inputs'] = {}
            line['extra'] = {}
            line['payslip'] = emp_payslips.read(payslip_fields)[0]
            employees_dicts = emp.read(employees_fields)[0]
            if 'marital' in employees_dicts and 'gender' in employees_dicts:
                employees_dict = {'marital':dict(emp.fields_get(allfields=['marital'], context=self.localcontext.copy())['marital']['selection'])[emp.read(employees_fields)[0]['marital']],
                                  'gender':dict(emp.fields_get(allfields=['gender'], context=self.localcontext.copy())['gender']['selection'])[emp.read(employees_fields)[0]['gender']]
                                  }

                employees_dicts.update(employees_dict)
            line['employee'] = employees_dicts
            # for name in employees_fields:
            #     line['employee'][name] = getattr(emp, name)
            line['employee'][
                'address_home_id'] = emp.address_home_id and emp.address_home_id.contact_address.strip().replace('\n', ', ') or ''
            line['employee'][
                'address_id'] = emp.address_id and emp.address_id.contact_address.strip().replace('\n', ', ') or ''
            for code in dict_keys:
                line['cumul'][code] = self.env['hr.dictionnary'].compute_value(
                    code=code,
                    date_start=dd,
                    date_stop=df,
                    employee_id=emp.id,
                    payslip_ids=emp_payslips,
                    department_ids=p.departments_id and department_ids or False,
                    state=p.payslip_state
                )
                dict_id = self.env['hr.salary.rule'].search([('code','=',str(code))])
                if dict_id:
                    line['tx'][code] = self.env['hr.salary.rule'].browse(dict_id).rate_val
                else:
                    line['tx'][code] = ''
            line['extra']['DAYS'] = self.env['hr.dictionnary'].compute_value(
                category_code='GAIN',
                date_start=dd,
                date_stop=df,
                employee_id=emp.id,
                payslip_ids=emp_payslips,
                force_type='quantity',
                based_on='days',
                department_ids=p.departments_id and department_ids or False,
                state=p.payslip_state
            ) + self.env['hr.dictionnary'].compute_value(
                category_code='AUTRE_GAIN',
                date_start=dd,
                date_stop=df,
                employee_id=emp.id,
                payslip_ids=emp_payslips,
                force_type='quantity',
                based_on='days',
                department_ids=p.departments_id and department_ids or False,
                state=p.payslip_state
            )
            line['extra']['HOURS'] = self.env['hr.dictionnary'].compute_value(
                category_code='GAIN',
                date_start=dd,
                date_stop=df,
                employee_id=emp.id,
                payslip_ids=emp_payslips,
                force_type='quantity',
                based_on='hours',
                department_ids=p.departments_id and department_ids or False,
                state=p.payslip_state
            ) + self.env['hr.dictionnary'].compute_value(
                category_code='AUTRE_GAIN',
                date_start=dd,
                date_stop=df,
                employee_id=emp.id,
                payslip_ids=emp_payslips,
                force_type='quantity',
                based_on='hours',
                department_ids=p.departments_id and department_ids or False,
                state=p.payslip_state
            )
            for slip in emp_payslips:
                for input_line in slip.input_line_ids:
                    line['inputs'][input_line.code] = input_line.amount
                line['extra']['TH'] = not slip.contract_id.based_on_days and line[
                    'inputs'].get('SALAIRE_PAR_HEURE', 0) or 0.0
                break
            tab.append(line)
        return tab

    def get_lines_by_type(self, p, dict_keys, employees_fields, payslip_fields):
        return [
            (self.get_lines(p, dict_keys, employees_fields, payslip_fields, contract_type='permanent'),
             u'ETAT CONCERNANT LE PERSONNEL PERMANENET',),
            (self.get_lines(p, dict_keys, employees_fields, payslip_fields, contract_type='occasional'),
             u'ETAT CONCERNANT LE PERSONNEL OCCASIONEL',),
            (self.get_lines(p, dict_keys, employees_fields, payslip_fields, contract_type='trainee'),
             u'ETAT CONCERNANT LES STAGIARES',),
        ]

    def get_companies_ids(self, p):
        if p.company_ids:
            return [x.id for x in p.company_ids]
        else:
            return self.env['res.company'].search([])

    def get_holiday(self, p, period, emp_id, holiday_id):
        dd = period[0][:10]
        df = period[1][:10]
        department_ids = [x.id for x in p.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([])
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('employee_id', '=', emp_id),
            ('company_id', 'in', self.get_companies_ids(p)),
        ]
        if p.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if p.payslip_state != 'all':
            payslip_domain.append(('state', '=', p.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        return self.env['hr.dictionnary'].compute_value(
            code=False,
            date_start=dd,
            date_stop=df,
            employee_id=emp_id,
            payslip_ids=payslip_ids,
            department_ids=p.departments_id and department_ids or False,
            state=p.payslip_state,
            holiday_status_id=holiday_id,
            force_type='quantity',
        )

    def get_rubrique(self, p, period, emp_id, rubrique_id):
        dd = period[0][:10]
        df = period[1][:10]
        department_ids = [x.id for x in p.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([])
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('employee_id', '=', emp_id),
            ('company_id', 'in', self.get_companies_ids(p)),
        ]
        if p.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if p.payslip_state != 'all':
            payslip_domain.append(('state', '=', p.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        return self.env['hr.dictionnary'].compute_value(
            code=False,
            date_start=dd,
            date_stop=df,
            employee_id=emp_id,
            payslip_ids=payslip_ids,
            department_ids=p.departments_id and department_ids or False,
            state=p.payslip_state,
            rubrique_id=rubrique_id,
            force_type='total',
        )

    def get_avance(self, p, period, emp_id, avance_id):
        dd = period[0][:10]
        df = period[1][:10]
        department_ids = [x.id for x in p.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([])
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('employee_id', '=', emp_id),
            ('company_id', 'in', self.get_companies_ids(p)),
        ]
        if p.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if p.payslip_state != 'all':
            payslip_domain.append(('state', '=', p.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        return self.env['hr.dictionnary'].compute_value(
            code=False,
            date_start=dd,
            date_stop=df,
            employee_id=emp_id,
            payslip_ids=payslip_ids,
            department_ids=p.departments_id and department_ids or False,
            state=p.payslip_state,
            avance_id=avance_id,
            force_type='total',
        )

    def get_avantage(self, p, period, emp_id, avantage_id):
        dd = period[0][:10]
        df = period[1][:10]
        department_ids = [x.id for x in p.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([])
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('employee_id', '=', emp_id),
            ('company_id', 'in', self.get_companies_ids(p)),
        ]
        if p.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if p.payslip_state != 'all':
            payslip_domain.append(('state', '=', p.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        return self.env['hr.dictionnary'].compute_value(
            code=False,
            date_start=dd,
            date_stop=df,
            employee_id=emp_id,
            payslip_ids=payslip_ids,
            department_ids=p.departments_id and department_ids or False,
            state=p.payslip_state,
            avantage_id=avantage_id,
            force_type='total',
        )

    def get_cotisation_ledger(self, p, period, emp_id, cotisation_ledger_id, cotisation):
        dd = period[0][:10]
        df = period[1][:10]
        department_ids = [x.id for x in p.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([])
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('employee_id', '=', emp_id),
            ('company_id', 'in', self.get_companies_ids(p)),
        ]
        if p.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if p.payslip_state != 'all':
            payslip_domain.append(('state', '=', p.payslip_state),)
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
            department_ids=p.departments_id and department_ids or False,
            state=p.payslip_state,
            cotisation_ledger_id=cotisation_ledger_id,
            force_type='total',
            category_type=category_type,
        )

    def get_headers(self, p, period):
        dd = period[0][:10]
        df = period[1][:10]
        ctx = self.localcontext.copy()
        ctx.update({'active_test': False, })
        department_ids = [x.id for x in p.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([])
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', dd),
            ('date_to', '<=', df),
            ('company_id', 'in', self.get_companies_ids(p)),
        ]
        if p.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if p.payslip_state != 'all':
            payslip_domain.append(('state', '=', p.payslip_state),)
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
                department_ids=p.departments_id and department_ids or False,
                state=p.payslip_state,
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
                department_ids=p.departments_id and department_ids or False,
                state=p.payslip_state,
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
                department_ids=p.departments_id and department_ids or False,
                state=p.payslip_state,
                avance_id=avance.get('id'),
                force_type='total',
            ):
                avances.append(avance)
        # Cotisations
        cotisation_ledgers = []
        for cotisation_ledger in self.env['hr.cotisation.ledger'].search_read([], ['name','show_on_ledger'], order='sequence asc'):
            if cotisation_ledger.get('show_on_ledger', False) == 'never':
                continue
            if p.cotisation in ['g','sp']:
                if cotisation_ledger.get('show_on_ledger', False) == 'always' or self.env['hr.dictionnary'].compute_value(
                    code=False,
                    date_start=dd,
                    date_stop=df,
                    employee_id=False,
                    payslip_ids=payslip_ids,
                    department_ids=p.departments_id and department_ids or False,
                    state=p.payslip_state,
                    cotisation_ledger_id=cotisation_ledger.get('id'),
                    force_type='total',
                ):
                    cotisation_ledgers.append(cotisation_ledger)
            if p.cotisation == 's':
                if cotisation_ledger.get('show_on_ledger', False) == 'always' or self.env['hr.dictionnary'].compute_value(
                    code=False,
                    date_start=dd,
                    date_stop=df,
                    employee_id=False,
                    payslip_ids=payslip_ids,
                    department_ids=p.departments_id and department_ids or False,
                    state=p.payslip_state,
                    cotisation_ledger_id=cotisation_ledger.get('id'),
                    force_type='total',
                    category_type='rs',
                ):
                    cotisation_ledgers.append(cotisation_ledger)
            if p.cotisation == 'p':
                if cotisation_ledger.get('show_on_ledger', False) == 'always' or self.env['hr.dictionnary'].compute_value(
                    code=False,
                    date_start=dd,
                    date_stop=df,
                    employee_id=False,
                    payslip_ids=payslip_ids,
                    department_ids=p.departments_id and department_ids or False,
                    state=p.payslip_state,
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
                department_ids=p.departments_id and department_ids or False,
                state=p.payslip_state,
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


class report_anciennete(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_anciennete'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_anciennete'
    _wrapped_report_class = common_parser


class report_cimr(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_cimr_declaration'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_cimr_declaration'
    _wrapped_report_class = common_parser


class report_mutuelle(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_mutuelle_declaration'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_mutuelle_declaration'
    _wrapped_report_class = common_parser


class report_declaration_cnss(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_cnss_declaration'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_cnss_declaration'
    _wrapped_report_class = common_parser


class report_declaration_cnss_versement(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_cnss_declaration_versement'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_cnss_declaration_versement'
    _wrapped_report_class = common_parser


class report_cs(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_cs_declaration'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_cs_declaration'
    _wrapped_report_class = common_parser


class report_cs_versement(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_cs_declaration_versement'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_cs_declaration_versement'
    _wrapped_report_class = common_parser


class report_ir(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_ir_declaration'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_ir_declaration'
    _wrapped_report_class = common_parser


class report_ir_versement(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_ir_declaration_versement'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_ir_declaration_versement'
    _wrapped_report_class = common_parser


class report_declaration_salary(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_salary_declaration'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_salary_declaration'
    _wrapped_report_class = common_parser


class report_salary_ledger(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_salary_ledger'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_salary_ledger'
    _wrapped_report_class = common_parser


class report_paye_journal(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_paye_journal'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_paye_journal'
    _wrapped_report_class = common_parser


class report_register_standard(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_register'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_register'
    _wrapped_report_class = common_parser


class report_cotisation_standard(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_cotisation'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_cotisation'
    _wrapped_report_class = common_parser
