# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
import odoo.addons.decimal_precision as dp
from variables import *
from datetime import datetime, timedelta

import time

import logging
_logger = logging.getLogger(__name__)

class hr_saisie_line(models.Model):
    _name = 'hr.saisie.line'
    _description = 'Lignes de saisie'
    _order = 'date_start desc'

    @api.one
    @api.depends('date_start', 'date_end', 'company_id', 'employee_id')
    def _compute_name(self):
        if self.date_start and self.date_end and self.company_id and self.employee_id:
            self.name = '/'.join([self.company_id.initial or self.company_id.name, self.employee_id.name,
                                  self.date_start, self.date_end]).replace('-', '')
        else:
            self.name = ''

    name = fields.Char(
        string=u'Nom', size=64, compute='_compute_name',  store=True,)

    date_start = fields.Date(
        string=u'Date début',   related='run_id.date_start',  store=True,)
    date_end = fields.Date(
        string=u'Date fin',   related='run_id.date_end', store=True,)
    run_id = fields.Many2one(
        'hr.saisie.run', string=u'Lot',  required=True, ondelete='cascade',)
    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé', required=True)
    contract_id = fields.Many2one(
        'hr.contract', string=u'Contrat',  required=True)
    company_id = fields.Many2one(
        'res.company', string=u'Société',  related='run_id.company_id', store=True,)
    state = fields.Selection(readonly=True, copy=False, related='run_id.state', store=True,)

    @api.multi
    def is_based_on_days(self):
        self.ensure_one()
        return ('days' in self.based_on)

    based_on = fields.Selection(
        string=u'Basé sur', related='contract_id.based_on',)
    struct_id = fields.Many2one(
        string=u'Structure du salaire',  related='contract_id.struct_id',)

    cv = fields.Integer(string=u'Puissance fiscale',  )
    kilometrage = fields.Float(string=u'Kilometrage', digits=dp.get_precision('Account'),  )

    rate = fields.Float(
        string=u'Taux H/J', digits=dp.get_precision('Account'),)
    normal = fields.Float(
        string=u'H/J normal', digits=dp.get_precision('Account'),)
    leave_paid = fields.Float(
        string=u'H/J Chomé payé', digits=dp.get_precision('Account'),)
    fix_leave_paid = fields.Float(
        string=u'Global H/J Chomé', digits=dp.get_precision('Account'), readonly=True, )

    expense_paid = fields.Float(
        string=u'Note de frais payées', digits=dp.get_precision('Account'),)
    expense_to_pay = fields.Float(
        string=u'Note de frais à payer', digits=dp.get_precision('Account'),)

    leave_ids = fields.One2many(
        'hr.saisie.leave', 'saisie_id', string=u'Congés',)
    hs_ids = fields.One2many('hr.saisie.hs', 'saisie_id', string=u'Heures supplémentaires',)
    rubrique_ids = fields.One2many(
        'hr.saisie.rubrique', 'saisie_id', string=u'Rubriques',)
    avantage_ids = fields.One2many(
        'hr.saisie.avantage', 'saisie_id', string=u'Avanatges',)
    avance_ids = fields.One2many(
        'hr.saisie.avance', 'saisie_id', string=u'Avances',)
    notes = fields.Text(string=u'Notes',)

    def check_data(self):
        # print self.leave_paid
        actual_days = self.leave_paid or 0
        # for line in self.leave_ids:
        #     if line.type_id.is_work:
        #         actual_days += line.value or 0
        if self.fix_leave_paid != actual_days:
            raise Warning(
                _('[%s] : Number of holidays is [%s], the given is [%s]') % (self.employee_id.otherid or self.employee_id.name, self.fix_leave_paid, actual_days))

    @api.one
    def propagate(self):
        start_time = time.time()
        def get_next_date(current_date, days=1):
            current_datetime = fields.Datetime.from_string(current_date)
            current_datetime += timedelta(days=days)
            current_date = fields.Datetime.to_string(current_datetime)
            return current_date

        date_from = self.date_start < self.contract_id.date_start and self.contract_id.date_start or self.date_start
        date_to = self.contract_id.date_end and self.date_end > self.contract_id.date_end and self.contract_id.date_end or self.date_end

        current_date = date_from
        current_date_timesheet = date_from


        product = self.env['product.product'].with_context({'active_test': False, }).search([
            ('default_expense_ok', '=', True),
        ], order='can_be_expensed desc', limit=1)
        tab = self.run_id.get_tab(force_employee_id=self.employee_id.id)
        # Propagate hours
        origin = self.based_on in [FIXED_DAYS, FIXED_HOURS] and tab.get(NORMAL, 0.0) or tab.get(ATTENDANCE, 0.0)
        new = self.normal
        diff = new - origin
        if diff:
            if self.based_on in [FIXED_DAYS, FIXED_HOURS]:
                raise Warning(
                    _("Nombre normal H/J de l'employé [%s] doit être [%s]") % (self.employee_id.name, origin))
            if self.based_on in [WORKED_DAYS, WORKED_HOURS, ATTENDED_DAYS, ATTENDED_HOURS]:

                mass_run = self.env['hr.employee.mass.attendance.run'].with_context({'active_test': False, }).search([
                    ('company_id', '=', self.company_id.id),
                    ('date_from', '>=', date_from),
                    ('date_to', '<=', date_to),
                    ('state', 'in', ['manual','done']),
                ], limit=1)
                if not mass_run:
                    mass_run = self.env['hr.employee.mass.attendance.run'].create({
                        'company_id': self.company_id.id,
                        'date_from': date_from,
                        'date_to': date_to,
                        'saisie_line_id': self.id,
                    })
                self.env['hr.employee.mass.attendance'].create({
                    'run_id': mass_run.id,
                    'employee_id': self.employee_id.id,
                    'date_from': date_from,
                    'date_to': date_to,
                    'saisie_line_id': self.id,
                    'days': self.is_based_on_days() and diff or diff /self.company_id.default_hours_on_holiday,
                    'hours': self.is_based_on_days() and diff*self.company_id.default_hours_on_holiday or diff,
                })
                mass_run.set_done()
            if self.based_on in [TIMESHEET_HOURS, TIMESHEET_DAYS]:
                timesheets = self.env['hr_timesheet_sheet.sheet'].with_context({'active_test': False, }).search([
                    ('state', '=', 'done'),
                    ('employee_id', '=', self.employee_id.id),
                    ('date_from', '>=', date_from),
                    ('date_to', '<=', date_to),
                ], order="date_to desc", limit=1)
                timesheet_date_from = timesheets and get_next_date(
                    timesheets.date_to) or date_from
                account = self.env['account.analytic.account'].with_context({'active_test': False, }).search(
                    [('use_timesheets', '=', True)])
                data = {
                    'name': self.name,
                    'user_id': self.employee_id.user_id.id,
                    'date': timesheet_date_from,
                    'unit_amount': diff,
                    'to_invoice': False,
                    'account_id': account.id,

                }
                data.update(
                    self.env['hr.analytic.timesheet'].on_change_user_id(
                        self.employee_id.user_id.id).get('value')
                )
                timesheet = self.env['hr_timesheet_sheet.sheet'].create({
                    'employee_id': self.employee_id.id,
                    'date_from': timesheet_date_from,
                    'date_to': timesheet_date_from,
                    'timesheet_ids': [(0, 0, data)],
                    'saisie_line_id': self.id,
                })

                timesheet.button_confirm()
                timesheet.signal_workflow('done')

        # Propagate holidays
        holiday_codes = [
            k for k, v in tab[LEAVE].iteritems() if isinstance(k, basestring) and v != 0]
        for holiday_line in self.leave_ids:
            code = holiday_line.type_id.code
            if code in holiday_codes:
                holiday_codes.remove(code)
            origin = tab[LEAVE].get(code, 0.0)
            new = holiday_line.value
            diff = new - origin
            if diff:
                doc_lines = origin > 0 and self.env['hr.holidays.line'].with_context({'active_test': False, }).search([
                    ('employee_id', '=', self.employee_id.id),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('holiday_status_id.code', '=', code),
                ]) or False
                if doc_lines:
                    # doc = doc_line.holiday_id
                    # doc.signal_workflow('reset')
                    holiday_docs = doc_lines.mapped('holiday_id')
                    holiday_docs.should_be_refused()
                while True:
                    holiday = self.env['hr.holidays'].with_context({'active_test': False, }).search([
                        ('date_from', '<=', current_date),
                        ('date_to', '>=', current_date),
                        ('employee_id', '=', self.employee_id.id),
                    ], limit=1)
                    if not holiday:
                        break
                    if current_date == date_to:
                        raise Warning(
                            _('The table of overtimes is overflow for this period'))
                    current_date = get_next_date(current_date)
                dhd = self.contract_id.default_hours_on_holiday or 0.0
                number_of_hours_temp = self.is_based_on_days() and new * \
                    dhd or new
                number_of_days_temp = self.is_based_on_days() and new or (
                    dhd > 0 and new / dhd or 0)
                doc = self.env['hr.holidays'].create({
                    'name': holiday_line.type_id.name,
                    'date_from': current_date,
                    'date_to': current_date,
                    'employee_id': self.employee_id.id,
                    'saisie_line_id': self.id,
                    'holiday_status_id': holiday_line.type_id.id,
                    'number_of_hours_temp': number_of_hours_temp,
                    'number_of_days_temp': number_of_days_temp,
                })
                doc.line_ids.create({
                    'date': current_date,
                    'holiday_id': doc.id,
                    'hours': number_of_hours_temp,
                    'days': number_of_days_temp,
                })
                doc.should_be_validated()
        if holiday_codes:
            doc_lines = self.env['hr.holidays.line'].with_context({'active_test': False, }).search([
                ('employee_id', '=', self.employee_id.id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('holiday_status_id.code', 'in', holiday_codes),
            ])
            if doc_lines:
                # doc = doc_line.holiday_id
                # doc.signal_workflow('reset')
                holiday_docs = doc_lines.mapped('holiday_id')
                holiday_docs.should_be_refused()
        # Propagate hs
        hs_codes = [
            k for k, v in tab[HS].iteritems() if isinstance(k, basestring) and v != 0]
        for hs_line in self.hs_ids:
            code = hs_line.type_id.code
            if code in hs_codes:
                hs_codes.remove(code)
            origin = tab[HS].get(code, 0.0)
            new = hs_line.value
            diff = new - origin
            if diff:
                doc_lines = origin > 0 and self.env['hr.holidays.line'].with_context({'active_test': False, }).search([
                    ('employee_id', '=', self.employee_id.id),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('holiday_status_id.code', '=', code),
                ]) or False
                if doc_lines:
                    # doc = doc_line.holiday_id
                    # doc.signal_workflow('reset')
                    hs_docs = doc_lines.mapped('holiday_id')
                    hs_docs.should_be_refused()
                while True:
                    holiday = self.env['hr.holidays'].with_context({'active_test': False, }).search([
                        ('date_from', '<=', current_date),
                        ('date_to', '>=', current_date),
                        ('employee_id', '=', self.employee_id.id),
                    ], limit=1)
                    if not holiday:
                        break
                    if current_date == date_to:
                        raise Warning(
                            _('The table of overtimes is overflow for this period'))
                    current_date = get_next_date(current_date)

                doc = self.env['hr.holidays'].create({
                    'name': hs_line.type_id.name,
                    'date_from': current_date,
                    'date_to': current_date,
                    'employee_id': self.employee_id.id,
                    'saisie_line_id': self.id,
                    'holiday_status_id': hs_line.type_id.id,
                    'number_of_hours_temp': new,
                    'number_of_days_temp': 1,
                })
                doc.line_ids.create({
                    'date': current_date,
                    'holiday_id': doc.id,
                    'hours': new,
                    'days': 1,
                })
                doc.should_be_validated()
        if hs_codes:
            doc_lines = self.env['hr.holidays.line'].with_context({'active_test': False, }).search([
                ('employee_id', '=', self.employee_id.id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('holiday_status_id.code', 'in', hs_codes),
            ])
            if doc_lines:
                # doc = doc_line.holiday_id
                # doc.signal_workflow('reset')
                hs_docs = doc_lines.mapped('holiday_id')
                hs_docs.should_be_refused()
        # Propagate Rubriques
        rubrique_codes = [
            k for k, v in tab[RUBRIQUE].iteritems() if isinstance(k, basestring) and v != 0]
        for rubrique_line in self.rubrique_ids:
            code = rubrique_line.type_id.code
            if code in rubrique_codes:
                rubrique_codes.remove(code)
            origin = tab[RUBRIQUE].get(code, 0.0)
            new = rubrique_line.value
            diff = new - origin
            if diff:
                doc = self.env['hr.rubrique.line'].create({
                    'name': rubrique_line.type_id.name,
                    'date_start': date_from,
                    'date_end': date_to,
                    'employee_id': self.employee_id.id,
                    'saisie_line_id': self.id,
                    'rubrique_id': rubrique_line.type_id.id,
                    'amount': diff
                })
                doc.signal_workflow('rubrique_confirm')
                doc.signal_workflow('rubrique_validate')
                doc.signal_workflow('rubrique_done')
        if rubrique_codes:
            for rubrique in self.env['hr.rubrique'].with_context({'active_test': False, }).search([('code', 'in', rubrique_codes)]):
                origin = tab[RUBRIQUE].get(rubrique.code, 0.0)
                diff = 0 - origin
                if diff:
                    doc = self.env['hr.rubrique.line'].create({
                        'name': rubrique.name,
                        'date_start': date_from,
                        'date_end': date_to,
                        'employee_id': self.employee_id.id,
                        'saisie_line_id': self.id,
                        'rubrique_id': rubrique.id,
                        'amount': diff
                    })
                    doc.signal_workflow('rubrique_confirm')
                    doc.signal_workflow('rubrique_validate')
                    doc.signal_workflow('rubrique_done')
        # Propagate Advances
        avance_codes = [
            k for k, v in tab[AVANCE].iteritems() if isinstance(k, basestring) and v != 0]
        for avance_line in self.avance_ids:
            code = avance_line.type_id.code
            if code in avance_codes:
                avance_codes.remove(code)
            origin = tab[AVANCE].get(code, 0.0)
            new = avance_line.value
            diff = new - origin
            if diff and avance_line.type_id.csv_erase and avance_line.type_id.interest_rate == 0:
                doc = self.env['hr.avance.line'].create({
                    'name': avance_line.type_id.name,
                    'date_start': date_from,
                    'date_end': date_to,
                    'employee_id': self.employee_id.id,
                    'saisie_line_id': self.id,
                    'avance_id': avance_line.type_id.id,
                    'amount': diff
                })
                doc.signal_workflow('avance_confirm')
                doc.signal_workflow('avance_validate')
                doc.signal_workflow('avance_done')
                for line in doc.line_ids:
                    line.set_done()

        if avance_codes:
            for avance in self.env['hr.avance'].with_context({'active_test': False, }).search([
                            ('code', 'in', avance_codes),
                            ('csv_erase', '=', True),
                            ('interest_rate', '=', 0),
                        ]):
                origin = tab[AVANCE].get(avance.code, 0.0)
                diff = 0 - origin
                if diff:
                    doc = self.env['hr.avance.line'].create({
                        'name': avance.name,
                        'date_start': date_from,
                        'date_end': date_to,
                        'employee_id': self.employee_id.id,
                        'saisie_line_id': self.id,
                        'avance_id': avance.id,
                        'amount': diff
                    })
                    doc.signal_workflow('avance_confirm')
                    doc.signal_workflow('avance_validate')
                    doc.signal_workflow('avance_done')
                    for line in doc.line_ids:
                        line.set_done()

        # Propagate Advantages
        avantage_codes = [
            k for k, v in tab[AVANTAGE].iteritems() if isinstance(k, basestring) and v != 0]
        for avantage_line in self.avantage_ids:
            code = avantage_line.type_id.code
            if code in avantage_codes:
                avantage_codes.remove(code)
            origin = tab[AVANTAGE].get(code, 0.0)
            new = avantage_line.value
            diff = new - origin
            if diff:
                doc = self.env['hr.avantage.line'].create({
                    'name': avantage_line.type_id.name,
                    'date_start': date_from,
                    'date_end': date_to,
                    'employee_id': self.employee_id.id,
                    'saisie_line_id': self.id,
                    'avantage_id': avantage_line.type_id.id,
                    'amount': diff
                })
                doc.signal_workflow('avantage_confirm')
                doc.signal_workflow('avantage_validate')
                doc.signal_workflow('avantage_done')
        if avantage_codes:
            for avantage in self.env['hr.avantage'].with_context({'active_test': False, }).search([('code', 'in', avantage_codes)]):
                origin = tab[AVANTAGE].get(avantage.code, 0.0)
                diff = 0 - origin
                if diff:
                    doc = self.env['hr.avantage.line'].create({
                        'name': avantage.name,
                        'date_start': date_from,
                        'date_end': date_to,
                        'employee_id': self.employee_id.id,
                        'saisie_line_id': self.id,
                        'avantage_id': avantage.id,
                        'amount': diff
                    })
                    doc.signal_workflow('avantage_confirm')
                    doc.signal_workflow('avantage_validate')
                    doc.signal_workflow('avantage_done')

        # Notes de frais to pay
        diff = self.expense_to_pay - tab.get(EXPENSE_TO_PAY, )
        if diff:
            if not product:
                raise Warning(
                    _('Please define a defaulmt product for expenses'))
            doc = self.env['hr.expense'].create({
                'name': _('Expense'),
                'date': date_from,
                'payroll_date': date_from,
                'payroll_ok': date_from,
                'company_id': self.company_id.id,
                'employee_id': self.employee_id.id,
                'saisie_line_id': self.id,
                'line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': _('Expense'),
                    'unit_amount': diff,
                    'date_value': date_from,
                })]
            })
            doc.signal_workflow('confirm')
            doc.signal_workflow('validate')
            doc.signal_workflow('payroll_done')
        # Notes de frais paid
        diff = self.expense_paid - tab.get(EXPENSE_PAID, )
        if diff:
            if not product:
                raise Warning(
                    _('Please define a defaulmt product for expenses'))
            doc = self.env['hr.expense'].create({
                'name': _('Expense'),
                'date': date_from,
                'company_id': self.company_id.id,
                'employee_id': self.employee_id.id,
                'saisie_line_id': self.id,
                'line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': _('Expense'),
                    'unit_amount': diff,
                    'date_value': date_from,
                })]
            })
            doc.signal_workflow('confirm')
            doc.signal_workflow('validate')
            doc.signal_workflow('done')
        # Kilometrage
        diff = self.kilometrage - tab.get(KILOMETRAGE)
        if diff:
            doc = self.env['hr.employee.km'].create({
                'name': _('Kilometrage'),
                'date': date_from,
                'employee_id': self.employee_id.id,
                'saisie_line_id': self.id,
                'cv': self.cv,
                'value': diff,
            })
            doc.set_done()
        _logger.info('Meter saisie_line propagate '.upper() + "%s" % (time.time() - start_time))

    @api.one
    def cancel_propagation(self):
        start_time = time.time()
        date_from = self.date_start < self.contract_id.date_start and self.contract_id.date_start or self.date_start
        date_to = self.contract_id.date_end and self.date_end > self.contract_id.date_end and self.contract_id.date_end or self.date_end
        product = self.env['product.product'].with_context({'active_test': False, }).search([
            ('default_expense_ok', '=', True),
        ], order='can_be_expensed desc', limit=1)
        tab = self.run_id.get_tab(
            force_employee_id=self.employee_id.id, force_saisie_line_id=self.id)
        # Cancel attendance
        mass_lines = self.env['hr.employee.mass.attendance'].with_context({'active_test': False, }).search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['manual','done']),
            ('saisie_line_id', '!=', False),
        ])
        if mass_lines:
            for mass_line in mass_lines:
                mass_line.days = 0
                mass_line.hours = 0
        # Cancel Timesheets
        timesheets = self.env['hr_timesheet_sheet.sheet'].with_context({'active_test': False, }).search([
            ('state', '=', 'done'),
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('saisie_line_id', '!=', False),
        ])
        for timesheet in timesheets:
            timesheet.should_be_canceled()
        # Cancel holidays
        doc_lines = self.env['hr.holidays.line'].with_context({'active_test': False, }).search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ])
        if doc_lines:
            hs_docs = doc_lines.mapped('holiday_id')
            for hs_doc in hs_docs:
                if hs_doc.saisie_line_id:
                    hs_doc.should_be_refused()
                else:
                    hs_doc.should_be_validated()
        # Cancel Rubriques
        rubrique_codes = [
            k for k, v in tab.get(RUBRIQUE, {}).iteritems() if isinstance(k, basestring) and v != 0]
        if rubrique_codes:
            for rubrique in self.env['hr.rubrique'].with_context({'active_test': False, }).search([('code', 'in', rubrique_codes)]):
                origin = tab[RUBRIQUE].get(rubrique.code, 0.0)
                diff = 0 - origin
                if diff:
                    doc = self.env['hr.rubrique.line'].create({
                        'name': rubrique.name,
                        'date_start': date_from,
                        'date_end': date_to,
                        'employee_id': self.employee_id.id,
                        'saisie_line_id': self.id,
                        'rubrique_id': rubrique.id,
                        'amount': diff
                    })
                    doc.signal_workflow('rubrique_confirm')
                    doc.signal_workflow('rubrique_validate')
                    doc.signal_workflow('rubrique_done')
        # Cancel Advances
        avance_codes = [
            k for k, v in tab.get(AVANCE, {}).iteritems() if isinstance(k, basestring) and v != 0]
        if avance_codes:
            for avance in self.env['hr.avance'].with_context({'active_test': False, }).search([
                    ('code', 'in', avance_codes),
                    ('csv_erase', '=', True),
                    ('interest_rate', '=', 0),
                    ]):
                origin = tab[AVANCE].get(avance.code, 0.0)
                diff = 0 - origin
                if diff:
                    doc = self.env['hr.avance.line'].create({
                        'name': avance.name,
                        'date_start': date_from,
                        'date_end': date_to,
                        'employee_id': self.employee_id.id,
                        'saisie_line_id': self.id,
                        'avance_id': avance.id,
                        'amount': diff
                    })
                    doc.signal_workflow('avance_confirm')
                    doc.signal_workflow('avance_validate')
                    doc.signal_workflow('avance_done')
                    for line in doc.line_ids:
                        line.set_done()
        # Cancel Advantages
        avantage_codes = [
            k for k, v in tab.get(AVANTAGE, {}).iteritems() if isinstance(k, basestring) and v != 0]
        if avantage_codes:
            for avantage in self.env['hr.avantage'].with_context({'active_test': False, }).search([('code', 'in', avantage_codes)]):
                origin = tab[AVANTAGE].get(avantage.code, 0.0)
                diff = 0 - origin
                if diff:
                    doc = self.env['hr.avantage.line'].create({
                        'name': avantage.name,
                        'date_start': date_from,
                        'date_end': date_to,
                        'employee_id': self.employee_id.id,
                        'saisie_line_id': self.id,
                        'avantage_id': avantage.id,
                        'amount': diff
                    })
                    doc.signal_workflow('avantage_confirm')
                    doc.signal_workflow('avantage_validate')
                    doc.signal_workflow('avantage_done')
        # Cancel Notes de frais to pay
        diff = tab.get(EXPENSE_TO_PAY, 0) * -1
        if diff:
            if not product:
                raise Warning(
                    _('Veuillez définir un article par défaut pour les notes de frais'))
            doc = self.env['hr.expense'].create({
                'name': _('Note de frais'),
                'date': date_from,
                'payroll_date': date_from,
                'payroll_ok': date_from,
                'company_id': self.company_id.id,
                'employee_id': self.employee_id.id,
                'saisie_line_id': self.id,
                'line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': _('Note de frais annulé'),
                    'unit_amount': diff,
                    'date_value': date_from,
                })]
            })
            doc.signal_workflow('confirm')
            doc.signal_workflow('validate')
            doc.signal_workflow('payroll_done')
        # Cancel Notes de frais paid
        diff = tab.get(EXPENSE_PAID, 0) * -1
        if diff:
            if not product:
                raise Warning(
                    _('Veuillez définir un article par défaut pour les notes de frais'))
            doc = self.env['hr.expense.expense'].create({
                'name': _('Note de frais'),
                'date': date_from,
                'company_id': self.company_id.id,
                'employee_id': self.employee_id.id,
                'saisie_line_id': self.id,
                'line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': _('Expense cancel'),
                    'unit_amount': diff,
                    'date_value': date_from,
                })]
            })
            doc.signal_workflow('confirm')
            doc.signal_workflow('validate')
            doc.signal_workflow('done')
        # Kilometrage
        diff = tab.get(KILOMETRAGE, 0) * -1
        if diff:
            doc = self.env['hr.employee.km'].create({
                'name': _('Kilometrage (Cancel)'),
                'date': date_from,
                'employee_id': self.employee_id.id,
                'saisie_line_id': self.id,
                'cv': self.cv,
                'value': diff,
            })
            doc.set_done()
        _logger.info('Meter saisie_line cancel_propagation '.upper() + "%s" % (time.time() - start_time))


class hr_saisie_leave(models.Model):
    _name = 'hr.saisie.leave'
    _description = 'Leaves'

    saisie_id = fields.Many2one(
        'hr.saisie.line', string=u'Saisie',  required=True, ondelete='cascade',)
    type_id = fields.Many2one('hr.holidays.status', string=u'Type de congé', domain=[
        ('is_hs', '=', False)], required=True, )
    value = fields.Float(
        string=u'Valeur', digits=dp.get_precision('Account'),  required=True, )

    _sql_constraints = [
        ('type_id_saisie_id_unique', 'UNIQUE (type_id,saisie_id)',
         'La ligne doit être unique !'),
    ]


class hr_saisie_hs(models.Model):
    _name = 'hr.saisie.hs'
    _description = u'Heures supplémentaires'

    saisie_id = fields.Many2one(
        'hr.saisie.line', string=u'Saisie',  required=True, ondelete='cascade',)
    type_id = fields.Many2one('hr.holidays.status', string=u'Type', domain=[
        ('is_hs', '=', True)], required=True, )
    value = fields.Float(
        string=u'Valeur', digits=dp.get_precision('Account'),  required=True, )

    _sql_constraints = [
        ('type_id_saisie_id_unique', 'UNIQUE (type_id,saisie_id)',
         'La ligne doit être unique !'),
    ]


class hr_saisie_rubrique(models.Model):
    _name = 'hr.saisie.rubrique'
    _description = 'Rubriques'

    saisie_id = fields.Many2one(
        'hr.saisie.line', string=u'Saisie',  required=True, ondelete='cascade',)
    type_id = fields.Many2one('hr.rubrique', string=u'Type', required=True, )
    value = fields.Float(
        string=u'Valeur', digits=dp.get_precision('Account'),  required=True, )

    _sql_constraints = [
        ('type_id_saisie_id_unique', 'UNIQUE (type_id,id)',
         'La ligne doit être unique !'),
    ]


class hr_saisie_avantage(models.Model):
    _name = 'hr.saisie.avantage'
    _description = 'Advantages'

    saisie_id = fields.Many2one(
        'hr.saisie.line', string=u'Saisie',  required=True, ondelete='cascade',)
    type_id = fields.Many2one('hr.avantage', string=u'Type', required=True, )
    value = fields.Float(
        string=u'Valeur', digits=dp.get_precision('Account'),  required=True, )

    _sql_constraints = [
        ('type_id_saisie_id_unique', 'UNIQUE (type_id,saisie_id)',
         'La ligne doit être unique !'),
    ]


class hr_saisie_avance(models.Model):
    _name = 'hr.saisie.avance'
    _description = 'Advances'

    saisie_id = fields.Many2one(
        'hr.saisie.line', string=u'Saisie',  required=True, ondelete='cascade',)
    type_id = fields.Many2one('hr.avance', string=u'Type', required=True, )
    value = fields.Float(
        string=u'Valeur', digits=dp.get_precision('Account'),  required=True, )

    _sql_constraints = [
        ('type_id_saisie_id_unique', 'UNIQUE (type_id,saisie_id)',
         'La ligne doit être unique !'),
    ]
