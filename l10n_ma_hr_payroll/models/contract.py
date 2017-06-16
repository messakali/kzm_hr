# encoding: utf-8

import logging
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
import time
from odoo.exceptions import Warning
import calendar
import datetime
from dateutil.relativedelta import relativedelta
from variables import *
from odoo.exceptions import Warning as UserError
from odoo.addons.kzm_base.controllers.tools import date_range


_logger = logging.getLogger(__name__)


class hr_contract(models.Model):
    _name = 'hr.contract'
    _inherit = ['hr.contract', 'mail.thread', 'ir.needaction_mixin']


    @api.multi
    def get_all_structures(self):
        """
        @param contract_ids: list of contracts
        @return: the structures linked to the given contracts, ordered by hierachy (parent=False first, then first level children and so on) and without duplicata
        """
        return [r.id for r in self.struct_id._get_parent_structure()]
    

    @api.one
    def _get_next_contract(self):
        next_id = False
        if self.date_end and self.employee_id and self.company_id:
            date_end = fields.Datetime.from_string(
                self.date_end) + relativedelta(days=1)
            next_start = fields.Date.to_string(date_end)
            next_id = self.search([
                ('employee_id', '=', self.employee_id.id),
                ('company_id', '=', self.company_id.id),
                ('date_start', 'in', [next_start, self.date_end]),
            ], order='date_start asc', limit=1)
        self.next_id = next_id

    @api.one
    def _get_previous_contract(self):
        previous_id = False
        if self.date_start and self.employee_id and self.company_id:
            date_start = fields.Datetime.from_string(
                self.date_start) + relativedelta(days=-1)
            previous_end = fields.Date.to_string(date_start)
            previous_id = self.search([
                ('employee_id', '=', self.employee_id.id),
                ('company_id', '=', self.company_id.id),
                ('date_end', 'in', [previous_end, self.date_start]),
            ], order='date_end desc', limit=1)
        self.previous_id = previous_id

    next_id = fields.Many2one(
        'hr.contract', string=u'Suivant', compute='_get_next_contract',)
    previous_id = fields.Many2one(
        'hr.contract', string=u'Précédent',  compute='_get_previous_contract',)

    type_id = fields.Many2one(string=u'Type', track_visibility='onchange')
    struct_id = fields.Many2one(string=u'Structure du salaire', track_visibility='onchange')
    date_start = fields.Date(string=u'Date début', track_visibility='onchange')
    date_end = fields.Date(string=u'Date fin', track_visibility='onchange')

    name = fields.Char(
        default=lambda self: self.env['ir.sequence'].get('rec_contract'), track_visibility='onchange')
    voucher_mode = fields.Selection([
        ('ES', u'Espèces'),
        ('CH', u'Chèque'),
        ('VIR', u'Virement'),
    ], string=u'Mode de règlement', track_visibility='onchange', required=True, )
    advantages = fields.Text(
        string=u'Description de la structure', related='struct_id.advantages', store=True)

    journal_id = fields.Many2one(
        related='company_id.payroll_journal_id', store=True, readonly=True, )

    @api.one
    @api.depends("employee_id.qualif_id")
    def _get_qualif_id(self):
        if self.employee_id and self.employee_id.qualif_id:
            self.qualif_id = self.employee_id.qualif_id
        else:
            self.qualif_id = False

    @api.one
    def _set_qualif_id(self):
        if self.employee_id:
            self.employee_id.write(
                {'qualif_id': self.qualif_id and self.qualif_id.id or False})

    qualif_id = fields.Many2one(
        'hr.employee.qualification', string=u"Qualification", compute='_get_qualif_id', inverse='_set_qualif_id', store=True, )

    @api.one
    @api.depends("employee_id.job_id")
    def _get_job_id(self):
        if self.employee_id and self.employee_id.job_id:
            self.job_id = self.employee_id.job_id
        else:
            self.job_id = False

    @api.one
    def _set_job_id(self):
        if self.employee_id:
            self.employee_id.write(
                {'job_id': self.job_id and self.job_id.id or False})

    job_id = fields.Many2one(
        compute='_get_job_id', inverse='_set_job_id', store=True, string=u'Poste' )

    @api.one
    @api.depends("employee_id.task_id")
    def _get_task_id(self):
        if self.employee_id and self.employee_id.task_id:
            self.task_id = self.employee_id.task_id
        else:
            self.task_id = False

    @api.one
    def _set_task_id(self):
        if self.employee_id:
            self.employee_id.write(
                {'task_id': self.task_id and self.task_id.id or False})

    task_id = fields.Many2one(
        'hr.employee.task', string=u"Tâche", compute='_get_task_id', inverse='_set_task_id', store=True, )

    date_signature = fields.Date(
        string=u'Date de la signature', default=lambda self: fields.Date.today(),)
    city_signature = fields.Char(string=u'Ville',)

    @api.one
    @api.depends('trial_date_start', 'trial_date_end')
    def _compute_trial_days(self):
        days = 0
        if self.trial_date_start and self.trial_date_end:
            trial_date_start = fields.Datetime.from_string(
                self.trial_date_start)
            trial_date_end = fields.Datetime.from_string(self.trial_date_end)
            days = (trial_date_end - trial_date_start).days + 1
        self.trial_days = days

    trial_days = fields.Integer(
        string=u'Période de test', compute='_compute_trial_days',)
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        super(hr_contract, self)._onchange_employee_id()
        if not self.employee_id:
            self.date_start = fields.Date.today()
            return True
        emp_obj = self.employee_id

        self.company_id = emp_obj.company_id.id
        self.city_signature = emp_obj.company_id.main_company_id.city or ''
        self.journal_id = emp_obj.company_id.payroll_journal_id.id

        hire_date = emp_obj.hire_date or False
        if hire_date:
            self.date_start = hire_date
        contract_ids = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)], order="date_start asc")
        if contract_ids:
            contracts = contract_ids
            msg = ''
            for contract in contracts:
                msg += _('Société') + ' : ' + contract.company_id.name + '\n'
                msg += _('De') + ' : ' + contract.date_start
                if contract.date_end:
                    msg += ' '
                    msg += _('À') + ' : ' + contract.date_end
                msg += '\n'
                msg += _('Type du contrat') + ' : ' + contract.type_id.name
                msg += '\n'
                struct_id = contract.struct_id and contract.struct_id.name or ''
                msg += _('Structure du salaire') + ' : ' + struct_id
                msg += '\n'
                if contract.motif:
                    msg += _('Raison') + ' : ' + contract.motif
                    msg += '\n'
                if contract.notes:
                    msg += _('Notes') + ' : ' + contract.notes
                    msg += '\n'
                msg += '_' * 10
                msg += '\n'
        return {'warning': {'title': _('Historisue'), 'message': msg}}

    @api.onchange('salary_net_effectif')
    def _onchange_salary_net_effectif(self):
        if self.salary_net_effectif:
            self.salary_net = self.salary_net_effectif
        else:
            self.salary_net = 0

    @api.onchange('date_lic')
    def _onchange_date_lic(self):
        if self.date_lic:
            self.date_end = self.date_lic
        else:
            self.date_end = False

    @api.onchange('date_end')
    def _onchange_date_end(self):
        if self.date_end:
            self.date_lic = self.date_end
        else:
            self.date_lic = False

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.date_start and self.working_hours:
            self.update_days_hours_first_month()

    @api.onchange('working_hours')
    def _onchange_working_hours(self):
        if self.date_start and self.working_hours:
            self.update_days_hours_first_month()

    @api.multi
    def update_days_hours_first_month(self):
        for contract in self:
            if contract.date_start and contract.working_hours:
                dt_from, dt_to = date_range(self.date_start)
                dt_from = self.date_start
                day_from = datetime.datetime.strptime(dt_from, "%Y-%m-%d")
                day_to = datetime.datetime.strptime(dt_to, "%Y-%m-%d")
                nb_of_days = (day_to - day_from).days + 1
                days = hours = 0
                for day in range(0, nb_of_days):
                    current_date = day_from + datetime.timedelta(days=day)
                    working_hours_on_day = self.env['resource.calendar'].working_hours_on_day(current_date)
                    days += working_hours_on_day > 0 and 1 or 0
                    hours += working_hours_on_day
                contract.nbr_days_declared_first_month = days
                contract.nbr_hours_declared_first_month = hours


    @api.model
    def create(self, vals):
        contract = super(hr_contract, self).create(vals)
        contract.employee_id.update_rotation()
        self.update_contract_state(force_employee=contract.employee_id)
        for rubrique in contract.rubrique_ids:
            rubrique.employee_id = contract.employee_id
        return contract

    @api.multi
    def write(self, vals):
        update = False
        employees = []
        res = super(hr_contract, self).write(vals)
        for k in vals.keys():
            if k in ['date_start', 'date_end', 'trial_date_start', 'trial_date_end', 'employee_id']:
                update = True
                break
        for contract in self:
            self.update_contract_state(force_employee=contract.employee_id)
            for rubrique in contract.rubrique_ids:
                rubrique.employee_id = contract.employee_id
            if update:
                employees.append(contract.employee_id)
        for emp in employees:
            emp.update_rotation()
        return res

    @api.multi
    def unlink(self):
        employees = [x.employee_id for x in self]
        res = super(hr_contract, self).unlink()
        for emp in employees:
            emp.update_rotation()
        return res

    @api.one
    @api.depends("struct_id")
    def _compute_cnss_cimr_ok(self):
        self.update_cnss_cimr()

    @api.onchange('struct_id')
    def _onchange_struct_id(self):
        if self.struct_id:
            self.simulate_struct_id = self.struct_id.id

    cimr_ok = fields.Boolean(
        string=u'CIMR', related='struct_id.cimr_ok', store=True,  readonly=True, )
    cnss_ok = fields.Boolean(
        string=u'CNSS', related='struct_id.cnss_ok', store=True, readonly=True, )
    assurance_ok = fields.Boolean(
        string=u'Assurance', related='struct_id.assurance_ok', store=True, readonly=True, )

    @api.multi
    def get_contract_data(self) :
        return {
         'name': ' '.join((self.name, self.type_id.name, BASED_ON[self.based_on])),
         'type_id': self.type_id and self.type_id.id or False,
         'job_id': self.job_id and self.job_id.id or False,
         'based_on_id': self.based_on_id and self.based_on_id.id or False,
         'nbr_days_declared': self.nbr_days_declared,
         'nbr_hours_declared': self.nbr_hours_declared,
         'default_hours_on_worked_day': self.default_hours_on_worked_day,
         'default_hours_on_leave': self.default_hours_on_leave,
         'default_hours_on_holiday': self.default_hours_on_holiday,
         'salary_by_day': self.salary_by_day,
         'salary_by_hour': self.salary_by_hour,
         'struct_id': self.struct_id and self.struct_id.id or False,
         'wage': self.wage,
         'working_hours': self.working_hours and self.working_hours.id or False,
         'analytic_account_id': self.analytic_account_id and self.analytic_account_id.id or False,
         'voucher_mode': self.voucher_mode or False,
         'nb_holidays_by_month': self.nb_holidays_by_month or 0,
         'salary_net_effectif': self.salary_net_effectif or 0,
        }

    @api.one
    def create_template(self):
        data = self.get_contract_data()
        template_id = self.template_id.create(data)
        self.template_id = template_id.id

    @api.one
    def update_template(self):
        data = self.get_contract_data()
        if 'name' in data:
            del data['name']
        if self.template_id:
            self.template_id.write(data)


    is_contract_valid = fields.Boolean(string=u'Contrat valide',)

    def _search_valid_contracts_by_context(self, operator, value):
        def check_value_is_date(date_text):
            try:
                fields.Date.from_string(date_text)
                return True
            except:
                return False
        if operator not in ('=', '!=', '<', '<=', '>', '>=', 'in', 'not in'):
            return []
        date = self._context.get('date', time.strftime('%Y-%m-%d'))
        date_start = self._context.get('date_start', False)
        date_end = self._context.get('date_end', False)
        if isinstance(value, basestring):
            if check_value_is_date(value):
                date = value
        if isinstance(value, datetime.datetime):
            date = fields.Datetime.to_string(value)
        ids = []
        if isinstance(value, (tuple, list)) or (date_start and date_end):
            if isinstance(value, (tuple, list)):
                date_start, date_end = value[0], value[1]
        if date_end:
            contracts = self.env['hr.contract'].search(
                [('date_start', '<=', date_end)])
        else:
            contracts = self.env['hr.contract'].search(
                [('date_start', '<=', date)])
        if date_start:
            contracts = contracts.filtered(
                lambda c: not c.date_end or (c.date_end and c.date_end >= date_start))
        else:
            contracts = contracts.filtered(
                lambda c: not c.date_end or (c.date_end and c.date_end >= date))
        ids = contracts.mapped('id')
        if value:
            return [('id', 'in', ids)]
        else:
            return [('id', 'not in', ids)]

    @api.one
    def _compute_valid_contracts_by_context(self):
        self.is_contract_valid_by_context = False

    is_contract_valid_by_context = fields.Boolean(
        string=u'Contrat valide',
        search='_search_valid_contracts_by_context',
        compute='_compute_valid_contracts_by_context',
    )

    @api.one
    @api.depends("based_on_id")
    def _compute_based_on(self):
        if self.based_on_id:
            self.based_on = self.based_on_id.code
        else:
            self.based_on = False

    based_on = fields.Selection(BASED_ON_SELECTION, string=u'Basé sur', compute='_compute_based_on', store=True,
                                track_visibility='onchange',)

    based_on_id = fields.Many2one(
        'hr.contract.base', string=u'Basé sur', required=True,)

    @api.one
    @api.depends("company_id", "company_id.based_on_ids")
    def _compute_based_on_ids(self):
        if self.company_id:
            self.based_on_ids = self.company_id.based_on_ids
        else:
            self.based_on_ids = False

    based_on_ids = fields.Many2many(
        comodel_name='hr.contract.base',
        relation='hr_contract_based_on_rel',
        column1='contract_id',
        column2='based_on_id',
        string=u'Basé sur', compute='_compute_based_on_ids', store=True,)

    @api.one
    @api.depends("based_on")
    def _compute_based_on_days(self):
        if self.based_on and 'days' in self.based_on:
            self.based_on_days = True
        else:
            self.based_on_days = False

    @api.one
    @api.depends("based_on")
    def _compute_fixed_salary(self):
        if self.based_on and self.based_on in [FIXED_DAYS, FIXED_HOURS]:
            self.fixed_salary = True
        else:
            self.fixed_salary = False

    based_on_days = fields.Boolean(
        string=u'Basé sur les jours', compute='_compute_based_on_days', store=True)
    fixed_salary = fields.Boolean(
        string=u'Salaire fixe', compute='_compute_fixed_salary', store=True)

    holiday_allocation_type = fields.Selection([
        ('aucun', 'Aucune attribution automatique'),
        ('contract', 'Baser sur le nombre de jours par mois dans le contrat'),
        ('scale', 'Baser sur le nombre de jours par mois dans le tableau d\'ancienneté'),
    ], string='Méthode d\'attribution automatique de nombre de jours du congé légal', default='aucun',   )

    nb_holidays_by_month = fields.Float(
        string=u'Nombre de jours de congé légal à attribuer par mois', digits=dp.get_precision('Day'),
        track_visibility='onchange',
    )
    date_begin_holiday = fields.Date(
        string=u'Jour pour commencer à consommer les congés légaux',
        track_visibility='onchange',
    )

    simulation_result = fields.Text(string=u'Résultat',)

    @api.onchange('salary_by_hour', 'nbr_hours_declared')
    def onchange_hours_fields(self):
        self.wage = self.salary_by_hour * self.nbr_hours_declared

    @api.onchange('salary_by_day', 'nbr_days_declared')
    def onchange_days_fields(self):
        self.wage = self.salary_by_day * self.nbr_days_declared

    @api.onchange('based_on', 'wage')
    def onchange_wage_field(self):
        if self.based_on and self.company_id and self.company_id.rate_hours_on_day:
            if self.wage and self.nbr_days_declared and self.based_on in [FIXED_DAYS, WORKED_DAYS]:
                self.salary_by_day = self.wage / self.nbr_days_declared
                self.nbr_hours_declared = self.nbr_days_declared * self.company_id.rate_hours_on_day
                self.salary_by_hour = self.salary_by_day / self.company_id.rate_hours_on_day
            if self.wage and self.nbr_hours_declared and self.based_on in [FIXED_HOURS, WORKED_HOURS]:
                self.salary_by_day = (self.wage / self.nbr_hours_declared) * self.company_id.rate_hours_on_day
                self.nbr_days_declared = self.nbr_hours_declared/self.company_id.rate_hours_on_day
                self.salary_by_hour = self.wage / self.nbr_hours_declared

    @api.onchange('nbr_days_declared_first_month')
    def onchange_nbr_days_declared_first_month(self):
        if self.based_on and self.company_id and self.company_id.rate_hours_on_day:
            if self.nbr_days_declared and self.based_on in [FIXED_DAYS, WORKED_DAYS]:
                self.nbr_hours_declared_first_month = self.nbr_days_declared_first_month * self.company_id.rate_hours_on_day

    @api.onchange('nbr_hours_declared_first_month')
    def onchange_nbr_hours_declared_first_month(self):
        if self.based_on and self.company_id and self.company_id.rate_hours_on_day:
            if self.nbr_days_declared and self.based_on in [FIXED_HOURS, WORKED_HOURS]:
                self.nbr_days_declared_first_month = self.nbr_hours_declared_first_month / self.company_id.rate_hours_on_day

    default_hours_on_worked_day = fields.Float(
        string=u'Nombre d\'heures dans un jour travaillé',
        digits=dp.get_precision('Salary Rate'),
        default=lambda self: self.env.user.company_id.default_hours_on_worked_day,
        track_visibility='onchange',
        help='C\'est une valeur par défaut utilisé dans un jour travaillé',
    )
    default_hours_on_holiday = fields.Float(
        string=u'Nombre d\'heures dans un jour férié',
        digits=dp.get_precision('Salary Rate'),
        default=lambda self: self.env.user.company_id.default_hours_on_holiday,
        track_visibility='onchange',
        help='C\'est une valeur par défaut utilisé dans un jour férié mais travaillé',
    )
    default_hours_on_leave = fields.Float(
        string=u'Nombre d\'heures dans un congé',
        digits=dp.get_precision('Salary Rate'),
        default=lambda self: self.env.user.company_id.default_hours_on_leave,
        track_visibility='onchange',
        help='C\'est une valeur par défaut utilisé dans un congé',
    )
    nbr_days_declared_first_month = fields.Float(
        string=u'Nombre de jours déclaré pour le 1èr mois',
        digits=dp.get_precision('Salary'),
        default=lambda self: self.env.user.company_id.nbr_days_declared,
        track_visibility='onchange',
    )
    nbr_days_declared = fields.Float(
        string=u'Nombre de jours déclaré',
        digits=dp.get_precision('Salary'),
        default=lambda self: self.env.user.company_id.nbr_days_declared,
        track_visibility='onchange',
    )
    nbr_hours_declared = fields.Float(
        string=u'Nombre d\'heures déclaré',
        digits=dp.get_precision('Salary'),
        default=lambda self: self.env.user.company_id.nbr_hours_declared,
        track_visibility='onchange',
    )
    nbr_hours_declared_first_month = fields.Float(
        string=u'Nombre d\'heures déclaré pour le 1èr mois',
        digits=dp.get_precision('Salary'),
        default=lambda self: self.env.user.company_id.nbr_hours_declared,
        track_visibility='onchange',
    )
    salary_by_day = fields.Float(
        string=u'Salaire journalier', digits=dp.get_precision('Salary Rate'),
        track_visibility='onchange',
    )
    salary_by_hour = fields.Float(
        string=u'Salaire horaire', digits=dp.get_precision('Salary Rate'),
        track_visibility='onchange',
    )
    wage = fields.Float(string=u"Salaire de base", required=False,
                        track_visibility='onchange', digits=dp.get_precision('Salary'),)

    date_start_cron = fields.Date(string=u'Date pour commencer l\'attribution automatique du nombre de jours pour les congés légaux',
                                  track_visibility='onchange', default=lambda self: time.strftime('%Y-%m-20'), )
    date_lic = fields.Date(string=u'Date licenciement',
                           track_visibility='onchange',)
    motif = fields.Text(string=u'Motif',
                        track_visibility='onchange',)
    preavis_duration = fields.Float(string=u'Durée du préavis',
                                    track_visibility='onchange', digits=dp.get_precision('Account'), )
    observation_preavis_duration = fields.Float(string=u'Durée d\'observation du préavis',
                                                track_visibility='onchange', digits=dp.get_precision('Account'),)
    minimal_duration = fields.Float(string=u'Durée minimal',
                                    track_visibility='onchange', digits=dp.get_precision('Account'),)

    @api.onchange('company_id')
    def _onchange_company_id(self) :
        if self.company_id:
            self.default_hours_on_worked_day = self.company_id.default_hours_on_worked_day
            self.default_hours_on_holiday = self.company_id.default_hours_on_holiday
            self.default_hours_on_leave = self.company_id.default_hours_on_leave
            if self.based_on and self.based_on in [FIXED_DAYS, WORKED_DAYS, ATTENDED_DAYS, TIMESHEET_DAYS]:
                self.nbr_days_declared = self.company_id.nbr_days_declared
            if self.based_on and self.based_on in [FIXED_HOURS, WORKED_HOURS, ATTENDED_HOURS, TIMESHEET_HOURS]:
                self.nbr_hours_declared = self.company_id.nbr_hours_declared

    company_id = fields.Many2one('res.company', string=u'Société',
                                 track_visibility='onchange',
                                 required=True,  )

    preavis_nbr_renew = fields.Integer(
        string=u'Nombre de renouvelement de préavis',)

    article_ids = fields.Many2many(
        'hr.contract.article', string=u"Autres articles", track_visibility='onchange')

    solde_tout_compte = fields.Date(
        string=u'Date solde de tout compte', track_visibility='onchange', )
    prime_licenciement = fields.Float(string=u'Prime de licenciement', digits=dp.get_precision(
        'Account'), track_visibility='onchange',)
    prime_preavis = fields.Float(string=u'Prime de préavis', digits=dp.get_precision(
        'Account'), track_visibility='onchange',)
    stc_worked_days = fields.Float(string=u'Jours travaillés', digits=dp.get_precision(
        'Account'), track_visibility='onchange',)
    stc_worked_hours = fields.Float(string=u'Heures travaillés', digits=dp.get_precision(
        'Account'), track_visibility='onchange',)
    remaining_leaves = fields.Float(string=u'Congés restant', digits=dp.get_precision(
        'Account'), track_visibility='onchange', )

    # SIMULATION

    simulate_elements_ok = fields.Boolean(string=u'Simulation des éléments du salaire',  default=False )
    simulate_hire_date_ok = fields.Boolean(string=u'Simulation en utilisant la date d\'embauche',  default=True )

    simulate_salary_by_day = fields.Float(
        string=u'Salaire journalier', digits=dp.get_precision('Salary Rate'), readonly=True,
    )
    simulate_salary_by_hour = fields.Float(
        string=u'Salaire horaire', digits=dp.get_precision('Salary Rate'), readonly=True,
    )
    simulate_wage = fields.Float(
        string=u'Salaire de base', digits=dp.get_precision('Salary'),  readonly=True, )

    salary_net_effectif = fields.Float(
        string=u'Salaire Net', digits=dp.get_precision('Salary'),)

    salary_net = fields.Float(
        string=u'Salaire Net', digits=dp.get_precision('Salary'),)

    simulate_found_salary_net = fields.Float(
        string=u'Salaire Net', digits=dp.get_precision('Salary'), readonly=True, )

    simulate_found_salary_brut = fields.Float(
        string=u'Salaire brut', digits=dp.get_precision('Salary'), readonly=True, )

    salary_net_imposable = fields.Float(
        string=u'Net imposable', digits=dp.get_precision('Salary'),)

    salary_net_contractuel = fields.Float(
        string=u'Net contractuel', digits=dp.get_precision('Salary'),)

    salary_brut = fields.Float(
        string=u'Brut', digits=dp.get_precision('Salary'),)

    salary_brut_imposable = fields.Float(
        string=u'Brut imposable', digits=dp.get_precision('Salary'),)

    salary_net_inverse = fields.Float(
        string=u'Salaire Net', digits=dp.get_precision('Salary'),)

    simulate_struct_id = fields.Many2one(
        'hr.payroll.structure', string=u'Structure salariale',)

    simulate_without_arrondi = fields.Boolean(string=u'Simuler sans arrondi',  default=True )

    last_simulation_date = fields.Datetime(string=u'Dernière simulation',  readonly=True, )
    number_of_iteration = fields.Integer(string=u'Nombre des itérations',  readonly=True, )

    @api.one
    def use_simulated_data(self):
        data = {
            'salary_by_day': self.simulate_salary_by_day,
            'salary_by_hour': self.simulate_salary_by_hour,
            'wage': self.simulate_wage,
            'struct_id': self.simulate_struct_id.id,
            'salary_net_effectif': self.simulate_found_salary_net,
        }
        self.write(data)
        self.onchange_wage_field()


    @api.one
    def simulate_salary_net_inverse(self):
        if not self.simulate_struct_id:
            raise Warning(
            _("Veuillez spécifier une structure de salaire à utiliser"))
        self = self.with_context(dict(self.env.context), simulation=True, simulate_elements_ok=self.simulate_elements_ok, structure_ids=[self.simulate_struct_id.id])
        date_to_use = self.simulate_hire_date_ok and self.employee_id.hire_date or fields.Date.today()
        date_start = date_to_use[:8] + '01'
        date_stop = date_to_use[
            :8] + str(calendar.monthrange(int(date_to_use[:4]), int(date_to_use[5:7]))[1])
        slip = self.env['hr.payslip'].create({
            'date_from': date_start,
            'date_to': date_stop,
            'employee_id': self.employee_id.id,
            'struct_id': self.simulate_struct_id.id,
            'contract_id': self.id,
            'journal_id': self.env['account.journal'].search([], limit=1).id,
            'voucher_mode': self.voucher_mode,
            'simulation_ok': True,
            'simulate_elements_ok' : self.simulate_elements_ok,
        })
        data = slip.onchange_employee_id(
            date_from=date_start,
            date_to=date_stop,
            employee_id=self.employee_id.id,
            contract_id=self.id
        ).get('value', {})
        worked_days_line_ids = data.get('worked_days_line_ids', [])
        worked_days_line_ids = [(0, 0, x) for x in worked_days_line_ids]
        data['worked_days_line_ids'] = worked_days_line_ids
        input_line_ids = data.get('input_line_ids', [])
        input_line_ids = [(0, 0, x) for x in input_line_ids]
        data['input_line_ids'] = input_line_ids
        data.update({
            'struct_id': self.simulate_struct_id.id,
            'voucher_mode': self.voucher_mode,
        })
        slip.write(data)
        if not slip.contract_id:
            raise Warning(_('Aucun contrat valide pour la période de  [%s]') % (date_start[5:7]+'/'+date_start[:4]))
        slip.compute_sheet()
        self.salary_net_inverse = slip.salary_net
        slip.unlink()

    @api.one
    def simulate_salary_brut(self):
        ctx = self.env.context.copy()
        ctx.update({
            'field_contract': 'salary_brut',
            'field_payslip': 'salary_brut',
        })
        self.with_context(ctx).simulate_salary_net()

    @api.one
    def simulate_salary_brut_imposable(self):
        ctx = self.env.context.copy()
        ctx.update({
            'field_contract': 'salary_brut_imposable',
            'field_payslip': 'salary_brut_imposable',
        })
        self.with_context(ctx).simulate_salary_net()

    @api.one
    def simulate_salary_net_imposable(self):
        ctx = self.env.context.copy()
        ctx.update({
            'field_contract': 'salary_net_imposable',
            'field_payslip': 'salary_net_imposable',
        })
        self.with_context(ctx).simulate_salary_net()

    @api.one
    def simulate_salary_net_contractuel(self):
        ctx = self.env.context.copy()
        ctx.update({
            'field_contract': 'salary_net_contractuel',
            'field_payslip': 'salary_net_contractuel',
        })
        self.with_context(ctx).simulate_salary_net()

    @api.one
    def simulate_salary_net(self):
        if not self.simulate_struct_id:
            raise Warning(
            _("Veuillez spécifier une structure de salaire à utiliser"))
        self = self.with_context(dict(self.env.context), simulation=True, simulate_elements_ok=self.simulate_elements_ok, structure_ids=[self.simulate_struct_id.id])
        _logger.info("Simulation of [%s]. Started" % self.env.context.get(
            'field_contract', 'salary_net'))
        start_time = time.time()
        coeff = 2
        if self.simulate_elements_ok:
            coeff = 30
        field_contract = self.env.context.get('field_contract', 'salary_net')
        field_payslip = self.env.context.get('field_payslip', 'salary_net')
        MAX_WAGE = (getattr(self, field_contract) * coeff)/self.nbr_days_declared
        MAX_SALARY_BY_DAY, MIN_SALARY_BY_DAY = MAX_WAGE, 0.0
        MAX_SALARY_BY_HOUR, MIN_SALARY_BY_HOUR = MAX_WAGE / self.company_id.rate_hours_on_day, 0.0
        if self.based_on not in [FIXED_DAYS, FIXED_HOURS, WORKED_DAYS, WORKED_HOURS]:
            raise Warning(
                _("La simulation est possible juste pour les salaires fixes"))
        if self.based_on in [FIXED_DAYS, WORKED_DAYS]:
            if self.nbr_days_declared <= 0:
                raise Warning(_("Veuillez spécifier le nombre de jours déclaré"))
        if self.based_on in [FIXED_HOURS, WORKED_HOURS]:
            if self.nbr_hours_declared <= 0:
                raise Warning(_("Veuillez spécifier le nombre d\'heures déclaré"))
        date_to_use = self.simulate_hire_date_ok and self.employee_id.hire_date or fields.Date.today()
        date_start = date_to_use[:8] + '01'
        date_stop = date_to_use[
            :8] + str(calendar.monthrange(int(date_to_use[:4]), int(date_to_use[5:7]))[1])
        slip = self.env['hr.payslip'].create({
            'date_from': date_start,
            'date_to': date_stop,
            'employee_id': self.employee_id.id,
            'contract_id': self.id,
            'struct_id': self.simulate_struct_id.id,
            'journal_id': self.env['account.journal'].search([], limit=1).id,
            'voucher_mode': self.voucher_mode,
            'simulation_ok': True,
            'simulate_elements_ok' : self.simulate_elements_ok,
            'without_arrondi' : self.simulate_without_arrondi,
        })
        data = slip.onchange_employee_id(
            date_from=date_start,
            date_to=date_stop,
            employee_id=self.employee_id.id,
            contract_id=self.id
        ).get('value', {})
        worked_days_line_ids = data.get('worked_days_line_ids', [])
        worked_days_line_ids = [(0, 0, x) for x in worked_days_line_ids]
        data['worked_days_line_ids'] = worked_days_line_ids
        input_line_ids = data.get('input_line_ids', [])
        input_line_ids = [(0, 0, x) for x in input_line_ids]
        data['input_line_ids'] = input_line_ids
        data.update({
            'voucher_mode': self.voucher_mode,
            'struct_id': self.simulate_struct_id.id,
        })
        slip.write(data)
        declared_hours = self.nbr_hours_declared
        declared_days = self.nbr_days_declared
        # Initialisation
        found = False
        number_of_iteration = 0
        founds = []
        while not found:
            number_of_iteration += 1
            AVG_SALARY_BY_DAY = (MAX_SALARY_BY_DAY + MIN_SALARY_BY_DAY) / 2.
            AVG_SALARY_BY_HOUR = (MAX_SALARY_BY_HOUR + MIN_SALARY_BY_HOUR) / 2.
            out = 0
            for work_day in slip.worked_days_line_ids:
                if work_day.code == ATTENDANCE_MAJ :
                    work_day.number_of_days = declared_days
                    work_day.number_of_hours = declared_hours
                    out += 1
                if out == 1 :
                    break
            out = 0
            for input_line in slip.input_line_ids:
                if input_line.code == SALAIRE_PAR_JOUR :
                    input_line.amount = AVG_SALARY_BY_DAY
                    out += 1
                if input_line.code == SALAIRE_PAR_HEURE :
                    input_line.amount = AVG_SALARY_BY_HOUR
                    out += 1
                if out == 2 :
                    break
            slip.compute_sheet()
            _logger.info("Iteration:[%d], Need:[%s], Found=[%s]",number_of_iteration, getattr(self, field_contract),getattr(slip, field_payslip))
            if getattr(slip, field_payslip) == 0:
                raise Warning(_('We get a Zero in the result !'))
            if getattr(self, field_contract) > getattr(slip, field_payslip):
                MIN_SALARY_BY_DAY = AVG_SALARY_BY_DAY
                MIN_SALARY_BY_HOUR = AVG_SALARY_BY_HOUR
            elif getattr(self, field_contract) < getattr(slip, field_payslip):
                MAX_SALARY_BY_DAY = AVG_SALARY_BY_DAY
                MAX_SALARY_BY_HOUR = AVG_SALARY_BY_HOUR
            else:
                found = True
            if getattr(slip, field_payslip) in founds:
                found = True
            founds.append(getattr(slip, field_payslip))
        elapsed_time = time.time() - start_time
        _logger.info("Simulation of the wage. Finished")
        simulate_salary_by_day = 0
        simulate_salary_by_hour = 0
        simulate_wage = 0
        if self.based_on_days:
            simulate_salary_by_day = AVG_SALARY_BY_DAY
            simulate_salary_by_hour = AVG_SALARY_BY_HOUR
            simulate_wage = AVG_SALARY_BY_DAY * declared_days
        else:
            simulate_salary_by_day = AVG_SALARY_BY_DAY
            simulate_salary_by_hour = AVG_SALARY_BY_HOUR
            simulate_wage = AVG_SALARY_BY_HOUR * declared_hours
        simulate_found_salary_net, simulate_found_salary_brut = slip.salary_net, slip.salary_brut
        self.write({
            'simulate_salary_by_day': simulate_salary_by_day,
            'simulate_salary_by_hour': simulate_salary_by_hour,
            'simulate_wage': simulate_wage,
            'simulate_found_salary_net': simulate_found_salary_net,
            'simulate_found_salary_brut': simulate_found_salary_brut,
            'last_simulation_date': fields.Datetime.now() ,
            'number_of_iteration': number_of_iteration ,
        })
        slip.unlink()
        _logger.info("Simulation of the wage. time elapsed [%s] number of iteration is [%s]" % (
            elapsed_time, number_of_iteration))

    @api.model
    def generate_payslip(self, ids,  month=False, year=False):
        self = self.browse(ids)
        for contract in self:
            today = fields.Date.today()
            _year = today[:4]
            _month = today[5:7]
            if month:
                _month = str(month).rjust(2, '0')
            if year:
                _year = str(year)
            date_start = _year + '-' + _month + '-' + '01'
            date_stop = date_start[
                :8] + str(calendar.monthrange(int(_year), int(_month))[1])
            slip = self.env['hr.payslip'].search([
                ('employee_id', '=', contract.employee_id.id),
                ('contract_id', '=', False),
                ('struct_id', '=', False),
                ('date_from', '=', date_start),
                ('date_to', '=', date_stop),
            ])
            if slip:
                raise Warning(
                    _('A payslip without contract is found on this period'))
            slip = self.env['hr.payslip'].search([
                ('employee_id', '=', contract.employee_id.id),
                ('contract_id', '=', contract.id),
                ('struct_id', '=', contract.struct_id.id),
                ('date_from', '=', date_start),
                ('date_to', '=', date_stop),
            ])
            if slip:
                return False
            slip = self.env['hr.payslip'].create({
                'employee_id': contract.employee_id.id,
                'contract_id': contract.id,
                'struct_id': contract.struct_id.id,
                'journal_id': contract.employee_id.company_id.main_company_id.id,
                'voucher_mode': contract.voucher_mode,
                'date_from': date_start,
                'date_to': date_stop,
            })

            data = slip.onchange_employee_id(
                date_from=date_start,
                date_to=date_stop,
                employee_id=contract.employee_id.id,
                contract_id=contract.id
            ).get('value', {})
            worked_days_line_ids = data.get('worked_days_line_ids', [])
            worked_days_line_ids = [(0, 0, x) for x in worked_days_line_ids]
            data['worked_days_line_ids'] = worked_days_line_ids
            input_line_ids = data.get('input_line_ids', [])
            input_line_ids = [(0, 0, x) for x in input_line_ids]
            data['input_line_ids'] = input_line_ids
            slip.write(data)

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id:
            self.show_field_start = self.type_id.show_field_start
            self.required_field_start = self.type_id.required_field_start
            self.show_field_stop = self.type_id.show_field_stop
            self.required_field_stop = self.type_id.required_field_stop
            if self.type_id.empty_field_start:
                self.date_start = False
            if self.type_id.empty_field_stop:
                self.date_end = False
        else:
            self.date_end = False
            self.show_field_stop = True

    show_field_start = fields.Boolean(string=u'Show date start',
                                      default=True,
                                      store=True, )
    required_field_start = fields.Boolean(
        string=u'Date start is required',
        default=True,
    )
    show_field_stop = fields.Boolean(
        string=u'Show date stop',
        default=True,
    )
    required_field_stop = fields.Boolean(
        string=u'Date stop is required',
        default=False,
    )

    @api.onchange('template_id')
    def onchange_template_id(self):
        if self.template_id:
            if self.template_id.based_on_id:
                self.based_on_id = self.template_id.based_on_id and self.template_id.based_on_id.id or False
            if self.template_id.nbr_days_declared:
                self.nbr_days_declared = self.template_id.nbr_days_declared
            if self.template_id.nbr_hours_declared:
                self.nbr_hours_declared = self.template_id.nbr_hours_declared
            if self.template_id.salary_by_day:
                self.salary_by_day = self.template_id.salary_by_day
            if self.template_id.salary_by_hour:
                self.salary_by_hour = self.template_id.salary_by_hour
            if self.template_id.struct_id:
                self.struct_id = self.template_id.struct_id
            if self.template_id.job_id:
                self.job_id = self.template_id.job_id
            if self.template_id.type_id:
                self.type_id = self.template_id.type_id
            if self.template_id.wage:
                self.wage = self.template_id.wage
            if self.template_id.working_hours:
                self.working_hours = self.template_id.working_hours
            if self.template_id.analytic_account_id:
                self.analytic_account_id = self.template_id.analytic_account_id.id
            if self.template_id.voucher_mode:
                self.voucher_mode = self.template_id.voucher_mode
            if self.template_id.nb_holidays_by_month:
                self.nb_holidays_by_month = self.template_id.nb_holidays_by_month
            if self.template_id.default_hours_on_worked_day:
                self.default_hours_on_worked_day = self.template_id.default_hours_on_worked_day
            if self.template_id.default_hours_on_holiday:
                self.default_hours_on_holiday = self.template_id.default_hours_on_holiday
            if self.template_id.default_hours_on_leave:
                self.default_hours_on_leave = self.template_id.default_hours_on_leave
            if self.template_id.salary_net_effectif:
                self.salary_net_effectif = self.template_id.salary_net_effectif

    template_id = fields.Many2one('hr.contract.template', string=u'Template', track_visibility='onchange')
    auto_change_template = fields.Boolean(string=u'Auto change template', default=False )

    @api.onchange('auto_change_template')
    def _onchange_auto_change_template(self) :
        if self.auto_change_template:
             self.onchange_template_id()
             self.auto_change_template = False
    # @api.one
    # @api.constrains('wage')
    # def _check_wage(self):
    #     if round(self.wage) != round(self.nbr_days_declared *
    #                                  self.salary_by_day) or \
    #             round(self.wage) != round(self.nbr_hours_declared *
    #                                       self.salary_by_hour):
    #         raise Warning(
    #             _('The wage should be [number of hours * the salary by hour]'
    #               'and [number of days declared * the salary by day]'))

    rubrique_ids = fields.One2many('hr.rubrique.line', 'contract_id', string=u'Rubriques',  )

    # CRON
    @api.multi
    def update_contract_state(self, force_employee=False, from_cron=False):
        domain = []
        if force_employee:
            if not isinstance(force_employee, (int, long)):
                force_employee = force_employee.id
            domain = [('id', '=', force_employee)]
        for employee in self.env['hr.employee'].search(domain):
            if from_cron and employee.update_contract_state_update and employee.update_contract_state_update == fields.Date.today():
                continue
            current_contract_id = False
            first_contract_id = False
            hire_date = employee.hire_date
            for contract in self.env['hr.contract'].search([
                    ('employee_id', '=', employee.id)], order='date_start asc'):
                today = fields.Date.today()
                is_contract_valid = False
                if contract.date_start and contract.date_end:
                    if contract.date_start <= today and today <= contract.date_end:
                        is_contract_valid = True
                        current_contract_id = contract.id
                        first_contract_id = first_contract_id or contract.id
                elif contract.date_start:
                    if contract.date_start <= today:
                        is_contract_valid = True
                        current_contract_id = contract.id
                        first_contract_id = first_contract_id or contract.id
                elif contract.date_end:
                    if today <= contract.date_end:
                        is_contract_valid = True
                        current_contract_id = contract.id
                        first_contract_id = first_contract_id or contract.id
                else:
                    is_contract_valid = True
                    current_contract_id = contract.id
                    first_contract_id = first_contract_id or contract.id
                if contract.is_contract_valid != is_contract_valid:
                    contract.is_contract_valid = is_contract_valid
            if first_contract_id:
                first_time = self.env['hr.contract'].browse(
                    first_contract_id).date_start
                today = fields.Date.today()
                hire_date = first_time or False
            employee.write({
                'current_contract_id': current_contract_id,
                'first_contract_id': first_contract_id,
                'hire_date': hire_date,
                'update_contract_state_update': fields.Date.today() ,
            })

    @api.constrains('date_start','date_end')
    def _check_date_start_date_end(self):
        contracts = self.search([('employee_id','=',self.employee_id.id)], order='date_start asc')
        tab = []
        for c in contracts:
            if tab:
                if tab[-1][1] == False:
                    raise Warning(_('Veuillez clôturer le contrat [%s]') % tab[-1][2])
                if c.date_start <= tab[-1][1]:
                    raise Warning(_('Date de début doit être après [%s]') % tab[-1][1])
            tab.append((c.date_start, c.date_end, c.name))


class hr_contract_article(models.Model):
    _name = 'hr.contract.article'
    _description = 'Articles'

    sequence = fields.Integer(string=u'Séquence',)
    name = fields.Text(string=u'Description',  required=True, )


class hr_contract_type(models.Model):
    _inherit = 'hr.contract.type'

    show_field_start = fields.Boolean(
        string=u'Afficher date début',
        default=True,
    )
    required_field_start = fields.Boolean(
        string=u'Date début obligatoire',
        default=True,
    )
    empty_field_start = fields.Boolean(
        string=u'Date début vide',
        default=False,
    )
    show_field_stop = fields.Boolean(
        string=u'Afficher date fin',
        default=True,
    )
    required_field_stop = fields.Boolean(
        string=u'Date fin obligatoire',
        default=False,
    )
    empty_field_stop = fields.Boolean(
        string=u'Date fin vide',
        default=False,
    )

    type = fields.Selection([
        ('permanent', 'Permanent'),
        ('occasional', 'Occasionnel'),
        ('trainee', 'Stagiaire'),
    ], string=u'Type',)
