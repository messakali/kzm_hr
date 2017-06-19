# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning as UserError
from odoo.addons.kzm_base.controllers import tools as T
from datetime import datetime, timedelta
from variables import *

import time

import logging
_logger = logging.getLogger(__name__)

class hr_saisie_run(models.Model):
    _name = 'hr.saisie.run'
    _description = 'Lot de saisie'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date_start desc'

    _track = {
        'state': {
            'l10n_ma_hr_payroll.mt_saisie_run_confirmed': lambda self, cr, uid, obj, ctx=None: obj.state == 'confirm',
            'l10n_ma_hr_payroll.mt_saisie_run_csv': lambda self, cr, uid, obj, ctx=None: obj.state == 'csv',
            'l10n_ma_hr_payroll.mt_saisie_run_done': lambda self, cr, uid, obj, ctx=None: obj.state == 'done',
            'l10n_ma_hr_payroll.mt_saisie_run_cancel': lambda self, cr, uid, obj, ctx=None: obj.state == 'cancel',
        },
    }

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
            self.date_start = self.fiscalyear_id.date_start
            self.date_end = self.fiscalyear_id.date_end
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
        self.date_start = False
        self.date_end = False
        if self.period_id:
            self.date_start = self.period_id.date_start
            self.date_end = self.period_id.date_end

    fiscalyear_id = fields.Many2one(
        'date.range', string=u'Année', required=False, domain=[('type_id.fiscal_year', '=', True),('active', '=', True)])
    period_id = fields.Many2one(
        'date.range', string=u'Période', required=False)


    departments_id = fields.Many2many(
        'hr.department', 'saisie_run_department_rel', 'run_id', 'employee_id', string=u'Limiter les départements', )
    category_ids = fields.Many2many(
        'hr.employee.category', 'saisie_run_employee_categ_rel', 'run_id', 'category_id', string=u'Catégories des employés', )

    @api.one
    @api.depends('date_start', 'date_end', 'company_id')
    def _compute_name(self):
        if self.date_start and self.date_end and self.company_id:
            self.name = '/'.join([self.company_id.initial or self.company_id.name,
                                  self.date_start, self.date_end]).replace('-', '')
        else:
            self.name = ''

    name = fields.Char(
        string=u'Nom', size=64, compute='_compute_name',  store=True,)

    date_start = fields.Date(string=u'Date début',  required=True,
                             default=lambda self: T.date_range(fields.Date.today())[0],)
    date_end = fields.Date(string=u'Date fin',  required=True,
                           default=lambda self: T.date_range(fields.Date.today())[1],)

    csv_lock = fields.Boolean(string=u'Vérouillage CSV', default=False, copy=False)

    @api.multi
    def _get_default_company(self):
        companies = self.env['res.company'].with_context({'active_test': False, }).search([]).mapped('id')
        return len(companies) == 1 and companies[0] or False
    company_id = fields.Many2one(
        'res.company', string=u'Société', required=True, default=lambda self: self._get_default_company(),)

    line_ids = fields.One2many('hr.saisie.line', 'run_id', string=u'Lignes',)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('csv', 'Export/Import CSV'),
        ('confirm', 'Confirmé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string=u'État', readonly=True, track_visibility='onchange', copy=False, default='draft',)

    @api.one
    def _compute_saisie_line_count(self):
        self.saisie_line_count = len(self.line_ids)

    saisie_line_count = fields.Integer(string=u'Lignes', compute='_compute_saisie_line_count',   )
    @api.model
    def set_confirm(self):
        for line in self.line_ids:
            line.check_data()
            line.propagate()
        self.state = 'confirm'

    @api.model
    def set_csv(self):
        for record in self:
            user_ids = []
            user_ids += [x.id for x in record.company_id.rh_users_id]
            user_ids += [x.id for x in self.env.user.company_id.rh_users_id]
            user_ids = list(set(user_ids))
            record.message_subscribe_users(user_ids=user_ids)
        self.state = 'csv'

    @api.model
    def set_draft(self):
        self.state = 'draft'

    @api.model
    def set_done(self):
        self.state = 'done'

    @api.model
    def set_cancel(self):
        for line in self.line_ids:
            line.cancel_propagation()
        self.state = 'cancel'

    @api.multi
    def unlink(self):
        for obj in self:
            if obj.state != 'draft':
                raise UserError(
                    _('Vous ne pouvez pas supprimer un enregistrement qui n\'est pas en état brouillon'))
        return super(hr_saisie_run, self).unlink()

    @api.multi
    def get_tab(self, force_employee_id=False, force_saisie_line_id=False, force_departments=False, force_categories=False):
        """
        force_employee_id can be integer or object
        if specified, the result will be a dictionnary
        else, it return a list of all employees in the run
        """
        start_time = time.time()
        if force_employee_id:
            if not isinstance(force_employee_id, (long, int)):
                force_employee_id = force_employee_id.id
        if force_saisie_line_id:
            if not isinstance(force_saisie_line_id, (long, int)):
                force_saisie_line_id = force_saisie_line_id.id
        # Everything here is linked to payslip.py and rule.py

        def was_on_leave(employee_id, datetime_day, context=None):
            res, code, status = False, False, False
            day = datetime_day.strftime("%Y-%m-%d")
            holidays = self.env['hr.holidays.line'].with_context({'active_test': False, }).search([
                ('holiday_status_id.is_hs', '=', False),
                ('holiday_status_id.is_rappel', '=', False),
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id),
                ('date', '=', day)])
            if holidays:
                status = holidays.mapped('holiday_status_id')[0]
                res, code = status.name, status.code
            return res, code, sum(holidays.mapped('days')), sum(holidays.mapped('hours')), status

        def get_all_rappel(employee_id, datetime_day, context=None):
            day = datetime_day.strftime("%Y-%m-%d")
            return self.env['hr.holidays.line'].with_context({'active_test': False, }).search([
                ('holiday_id.holiday_status_id.is_rappel', '=', True),
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id),
                ('date', '=', day)
            ])

        def get_all_hs(employee_id, datetime_day, context=None):
            day = datetime_day.strftime("%Y-%m-%d")
            return self.env['hr.holidays.line'].with_context({'active_test': False, }).search([
                ('holiday_id.holiday_status_id.is_hs', '=', True),
                ('holiday_id.holiday_status_id.is_rappel', '=', False),
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id),
                ('date', '=', day)
            ])

        def get_holiday_work_lines(employee_id, datetime_day, context=None):
            day = datetime_day.strftime("%Y-%m-%d")
            return self.env['hr.holidays.line'].with_context({'active_test': False, }).search([
                ('holiday_id.holiday_status_id.is_work', '=', True),
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id),
                ('date', '=', day)
            ])

        def get_timesheet_lines(employee_id, datetime_day, context=None):
            day = datetime_day.strftime("%Y-%m-%d")
            return self.env['hr.analytic.timesheet'].with_context({'active_test': False, }).search([
                ('sheet_id.state', '=', 'done'),
                ('sheet_id.employee_id', '=', employee_id),
                ('date', '=', day)
            ])

        tab = []
        for run in self:
            contracts = self.env['hr.contract']
            contract_domain = [
                    ('is_contract_valid_by_context', 'in', (run.date_start,run.date_end)),
                    ('company_id', '=', run.company_id.id),
                    ]
            if force_departments:
                department_ids = isinstance(force_departments, list) and force_departments or force_departments.mapped('id')
                contract_domain.append(('employee_id.department_id','in', department_ids))
            if force_categories:
                category_ids = isinstance(force_categories, list) and force_categories or force_categories.mapped('id')
                contract_domain.append(('employee_id.category_ids','in', category_ids))
            tmp_contracts = self.env['hr.contract'].with_context({'active_test': False, }).search(contract_domain, order='date_start desc')
            blacklist = []
            for contract in tmp_contracts:
                if contract.employee_id.id in blacklist:
                    continue
                contracts |= contract
                blacklist.append(contract.employee_id.id)
            for contract in contracts.sorted(key=lambda r: r.based_on):
                date_start = run.date_start < contract.date_start and contract.date_start or run.date_start
                date_end = contract.date_end and run.date_end > contract.date_end and contract.date_end or run.date_end
                day_from = fields.Datetime.from_string(date_start)
                day_to = fields.Datetime.from_string(date_end)
                nb_of_days = (day_to - day_from).days + 1
                based_on_days = ('days' in contract.based_on)
                employee = contract.employee_id
                # if employee.id in blacklist:
                #     continue
                # blacklist.append(employee.id)
                if force_employee_id and force_employee_id != employee.id:
                    continue
                km, cv = self.env['hr.employee.km'].get_km_cv( employee.id, date_start, date_end)
                matrix = {
                    'employee_id': employee.id,
                    'contract_id': contract.id,
                    'run_id': run.id,
                    LEAVE_PAID: 0.0,
                    FIX_LEAVE_PAID: 0.0,
                    NORMAL: 0.0,
                    ATTENDANCE: 0.0,
                    CV: cv,
                    KILOMETRAGE: km,
                    'rate': based_on_days and contract.salary_by_day or contract.salary_by_hour,
                }
                for key in KEYS:
                    matrix[key] = {}
                # Correct normal
                if contract.based_on in [FIXED_DAYS, FIXED_HOURS]:
                    matrix[
                        NORMAL] = based_on_days and contract.nbr_days_declared or contract.nbr_hours_declared
                elif contract.based_on in [WORKED_DAYS, WORKED_HOURS, ATTENDED_DAYS, ATTENDED_HOURS]:
                    mass_days, mass_hours = self.env['hr.employee.mass.attendance'].get_days_hours(
                        employee.id, day_from, day_to)
                    mission_days, mission_hours = self.env['hr.employee.mission'].get_days_hours(
                        employee.id, day_from, day_to)
                    matrix[
                        NORMAL] = based_on_days and (mass_days+mission_days) or (mass_hours+mission_hours)
                    matrix[
                        ATTENDANCE] = based_on_days and (mass_days+mission_days) or (mass_hours+mission_hours)
                for day in range(0, nb_of_days):
                    work_lines = get_holiday_work_lines(
                        employee.id, day_from + timedelta(days=day))
                    working_hours_on_holiday = contract.default_hours_on_holiday
                    rappels = get_all_rappel(
                        employee.id, day_from + timedelta(days=day))
                    for rappel in rappels:
                        if based_on_days:
                            matrix[NORMAL] -= rappel.days
                            matrix[ATTENDANCE] -= rappel.days
                        else:
                            matrix[NORMAL] -= rappel.hours
                            matrix[ATTENDANCE] -= rappel.hours
                    if contract.based_on in [WORKED_DAYS, WORKED_HOURS, ATTENDED_DAYS, ATTENDED_HOURS]:
                        times_days, times_hours = self.env['hr.attendance'].get_days_hours(
                            employee.id, day_from + timedelta(days=day))
                        if contract.based_on in [ATTENDED_DAYS, WORKED_DAYS]:
                            matrix[NORMAL] += times_days
                            matrix[ATTENDANCE] += times_days
                        if contract.based_on in [ATTENDED_HOURS, WORKED_HOURS]:
                            matrix[NORMAL] += times_hours
                            matrix[ATTENDANCE] += times_hours
                    if contract.based_on in [TIMESHEET_DAYS, TIMESHEET_HOURS]:
                        timesheet_lines = get_timesheet_lines(
                            employee.id, day_from + timedelta(days=day))
                        if contract.based_on == TIMESHEET_DAYS:
                            if timesheet_lines:
                                matrix[NORMAL] += 1
                                matrix[ATTENDANCE] += 1
                        if contract.based_on == TIMESHEET_HOURS:
                            for timesheet_line in timesheet_lines:
                                matrix[NORMAL] += timesheet_line.unit_amount
                                matrix[ATTENDANCE] += timesheet_line.unit_amount
                    for work_line in work_lines:
                        if based_on_days:
                            matrix[FIX_LEAVE_PAID] -= work_line.days
                        else:
                            matrix[FIX_LEAVE_PAID] -= work_line.hours
                    if self.env['hr.holidays.public'].is_free(fields.Datetime.to_string(day_from + timedelta(days=day))):
                        if based_on_days:
                            matrix[NORMAL] -= 1
                            matrix[LEAVE_PAID] += 1
                            matrix[FIX_LEAVE_PAID] += 1
                        else:
                            matrix[NORMAL] -= working_hours_on_holiday
                            matrix[LEAVE_PAID] += working_hours_on_holiday
                            matrix[FIX_LEAVE_PAID] += working_hours_on_holiday
                    leave_type, code, leave_days, leave_hours, leave_status = was_on_leave(
                        employee.id, day_from + timedelta(days=day))
                    if leave_status:
                        if based_on_days:
                            matrix[NORMAL] -= leave_days
                        else:
                            matrix[NORMAL] -= leave_hours
                        if matrix[LEAVE].get(code, False):
                            if based_on_days:
                                matrix[LEAVE][code] += leave_days
                            else:
                                matrix[LEAVE][code] += leave_hours
                        else:
                            if based_on_days:
                                matrix[LEAVE][code] = leave_days
                            else:
                                matrix[LEAVE][code] = leave_hours

                # Expense paid
                domain = [
                    ('expense_id.state', 'in', ['done', 'paid']),
                    ('expense_id.payroll_ok', '=', False),
                    ('expense_id.employee_id', '=', employee.id),
                    ('date_value', '<=', date_end),
                    ('date_value', '>=', date_start),
                ]
                if force_saisie_line_id:
                    domain.append(
                        ('expense_id.saisie_line_id', '=', force_saisie_line_id))
                lines = self.env['hr.expense.line'].with_context({'active_test': False, }).search(domain)
                matrix[EXPENSE_PAID] = sum([x.total_amount for x in lines])
                # expense_to_pay
                domain = [
                    ('expense_id.state', '=', 'paid'),
                    ('expense_id.payroll_ok', '=', True),
                    ('expense_id.employee_id', '=', employee.id),
                    ('payroll_date', '<=', date_end),
                    ('payroll_date', '>=', date_start),
                ]
                if force_saisie_line_id:
                    domain.append(
                        ('expense_id.saisie_line_id', '=', force_saisie_line_id))
                lines = self.env['hr.expense.line'].with_context({'active_test': False, }).search(domain)
                matrix[EXPENSE_TO_PAY] = sum([x.total_amount for x in lines])
                for leave in self.env['hr.holidays.status'].with_context({'active_test': False, }).search([('is_hs', '=', False)]):
                    total = 0.0
                    domain = [
                        ('holiday_status_id', '=', leave.id),
                        ('state', '=', 'validate'),
                        ('employee_id', '=', employee.id),
                        ('date', '>=', date_start),
                        ('date', '<=', date_end)]
                    if force_saisie_line_id:
                        domain.append(
                            ('holiday_id.saisie_line_id', '=', force_saisie_line_id))
                    lines = self.env['hr.holidays.line'].with_context({'active_test': False, }).search(domain)
                    if based_on_days:
                        total = sum([x.days for x in lines])
                    else:
                        total = sum([x.hours for x in lines])
                    matrix[LEAVE][leave.code] = total
                    matrix[LEAVE][leave.id] = total
                for hs in self.env['hr.holidays.status'].with_context({'active_test': False, }).search([('is_hs', '=', True)]):
                    total = 0.0
                    domain = [
                        ('holiday_status_id', '=', hs.id),
                        ('state', '=', 'validate'),
                        ('employee_id', '=', employee.id),
                        ('date', '>=', date_start),
                        ('date', '<=', date_end)]
                    if force_saisie_line_id:
                        domain.append(
                            ('holiday_id.saisie_line_id', '=', force_saisie_line_id))
                    lines = self.env['hr.holidays.line'].with_context({'active_test': False, }).search(domain)
                    # if based_on_days:
                    #     total = sum([x.days for x in lines])
                    # else:
                    # Heures supplémentaires toujours basées sur les heures
                    total = sum([x.hours for x in lines])
                    matrix[HS][hs.code] = total
                    matrix[HS][hs.id] = total
                for rubrique in self.env['hr.rubrique'].with_context({'active_test': False, }).search([('auto_compute','=',False)]):
                    # Domain linked to rule.py
                    domain = self.env['hr.rubrique.line'].get_domain(employee_id=employee.id, state='done', code=rubrique.code, date_start=date_start, date_end=date_end)
                    if force_saisie_line_id:
                        domain.append(
                            ('saisie_line_id', '=', force_saisie_line_id))
                    lines = self.env['hr.rubrique.line'].with_context({'active_test': False, }).search(domain)
                    total = sum([x.amount for x in lines])
                    matrix[RUBRIQUE][rubrique.code] = total
                    matrix[RUBRIQUE][rubrique.id] = total
                for avantage in self.env['hr.avantage'].with_context({'active_test': False, }).search([]):
                    # Domain linked to rule.py
                    domain = [
                        ('state', '=', 'done'),
                        ('code', '=', avantage.code),
                        ('employee_id', '=', employee.id),
                        '|',
                        '|',
                        '&',
                        ('date_start', '>=', date_start),
                        ('date_start', '<=', date_end),
                        '&',
                        ('date_end', '>=', date_start),
                        ('date_end', '<=', date_end),
                        '&',
                        ('date_start', '<=', date_start),
                        ('date_end', '>=', date_end),
                    ]
                    if force_saisie_line_id:
                        domain.append(
                            ('saisie_line_id', '=', force_saisie_line_id))
                    lines = self.env['hr.avantage.line'].with_context({'active_test': False, }).search(domain)
                    total = sum([x.amount for x in lines])
                    matrix[AVANTAGE][avantage.code] = total
                    matrix[AVANTAGE][avantage.id] = total
                for avance in self.env['hr.avance'].with_context({'active_test': False, }).search([]):
                    # Domain linked to rule.py
                    domain = [
                        ('state', '=', 'done'),
                        ('avance_line_id.code', '=', avance.code),
                        ('avance_line_id.employee_id', '=', employee.id),
                        ('date', '>=', date_start),
                        ('date', '<=', date_end),
                    ]
                    if force_saisie_line_id:
                        domain.append(
                            ('saisie_line_id', '=', force_saisie_line_id))
                    lines = self.env['hr.avance.line.line'].with_context({'active_test': False, }).search(domain)
                    total = sum([x.amount for x in lines])
                    matrix[AVANCE][avance.code] = total
                    matrix[AVANCE][avance.id] = total
                tab.append(matrix)
                _logger.info('Meter saisie_run get_tab '.upper() + "%s -> nbr : %s" % (time.time() - start_time, len(contracts), ))
        if force_employee_id:
            return tab and tab[0] or {}
        return tab

    @api.multi
    def saisie_csv(self):
        for run in self:
            if not run.line_ids:
                raise UserError(_('Aucun ligne généré'))
            run.signal_workflow('saisie_csv')

    @api.multi
    def generate(self):
        start_time = time.time()
        for run in self:
            if run.csv_lock:
                raise UserError(
                    'Un fichier CSV a été déjà importé dans ce lot, éssayez de l\'annuler et de créer un nouveau lot de saiaie.')
            run.line_ids.unlink()
            data = run.get_tab(force_categories=run.category_ids, force_departments=run.departments_id)
            for line in data:
                new_line = {}
                for k, v in line.iteritems():
                    if not isinstance(v, dict):
                        new_line[k] = v
                saisie_line = run.line_ids.create(new_line)
                for k, v in line.iteritems():
                    if isinstance(v, dict):
                        for key, value in v.iteritems():
                            if k == LEAVE:
                                if value > 0 and isinstance(key, (int, long)):
                                    self.env['hr.saisie.leave'].create({
                                        'saisie_id': saisie_line.id,
                                        'type_id': key,
                                        'value': value,
                                    })
                            elif k == HS:
                                if value > 0 and isinstance(key, (int, long)):
                                    self.env['hr.saisie.hs'].create({
                                        'saisie_id': saisie_line.id,
                                        'type_id': key,
                                        'value': value,
                                    })
                            elif k == RUBRIQUE:
                                if value > 0 and isinstance(key, (int, long)):
                                    self.env['hr.saisie.rubrique'].create({
                                        'saisie_id': saisie_line.id,
                                        'type_id': key,
                                        'value': value,
                                    })
                            elif k == AVANTAGE:
                                if value > 0 and isinstance(key, (int, long)):
                                    self.env['hr.saisie.avantage'].create({
                                        'saisie_id': saisie_line.id,
                                        'type_id': key,
                                        'value': value,
                                    })
                            elif k == AVANCE:
                                if value > 0 and isinstance(key, (int, long)):
                                    self.env['hr.saisie.avance'].create({
                                        'saisie_id': saisie_line.id,
                                        'type_id': key,
                                        'value': value,
                                    })
                            else:
                                raise UserError(
                                    _('La clé [%s] est introuvale dans la liste (Avantage, Avance, Rubrique, etc)') % k)
            run.message_post(_('Génération des données'))
        _logger.info('Meter saisie_run generate '.upper() + "%s" % (time.time() - start_time))


    @api.multi
    def export_csv(self):
        for run in self:
            action = self.env.ref(
                'l10n_ma_hr_payroll.hr_saisie_export_wizard_action').read()
            if action:
                action = action[0]
                action['context'] = {'default_run_id': run.id}
                return action

    @api.multi
    def import_csv(self):
        for run in self:
            action = self.env.ref(
                'l10n_ma_hr_payroll.hr_saisie_import_wizard_action').read()
            if action:
                action = action[0]
                action['context'] = {'default_run_id': run.id}
                return action
