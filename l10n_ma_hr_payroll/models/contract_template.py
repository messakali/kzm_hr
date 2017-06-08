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



_logger = logging.getLogger(__name__)




class hr_contract_template(models.Model):
    _name = 'hr.contract.template'

    name = fields.Char(string=u'Nom', size=64, required=True)
    type_id = fields.Many2one('hr.contract.type', string=u'Type du contrat',)
    job_id = fields.Many2one('hr.job', string=u'Poste',)
    based_on_id = fields.Many2one('hr.contract.base', string=u'Basé sur',)

    nbr_days_declared = fields.Float(
        string=u'Nombre de jours déclaré', digits=dp.get_precision('Salary'),
    )
    default_hours_on_worked_day = fields.Float(
        string=u'Nombre d\'heures dans un jour travaillé', digits=dp.get_precision('Salary Rate'),
    )
    default_hours_on_leave = fields.Float(
        string=u'Nombre d\'heures dans un jour congé', digits=dp.get_precision('Salary Rate'),
    )
    default_hours_on_holiday = fields.Float(
        string=u'Nombre d\'heures dans un jour férié', digits=dp.get_precision('Salary Rate'),
    )
    nbr_hours_declared = fields.Float(
        string=u'Nombre d\'heures déclaré', digits=dp.get_precision('Salary'),
    )
    salary_by_day = fields.Float(
        string=u'Salaire journalier', digits=dp.get_precision('Salary Rate'),
    )
    salary_by_hour = fields.Float(
        string=u'Salaire horaire', digits=dp.get_precision('Salary Rate'),
    )
    struct_id = fields.Many2one(
        'hr.payroll.structure', string=u'Structure du salaire',)

    @api.onchange('salary_by_hour', 'nbr_hours_declared')
    def onchange_hours_fields(self):
        self.wage = self.salary_by_hour * self.nbr_hours_declared


    @api.one
    @api.depends("based_on_id")
    def _compute_based_on(self):
        if self.based_on_id:
            self.based_on = self.based_on_id.code
        else:
            self.based_on = False

    based_on = fields.Selection(BASED_ON_SELECTION, string=u'Basé sur', compute='_compute_based_on', store=True,)

#     @api.one
#     @api.onchange('salary_by_hour', 'nbr_hours_declared')
#     def onchange_hours_fields(self):
#         self.wage = self.salary_by_hour * self.nbr_hours_declared

    @api.onchange('salary_by_day', 'nbr_days_declared')
    def onchange_days_fields(self):
        self.wage = self.salary_by_day * self.nbr_days_declared

    @api.onchange('based_on', 'wage')
    def onchange_wage_field(self):
        rate_hours_on_day = self.env.user.company_id.main_company_id.rate_hours_on_day
        if self.based_on :
            if self.wage and self.nbr_days_declared and self.based_on in [FIXED_DAYS, WORKED_DAYS]:
                self.salary_by_day = self.wage / self.nbr_days_declared
                self.nbr_hours_declared = self.nbr_days_declared * rate_hours_on_day
                self.salary_by_hour = self.salary_by_day / rate_hours_on_day
            if self.wage and self.nbr_hours_declared and self.based_on in [FIXED_HOURS, WORKED_HOURS]:
                self.salary_by_day = (self.wage / self.nbr_hours_declared) * rate_hours_on_day
                self.nbr_days_declared = self.nbr_hours_declared/rate_hours_on_day
                self.salary_by_hour = self.wage / self.nbr_hours_declared

    wage = fields.Float(
        string=u'Salaire de base', digits=dp.get_precision('Salary'),)
    working_hours = fields.Many2one(
        'resource.calendar', string=u'Temps de travail',)

    voucher_mode = fields.Selection([
        ('ES', u'Espèces'),
        ('CH', u'Chèque'),
        ('VIR', u'Virement'),
    ], string=u'Mode de règlement', required=False, )
    salary_net_effectif = fields.Float(
        string=u'Salaire net', digits=dp.get_precision('Net Salary'),)

    analytic_account_id = fields.Many2one(
        'account.analytic.account', string=u'Compte analytique',)

    nb_holidays_by_month = fields.Float(
        string=u'Nombre de jours pour congé légal dans un mois', digits=dp.get_precision('Day'),)
