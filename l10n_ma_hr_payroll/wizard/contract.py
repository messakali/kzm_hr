# encoding: utf-8

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning
from odoo.addons.l10n_ma_hr_payroll.models.variables import *


class hr_contract_wizard(models.TransientModel):
    _name = 'hr.contract.wizard'

    @api.one
    @api.onchange('wage', 'nbr_hours_declared', 'nbr_days_declared')
    def onchange_wage_nbrs(self):
        self.salary_by_day = self.nbr_days_declared > 0 and \
            self.wage / self.nbr_days_declared or 0.0

        self.salary_by_hour = self.nbr_hours_declared > 0 and \
            self.wage / self.nbr_hours_declared or 0.0


    default_hours_on_worked_day = fields.Float(
        string=u'Nombre d\'heures dans un jour travaillé',
        digits=dp.get_precision('Salary Rate'),
        default=lambda self: self.env.user.company_id.default_hours_on_worked_day,
        track_visibility='onchange',
        help='C\'est une valeur par défaut utilisé dans un jour férié mais travaillé',
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
    salary_by_day = fields.Float(
        string=u'Salaire journalier', digits=dp.get_precision('Salary Rate'),
        track_visibility='onchange',
    )
    salary_by_hour = fields.Float(
        string=u'Salaire horaire', digits=dp.get_precision('Salary Rate'),
        track_visibility='onchange',
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
    date_start_cron = fields.Date(string=u'Date pour commencer l\'attribution automatique du nombre de jours pour les congés légaux')
    preavis_duration = fields.Integer(string=u'Durée du préavis',)

    type_id = fields.Many2one(
        'hr.contract.type', string=u'Type du contrat', required=True)
    based_on_id = fields.Many2one(
        'hr.contract.base', string=u'Basé sur', required=True,)

    struct_id = fields.Many2one(
        'hr.payroll.structure', string=u'Structure du salaire', required=True)
    wage = fields.Float(
        string=u'Salaire de base', digits=dp.get_precision('Salary'), required=True, )
    working_hours = fields.Many2one(
        'resource.calendar', string=u'Temps de travail',)

    voucher_mode = fields.Selection([
        ('ES', u'Espèces'),
        ('CH', u'Chèque'),
        ('VIR', u'Virement'),
    ], string=u'Mode de règlement', required=True, )

    company_id = fields.Many2one(
        'res.company', string=u'Société', required=True,)

    trial_date_start = fields.Date('Date début de la période de test')
    trial_date_end = fields.Date(string=u'Date fin de la période de test')

    salary_net_effectif = fields.Float(
        string=u'Salaire net', digits=dp.get_precision('Salary'),)

    date_start = fields.Date(string=u'Date début', required=True)
    date_end = fields.Date(string=u'Date fin')

    nb_holidays_by_month = fields.Float(
        string=u'Nombre de jours de congé légal à attribuer par mois', digits=dp.get_precision('Day'),
    )
    date_begin_holiday = fields.Date(
        string=u'Jour pour commencer à consommer les congés légaux',
    )

    @api.multi
    def action_generate(self):
        self.ensure_one()
        employees = self.env['hr.employee'].browse(
            self._context.get('active_ids', []))
        res = []
        for employee in employees:
            company = employee.company_id
            data = {
                'employee_id': employee.id,
                'job_id': employee.job_id and employee.job_id.id or False,
                'nbr_days_declared': self.nbr_days_declared,
                'nbr_hours_declared': self.nbr_hours_declared,
                'default_hours_on_worked_day': self.default_hours_on_worked_day,
                'default_hours_on_holiday': self.default_hours_on_holiday,
                'default_hours_on_leave': self.default_hours_on_leave,
                'salary_by_day': self.salary_by_day,
                'salary_by_hour': self.salary_by_hour,
                'date_start_cron': self.date_start_cron,
                'preavis_duration': self.preavis_duration,
                'type_id': self.type_id.id,
                'based_on_id': self.based_on.id,
                'salary_net_effectif': self.salary_net_effectif,
                'struct_id': self.struct_id.id,
                'wage': self.wage,
                'working_hours': self.working_hours.id,
                'voucher_mode': self.voucher_mode,
                'trial_date_start': self.trial_date_start,
                'trial_date_end': self.trial_date_end,
                'date_start': self.date_start,
                'date_end': self.date_end,
                'nb_holidays_by_month': self.nb_holidays_by_month,
                'date_begin_holiday': self.date_begin_holiday,
                'company_id': self.company_id.id,
            }
            res.append(self.env['hr.contract'].create(data).id)
        return {
            'name': _('Contrats générés'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.contract',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res)]
        }


class hr_contract_close(models.TransientModel):
    _name = 'hr.contract.close'

    date = fields.Date(string=u'Date',  required=True, default=lambda self: fields.Date.today()  )
    motif = fields.Text(string=u'Motif',)

    solde_tout_compte = fields.Boolean(string=u'Solde de tout compte',)

    prime_licenciement = fields.Float(string=u'Prime de licenciement', digits=dp.get_precision('Account'),  )
    prime_preavis = fields.Float(string=u'Prime de préavis', digits=dp.get_precision('Account'),  )

    declared_period = fields.Float(string=u'Déclaré dans la période', digits=dp.get_precision('Account'),  )
    minus_period = fields.Float(string=u'À déduire dans la période', digits=dp.get_precision('Account'),  )
    @api.one
    @api.depends("declared_period","minus_period")
    def _compute_period(self):
        self.period = self.declared_period - self.minus_period

    period = fields.Float(string=u'Période travaillée', digits=dp.get_precision('Account'), compute='_compute_period', store=True,    )
    based_on = fields.Selection(BASED_ON_SELECTION, string=u'Basé sur', default=WORKED_DAYS )

    legal_leaves = fields.Float(string=u'Congés pris', digits=dp.get_precision('Account'),  default=0.0)
    legal_leaves_addon = fields.Float(string=u'Complément des congés pris', digits=dp.get_precision('Account'), default=0.0,   )

    @api.one
    @api.depends("legal_leaves","legal_leaves_addon")
    def _compute_remaining_leaves(self):
        self.remaining_leaves = self.legal_leaves + self.legal_leaves_addon

    remaining_leaves = fields.Float(string=u'Reste des congés', digits=dp.get_precision('Account'),  compute='_compute_remaining_leaves', store=True,   )


    @api.model
    def default_get(self, fields):
        res = super(hr_contract_close, self).default_get(fields)
        contract_id = self.env.context.get('active_id', False)
        if contract_id:
            contract = self.env['hr.contract'].browse(contract_id)
            res['declared_period'] = contract.based_on_days and contract.nbr_days_declared or contract.nbr_hours_declared
            res['based_on'] = contract.based_on
            res['legal_leaves'] = contract.employee_id.remaining_leaves
        return res


    @api.multi
    def action_generate(self):
        self.ensure_one()
        contracts = self.env['hr.contract'].browse(
            self._context.get('active_ids', []))
        for contract in contracts:
            data = {
                'date_end': self.date,
                'date_lic': self.date,
                'motif': self.motif,
                'prime_preavis': self.prime_preavis,
                'prime_licenciement': self.prime_licenciement,
                'remaining_leaves': self.remaining_leaves,
                'stc_worked_days' : contract.based_on_days and self.period or  (self.period/contract.default_hours_on_worked_day),
                'stc_worked_hours' : contract.based_on_days and (self.period*contract.default_hours_on_worked_day) or self.period,
            }
            if self.solde_tout_compte:
                # We will test if date exists on the contract
                data.update({'solde_tout_compte': self.date})
            contract.write(data)
            contract.employee_id.message_post(
                _('Contrat à clôturé à la date de %s\nMotif : %s') % (self.date, self.motif or '',))
