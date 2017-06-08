# -*- coding: utf-8 -*-

import time
from odoo import models, fields, api, _
from odoo.report import report_sxw
from odoo.addons.kzm_base.controllers.tools import convert_txt2amount
from odoo.exceptions import Warning

class voucher_order(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(voucher_order, self).__init__(
            cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'lines': self.get_lines,
            'text': convert_txt2amount,
            'formula': self._get_formula,
        })


    def _get_formula(self, i, fr=True):
        if fr:
            return '=CONCATENER("3002000000000000000000000000000000000000000MAD2";REPT(0;16-NBCAR(F{var}));F{var};A{var};A{var};REPT(" ";21);"0001";REPT(" ";32);"1";B{var};REPT(" ";35-NBCAR(B{var}));C{var};REPT(" ";35-NBCAR(C{var}));D{var};E{var};A{var})'.format(var=i + 2)
        return '=CONCATENATE("3002000000000000000000000000000000000000000MAD2";REPT(0;16-LEN(F{var}));F{var};A{var};A{var};REPT(" ";21);"0001";REPT(" ";32);"1";B{var};REPT(" ";35-LEN(B{var}));C{var};REPT(" ";35-LEN(C{var}));D{var};E{var};A{var})'.format(var=i + 2)

    def get_lines(self, p):
        department_ids = [x.id for x in p.departments_id]
        if not department_ids:
            department_ids = self.pool.get(
                'hr.department').search(self.cr, self.uid, [])
        department_ids = self.pool.get(
            'hr.department').search(self.cr, self.uid, [('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', p.date_from),
            ('date_to', '<=', p.date_to),
            ('company_id', 'in', self.get_companies_ids(p)),
            ('voucher_mode', '=', 'VIR'),
            ('employee_id.bank_account_id', '!=', False),
        ]
        if p.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if p.state != 'all':
            payslip_domain.append(('state', '=', p.state),)
        payslip_ids = self.pool.get('hr.payslip').search(
            self.cr, self.uid, payslip_domain)
        payslips = self.pool.get('hr.payslip').browse(
            self.cr, self.uid, payslip_ids)
        employees = list(set([x.employee_id for x in payslips]))
        employees = sorted(employees, key=lambda x: x.otherid)
        tab = []
        for emp in employees:
            emp_payslips = payslips.filtered(
                lambda r: r.employee_id.id == emp.id)
            line = {}
            line['employee'] = {}
            line['cumul'] = {}
            line['bank'] = {}
            if emp.bank_account_id:
                line['bank'].update({
                    'name': emp.bank_account_id.bank_name or '',
                    'rib': emp.bank_account_id.acc_number or '',
                })
            fields_got = self.pool.get(
                'hr.employee').fields_get(self.cr, self.uid)
            for name, field in fields_got.iteritems():
                try:
                    line['employee'][name] = getattr(emp, name)
                except:
                    pass
            line['employee'][
                'address_home_id'] = emp.address_home_id and emp.address_home_id.contact_address.replace('\n', ', ') or ''
            line['employee'][
                'address_id'] = emp.address_id and emp.address_id.contact_address.replace('\n', ', ') or ''
            dict_keys = self.pool.get('hr.dictionnary').search_read(
                self.cr, self.uid, [], ['name'])
            for code in dict_keys:
                line['cumul'][code.get('name')] = self.pool.get('hr.dictionnary').compute_value(
                    self.cr,
                    self.uid,
                    code=code.get('name'),
                    date_start=p.date_from,
                    date_stop=p.date_to,
                    employee_id=emp.id,
                    payslip_ids=emp_payslips,
                    department_ids=p.departments_id and department_ids or False,
                    state=p.state
                )
            tab.append(line)
        return tab

    def get_companies_ids(self, p):
        if p.company_ids:
            return [x.id for x in p.company_ids]
        else:
            return self.pool.get('res.company').search(self.cr, self.uid, [])


class report_slipqweb(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_voucher_order'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_voucher_order'
    _wrapped_report_class = voucher_order
    
    
    
    
class voucher_order_global(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(voucher_order, self).__init__(
            cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'lines': self.get_lines,
            'text': convert_txt2amount,
            'formula': self._get_formula,
        })


    def _get_formula(self, i, fr=True):
        if fr:
            return '=CONCATENER("3002000000000000000000000000000000000000000MAD2";REPT(0;16-NBCAR(F{var}));F{var};A{var};A{var};REPT(" ";21);"0001";REPT(" ";32);"1";B{var};REPT(" ";35-NBCAR(B{var}));C{var};REPT(" ";35-NBCAR(C{var}));D{var};E{var};A{var})'.format(var=i + 2)
        return '=CONCATENATE("3002000000000000000000000000000000000000000MAD2";REPT(0;16-LEN(F{var}));F{var};A{var};A{var};REPT(" ";21);"0001";REPT(" ";32);"1";B{var};REPT(" ";35-LEN(B{var}));C{var};REPT(" ";35-LEN(C{var}));D{var};E{var};A{var})'.format(var=i + 2)

    def get_lines(self, p):
        department_ids = [x.id for x in p.departments_id]
        if not department_ids:
            department_ids = self.pool.get(
                'hr.department').search(self.cr, self.uid, [])
        department_ids = self.pool.get(
            'hr.department').search(self.cr, self.uid, [('id', 'child_of', department_ids)])
        payslip_domain = [
            ('date_to', '>=', p.date_from),
            ('date_to', '<=', p.date_to),
            ('company_id', 'in', self.get_companies_ids(p)),
            ('voucher_mode', '=', 'VIR'),
            ('employee_id.bank_account_id', '!=', False),
        ]
        if p.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if p.state != 'all':
            payslip_domain.append(('state', '=', p.state),)
        payslip_ids = self.pool.get('hr.payslip').search(
            self.cr, self.uid, payslip_domain)
        payslips = self.pool.get('hr.payslip').browse(
            self.cr, self.uid, payslip_ids)
        employees = list(set([x.employee_id for x in payslips]))
        employees = sorted(employees, key=lambda x: x.otherid)
        tab = []
        for emp in employees:
            emp_payslips = payslips.filtered(
                lambda r: r.employee_id.id == emp.id)
            line = {}
            line['employee'] = {}
            line['cumul'] = {}
            line['bank'] = {}
            if emp.bank_account_id:
                line['bank'].update({
                    'name': emp.bank_account_id.bank_name or '',
                    'rib': emp.bank_account_id.acc_number or '',
                })
            fields_got = self.pool.get(
                'hr.employee').fields_get(self.cr, self.uid)
            for name, field in fields_got.iteritems():
                try:
                    line['employee'][name] = getattr(emp, name)
                except:
                    pass
            line['employee'][
                'address_home_id'] = emp.address_home_id and emp.address_home_id.contact_address.replace('\n', ', ') or ''
            line['employee'][
                'address_id'] = emp.address_id and emp.address_id.contact_address.replace('\n', ', ') or ''
            dict_keys = self.pool.get('hr.dictionnary').search_read(
                self.cr, self.uid, [], ['name'])
            for code in dict_keys:
                line['cumul'][code.get('name')] = self.pool.get('hr.dictionnary').compute_value(
                    self.cr,
                    self.uid,
                    code=code.get('name'),
                    date_start=p.date_from,
                    date_stop=p.date_to,
                    employee_id=emp.id,
                    payslip_ids=emp_payslips,
                    department_ids=p.departments_id and department_ids or False,
                    state=p.state
                )
            tab.append(line)
        return tab

    def get_companies_ids(self, p):
        if p.company_ids:
            return [x.id for x in p.company_ids]
        else:
            return self.pool.get('res.company').search(self.cr, self.uid, [])


class report_slipqweb_global(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_voucher_order_global'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_voucher_order_global'
    _wrapped_report_class = voucher_order
