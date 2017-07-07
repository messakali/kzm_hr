# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import time


class hr_cotisation_wizard(models.TransientModel):
    _name = 'hr.cotisation.wizard'

    fiscalyear_id = fields.Many2one(
        'date.range', string=u'Année', required=False, domain=[('type_id.fiscal_year', '=', True),('active', '=', True)])
    period_id = fields.Many2one(
        'date.range', string=u'Période', required=False)
    date_from = fields.Date(string=u'Date début',  required=False)
    date_to = fields.Date(string=u'Date fin',  required=False)

    departments_id = fields.Many2many(
        'hr.department', 'salary_declaration_department_rel', 'declaration_id', 'department_id', string=u'Limiter les départements', )

    payslip_state = fields.Selection([
        ('all', 'All'),
        ('done', 'Terminé'),
    ], string=u'État', required=True, default='done')

    company_child = fields.Boolean(string=u'Filiales', default=False,)
    company_parent = fields.Boolean(string=u'Sociétés mères', default=False,)

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

    @api.multi
    def action_print(self):
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_cotisation')
    
    def get_register_lines(self):
        department_ids = [x.id for x in self.departments_id]
        if not department_ids:
            department_ids = self.env[
                'hr.department'].search([])
        department_ids = self.env[
            'hr.department'].search([('id', 'child_of', department_ids.ids)])
        payslip_domain = [
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('company_id', 'in', self.env['hr.common.report'].get_companies_ids(self)),
        ]
        if self.departments_id:
            payslip_domain.append(('department_id', 'in', department_ids),)
        if self.payslip_state != 'all':
            payslip_domain.append(('state', '=', self.payslip_state),)
        payslip_ids = self.env['hr.payslip'].search(payslip_domain)
        payslips = payslip_ids
        registers = self.env['hr.contribution.register'].search_read([],['name'])
        registers = [[x.get('id'), x.get('name'), 0] for x in registers]
        for slip in payslips:
            for line in slip.details_by_salary_rule_category:
                if line.total > 0 and line.register_id:
                    for i, item in enumerate(registers):
                        if item[0] == line.register_id.id:
                            registers[i][2] += line.total
        return registers
