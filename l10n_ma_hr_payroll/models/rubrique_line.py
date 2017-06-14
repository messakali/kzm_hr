# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, _
from odoo.exceptions import Warning


class hr_rubrique_line(models.Model):
    _name = 'hr.rubrique.line'
    _description = 'Éléments de salaire'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _track = {
        'state': {
            'l10n_ma_hr_payroll.mt_rubrique_line_confirmed': lambda self, cr, uid, obj, ctx=None: obj.state == 'confirm',
            'l10n_ma_hr_payroll.mt_rubrique_line_validated': lambda self, cr, uid, obj, ctx=None: obj.state == 'validate',
            'l10n_ma_hr_payroll.mt_rubrique_line_done': lambda self, cr, uid, obj, ctx=None: obj.state == 'done',
            'l10n_ma_hr_payroll.mt_rubrique_line_refused': lambda self, cr, uid, obj, ctx=None: obj.state == 'refuse',
        },
    }


    name = fields.Char(string=u'Description', size=128, required=False, readonly=True, states={
                       'draft': [('readonly', False)], 'confirm': [('readonly', False)]},)
    rubrique_id = fields.Many2one(
        'hr.rubrique', string=u'Rubrique', required=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},)
    amount = fields.Float(string=u'Montant', digits=dp.get_precision(
        'Account'), required=True, default=0.0, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},)
    date_start = fields.Date(
        string=u'Date début', required=False, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},)
    date_end = fields.Date(
        string=u'Date fin', required=False, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},)
    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé', required=False, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'Confirmée'),
        ('validate', 'Validée'),
        ('done', 'Terminée'),
        ('cancel', 'Annulée'),
    ], string=u'État', readonly=True, track_visibility='onchange', copy=False, default='draft',)

    saisie_line_id = fields.Many2one('hr.saisie.line', string=u'Ligne de saisie',)
    contract_id = fields.Many2one('hr.contract', string='Contrat', ondelete='cascade',   )


    @api.depends("rubrique_id","rubrique_id.code","rubrique_id.can_reset")
    def _compute_code(self):
        for rec in self:
            if rec.rubrique_id:
                rec.code = rec.rubrique_id.code
                rec.can_reset = rec.rubrique_id.can_reset

    code = fields.Char(
        string=u'Code', size=64, compute='_compute_code', store=True)

    @api.onchange('rubrique_id')
    def _onchange_rubrique_id(self):
        for rec in self:
            if rec.rubrique_id:
                if not rec.name:
                    rec.name = rec.rubrique_id.name

    can_reset = fields.Boolean(string=u'Peut être réinitialisé', compute='_compute_code', store=True)

    notes = fields.Text(string=u'Notes', readonly=True, states={
                        'draft': [('readonly', False)], 'confirm': [('readonly', False)]},)

    @api.model
    def get_domain(self, employee_id, state, code, date_start, date_end):
        A = ('date_start', '!=', False)
        B = ('date_end', '!=', False)
        A_ = ('date_start', '=', False)
        B_ = ('date_end', '=', False)
        C = ('date_start', '<=', date_end)
        D = ('date_end', '>=', date_start)
        M = ('date_end', '<=', date_end)
        N = ('date_end', '>=', date_start)
        P = ('date_end', '>=', date_end)
        S = ('date_start', '<=', date_end)
        domain = [
            ('state', '=', state),
            ('code', '=', code),
            ('employee_id', '=', employee_id),
            '|',
            '|',
            '|',
            '&','&',A,B_,C,
            '&','&',A_,B,D,
            '&',A_,B_,
            '&','&', A, B,
            '|',
            '&', M, N,
            '&',P, S
        ]
        return domain

    _sql_constraints = [
        ('rubriquedate_check', 'CHECK (date_end >= date_start)',
         u'Vérifier les erreurs des dates !'),
        ('amount_check', 'CHECK (amount != 0)',
         'Le montant doit être différent du zéro !'),
    ]

    @api.model
    def set_confirm(self):
        for record in self:
            test_date, test_amount = True, True
            if self.saisie_line_id:
                test_date = False
            record.employee_id.check_limits(
                self.date_start, self.amount, self, test_date=test_date, test_amount=test_amount)
            user_ids = []
            if record.employee_id and record.employee_id.user_id:
                user_ids += [record.employee_id.user_id.id]
            if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.user_id:
                user_ids += [record.employee_id.parent_id.user_id.id]
            user_ids += [x.id for x in self.env.user.company_id.rh_users_id]
            user_ids = list(set(user_ids))
            record.message_subscribe_users(user_ids=user_ids)
        self.state = 'confirm'

    @api.multi
    def should_be_cancel(self):
        for rubrique in self:
            if rubrique.state == 'draft':
                rubrique.signal_workflow('rubrique_refuse1')
            if rubrique.state == 'confirm':
                rubrique.signal_workflow('rubrique_refuse2')
            if rubrique.state == 'validate':
                rubrique.signal_workflow('rubrique_refuse3')

    @api.multi
    def should_be_done(self):
        for rubrique in self:
            for state in ['confirm','validate','done']:
                rubrique.signal_workflow('rubrique_%s' % state)

    @api.multi
    def should_be_draft(self):
        for rubrique in self:
            rubrique.signal_workflow('rubrique_reset_draft')

    @api.model
    def set_draft(self):
        self.state = 'draft'

    @api.model
    def set_validate(self):
        for record in self:
            record.employee_id.check_limits(self.date_start, self.amount, self)
        self.state = 'validate'

    @api.model
    def set_done(self):
        self.state = 'done'

    @api.model
    def set_cancel(self):
        self.state = 'cancel'

    @api.multi
    def unlink(self):
        for obj in self:
            if obj.state != 'draft':
                raise Warning(
                    _('Vous ne pouvez pas supprimer un document qui n\'est pas en état brouillon'))
        return super(hr_rubrique_line, self).unlink()
