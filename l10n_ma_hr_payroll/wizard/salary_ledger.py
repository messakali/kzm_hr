# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import time


class hr_salary_ledger(models.TransientModel):
    _name = 'hr.salary.ledger'

    fiscalyear_id = fields.Many2one(
        'date.range.type', string=u'Année', required=False)
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
        self.date_from = False
        self.date_to = False
        if self.fiscalyear_id:
            period_objs = self.env['date.range'].search([('type_id', '=', self.fiscalyear_id.id)])
            date_start = [p.date_start for p in period_objs]
            if date_start:
                self.date_from = min(date_start)
            date_end = [p.date_end for p in period_objs]
            if date_end:
                self.date_to = max(date_end)
            period_ids = [
                x.id for x in period_objs if x.active == True]
            return {
                'domain': {
                    'period_id': [('id', 'in', period_ids)],
                }
            }

    @api.onchange('period_id')
    def _onchange_period_id(self):
        self.date_start = False
        self.date_end = False
        if self.period_id:
            self.date_from = self.period_id.date_start
            self.date_to = self.period_id.date_end

    @api.multi
    def action_print(self):
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_salary_ledger')
