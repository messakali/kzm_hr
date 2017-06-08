# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, _


class hr_avance_run(models.TransientModel):
    _name = 'hr.avance.run'
    _description = 'Avances /Cessions batch'

    allocation_mode = fields.Selection([
        ('employee', 'Par employé'),
        ('category', 'Par catégorie des employés')
    ], string=u'Mode d\'affectation',  required=True)

    employee_ids = fields.Many2many('hr.employee', string=u'Employés',)
    category_ids = fields.Many2many(
        'hr.employee.category', string=u'Catégories des employés',)

    name = fields.Char(string=u'Description', size=128, required=False,)
    avance_id = fields.Many2one(
        'hr.avance', string=u'Type', required=True)
    amount = fields.Float(string=u'Montant', digits=dp.get_precision(
        'Account'), required=True, default=0.0)
    date = fields.Date(
        string=u'Date de l\'opération', default=lambda *a: fields.Date.today(), readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    date_start = fields.Date(
        string=u'Date début', required=True, default=lambda *a: fields.Date.today())
    date_end = fields.Date(
        string=u'Date fin', required=True, default=lambda *a: fields.Date.today())
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'Confirmé'),
        ('validate', 'Validé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string=u'État', default='draft',)

    notes = fields.Text(string=u'Notes',)

    rate = fields.Float(
        string=u'Taux de remboursement', digits=dp.get_precision('Account'),)
    echeance_nbr = fields.Integer(
        string=u'Nombre d\'échéances',  required=True, default=1)

    @api.one
    @api.depends("avance_id")
    def _compute_code_interest_rate(self):
        if self.avance_id:
            self.code = self.avance_id.code
            self.interest_rate = self.avance_id.interest_rate

    code = fields.Char(
        string=u'Code', size=64, compute='_compute_code_interest_rate', store=True)

    interest_rate = fields.Float(
        string=u'Taux d\'intérêt', related='avance_id.interest_rate', store=True,)

    every = fields.Integer(string=u'Périodicité', default=1, required=True,)

    journal_id = fields.Many2one('account.journal',
                                 string=u'Mode de règlement',
                                 domain=[('type', 'in', ['bank', 'cash'])],
                                 )

    @api.onchange('allocation_mode')
    def _onchange_allocation_mode(self):
        self.employee_ids = []
        self.category_ids = []

    @api.multi
    def generate(self):
        self.ensure_one()
        employees = self.employee_ids
        categories = self.category_ids
        if categories:
            employees += employees.search([('category_ids',
                                            'in', [x.id for x in categories])])
        ids = []
        for emp in employees:
            avance_id = self.env['hr.avance.line'].create({
                'name': self.name or '',
                'avance_id': self.avance_id.id,
                'amount': self.amount,
                'date_start': self.date_start,
                'employee_id': emp.id,
                'notes': self.notes,
                'rate': self.rate,
                'echeance_nbr': self.echeance_nbr,
                'every': self.every,
                'interest_rate': self.interest_rate,
                'code': self.code,
                'date': self.date,
            })
            if self.state != 'draft':
                if self.state in ['confirm', 'validate', 'done']:
                    avance_id.signal_workflow('avance_confirm')
                if self.state in ['validate', 'done']:
                    avance_id.signal_workflow('avance_validate')
                if self.state in ['done']:
                    avance_id.signal_workflow('avance_done')
                if self.state in ['cancel']:
                    avance_id.signal_workflow('avance_refuse1')
            ids.append(avance_id.id)
        form = self.env.ref('l10n_ma_hr_payroll.view_hr_avance_line_form')
        form_id = form and form.read(['id'])[0].get('id', False)
        return {
            'name': _('Éléments créés'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (form_id or False, 'form')],
            'res_model': 'hr.avance.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', ids)],
        }
