# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, _


class hr_rubrique_run(models.TransientModel):
    _name = 'hr.rubrique.run'
    _description = 'Rubrique batch'

    allocation_mode = fields.Selection([
        ('employee', 'Par employé'),
        ('category', 'Par catégorie des employés')
    ], string=u'Mode d\'affectation',  required=True)

    employee_ids = fields.Many2many('hr.employee', string=u'Employés',)
    category_ids = fields.Many2many(
        'hr.employee.category', string=u'Catégories des employés',)

    name = fields.Char(string=u'Description', size=128, required=False,)
    rubrique_id = fields.Many2one(
        'hr.rubrique', string=u'Rubrique', required=True)
    amount = fields.Float(string=u'Montant', digits=dp.get_precision(
        'Account'), required=True, default=0.0)
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
            rubrique_id = self.env['hr.rubrique.line'].create({
                'name': self.name or '',
                'rubrique_id': self.rubrique_id.id,
                'amount': self.amount,
                'date_start': self.date_start,
                'date_end': self.date_end,
                'employee_id': emp.id,
                'notes': self.notes,
            })
            if self.state != 'draft':
                if self.state in ['confirm', 'validate', 'done']:
                    rubrique_id.signal_workflow('rubrique_confirm')
                if self.state in ['validate', 'done']:
                    rubrique_id.signal_workflow('rubrique_validate')
                if self.state in ['done']:
                    rubrique_id.signal_workflow('rubrique_done')
                if self.state in ['cancel']:
                    rubrique_id.signal_workflow('rubrique_refuse1')
            ids.append(rubrique_id.id)
        form = self.env.ref('l10n_ma_hr_payroll.view_hr_rubrique_line_form')
        form_id = form and form.read(['id'])[0].get('id', False)
        return {
            'name': _('Éléments créés'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (form_id or False, 'form')],
            'res_model': 'hr.rubrique.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', ids)],
        }
