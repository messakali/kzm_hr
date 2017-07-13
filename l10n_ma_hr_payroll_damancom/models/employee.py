# encoding: utf-8

from odoo import models, fields, api, _
from datetime import timedelta
from .variables import *



class hr_employee(models.Model):
    _inherit = 'hr.employee'

    @api.multi
    def get_situation(self):
        self.ensure_one()
        ctx = self._context.copy()
        domain = [('employee_id', '=', self.id)]
        if ctx.get('date', False):
            domain.append(('date', '<=', ctx.get('date')),)
        line = self.env['hr.employee.situation'].search(
            domain, order='date desc', limit=1)
        default = ctx.get('default', False) and ctx.get('default') or False
        return line and line.name or default

    situation_ids = fields.One2many(
        'hr.employee.situation', 'employee_id',
        string=u'Situations', required=False, )

class hr_employee_situtation(models.Model):
    _name = 'hr.employee.situation'
    _description = 'Employee Situation'
    _order = 'date asc'

    @api.one
    def _compute_date_end(self):
        next_item = self.search([
            ('date', '>', self.date),
            ('employee_id', '=', self.employee_id.id),
        ], order='date asc', limit=1)
        if next_item:
            date = fields.Datetime.from_string(next_item.date) + timedelta(days=-1)
            self.date_end = fields.Datetime.to_string(date)
        else:
            self.date_end = False

    name = fields.Selection(
        SITUATION, string=u'Situation', required=True, default='NON_RENSEIGNE')
    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé', required=True, ondelete='cascade',  )
    contract_id = fields.Many2one(
        'hr.contract', string=u'Contrat', required=True, ondelete='cascade',  )
    date = fields.Date(
        string=u'Date',  required=True, default=lambda *a: fields.Date.today())
    date_end = fields.Date(string=u'Date fin', compute='_compute_date_end',)

    _sql_constraints = [
        ('date_employee_contract_unique', 'UNIQUE (date, employee_id, contract_id)',
         'La situation doit être unique par date et par contrat !'),
    ]
