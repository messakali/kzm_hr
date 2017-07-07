# encoding: utf-8

from odoo import models, fields, api, _
from datetime import datetime
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning


class mass_attendance_run(models.Model):
    _name = 'hr.employee.mass.attendance.run'
    _description = 'Lot de pointage en masse'
    _rec_name = 'company_id'
    _order = 'date_from desc'

    name = fields.Char(string=u'Nom', size=64,)

    fiscalyear_id = fields.Many2one(
        'date.range', string=u'Année', required=False, domain=[('type_id.fiscal_year', '=', True),('active', '=', True)])
    period_id = fields.Many2one(
        'date.range', string=u'Période', required=False)

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

    company_id = fields.Many2one(
        'res.company', string=u'Société', required=True,)
    date_from = fields.Date(
        string=u'Date début', required=True, default=lambda self: fields.Date.today())
    date_to = fields.Date(
        string=u'Date fin', required=True, default=lambda self: fields.Date.today())
    departments_id = fields.Many2many(
        'hr.department', 'mass_attendance_department_rel', 'mass_attebndance_id', 'department_id', string=u'Limiter les départements', )

    line_ids = fields.One2many(
        'hr.employee.mass.attendance', 'run_id', string=u'Lignes',)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Terminé'),
    ], string=u'État', required=True, default='draft')

    saisie_line_id = fields.Many2one('hr.saisie.line', string=u'Ligne de saisie',)

    @api.one
    def set_done(self):
        self.state = 'done'

    @api.one
    def set_draft(self):
        self.state = 'draft'

    @api.one
    def generate(self):
        if self.state != 'draft':
            return
        contracts = self.env['hr.contract'].search([
            ('is_contract_valid_by_context', 'in', (self.date_from, self.date_to)),
            ('company_id', '=', self.company_id.id),
        ])
        self.line_ids.unlink()
        employees = contracts.mapped('employee_id')
        for emp in employees:
            self.line_ids.create({
                'employee_id': emp.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'run_id': self.id,
            })

    @api.one
    def unlink(self):
        if self.state == 'done':
            raise Warning(
                _('La ligne ne peut pas être supprimé car elle est validée'))
        super(mass_attendance_run, self).unlink()


class mass_attendance(models.Model):
    _name = 'hr.employee.mass.attendance'
    _description = 'Pointage en masse'
    _rec_name = 'employee_id'
    _order = 'date_from desc'

    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé',  required=True)

    @api.one
    @api.depends("employee_id")
    def _compute_company_id(self):
        contract, company = False, False
        if self.employee_id and self.date_from:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('is_contract_valid_by_context', 'in', (self.date_from, self.date_to)),
            ], limit=1, order="date_start desc")
            company = contract and contract.company_id or False
        self.contract_id = contract
        self.company_id = company

    run_id = fields.Many2one(
        'hr.employee.mass.attendance.run', string=u'Lot', required=False, ondelete='cascade',)
    company_id = fields.Many2one(
        'res.company', string=u'Société', compute='_compute_company_id',   store=True,)
    contract_id = fields.Many2one(
        'hr.contract', string=u'Contrat', compute='_compute_company_id',   store=True,)
    based_on = fields.Selection(
        string=u'Basé sur', related='contract_id.based_on', store=True, readonly=True, )

    @api.one
    @api.depends("run_id","run_id.state")
    def _compute_state(self):
        if self.run_id:
            self.state = self.run_id.state
        else:
            self.state = 'manual'

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('manual', 'Manuel'),
        ('done', 'Terminé'),
        ], string=u'État', compute='_compute_state', store=True, readonly=True,  )
    date_from = fields.Date(
        string=u'Date début', required=True, default=lambda self: fields.Date.today())
    date_to = fields.Date(
        string=u'Date fin', required=True, default=lambda self: fields.Date.today())
    days = fields.Float(
        string=u'Nombre de jours', digits=dp.get_precision('Account'), default=0,)
    hours = fields.Float(
        string=u'Nombre d\'heures', digits=dp.get_precision('Account'), default=0,)

    @api.one
    @api.depends("date_from", "date_to")
    def _compute_dates(self):
        if self.date_from:
            self.month = self.date_from[:7]
            self.year = self.date_from[:4]
        else:
            self.month = False
            self.year = False

    month = fields.Char(
        string=u'Mois', size=64, compute='_compute_dates', store=True,)
    year = fields.Char(
        string=u'Année', size=4, compute='_compute_dates', store=True,)

    saisie_line_id = fields.Many2one('hr.saisie.line', string=u'Ligne de saisie',)

    _sql_constraints = [
        ('date_check', 'CHECK (date_from <= date_to)',
         'Vérifier les erreurs des dates !'),
    ]

    @api.one
    def unlink(self):
        if self.state == 'done':
            raise Warning(
                _('La ligne ne peut pas être supprimé car elle est validée'))
        super(mass_attendance, self).unlink()

    @api.model
    def get_days_hours(self, employee_id, date_from, date_to):
        if not isinstance(employee_id, (int, long)):
            employee_id = employee_id.id
        if isinstance(date_from, datetime):
            date_from = fields.Datetime.to_string(date_from)
        if isinstance(date_to, datetime):
            date_to = fields.Datetime.to_string(date_to)
        lines = self.search([
            ('employee_id', '=', employee_id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['manual','done']),
        ])
        days, hours = 0.0, 0.0
        for line in lines:
            days += line.days
            hours += line.hours
        return days, hours
