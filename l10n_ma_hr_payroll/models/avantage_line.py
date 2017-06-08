# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, _
from odoo.exceptions import Warning


class hr_avantage_line(models.Model):
    _name = 'hr.avantage.line'
    _description = 'Avantages'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _track = {
        'state': {
            'l10n_ma_hr_payroll.mt_avantage_line_confirmed': lambda self, cr, uid, obj, ctx=None: obj.state == 'confirm',
            'l10n_ma_hr_payroll.mt_avantage_line_validated': lambda self, cr, uid, obj, ctx=None: obj.state == 'validate',
            'l10n_ma_hr_payroll.mt_avantage_line_done': lambda self, cr, uid, obj, ctx=None: obj.state == 'done',
            'l10n_ma_hr_payroll.mt_avantage_line_refused': lambda self, cr, uid, obj, ctx=None: obj.state == 'refuse',
        },
    }
    name = fields.Char(string=u'Description', size=128, required=False, readonly=True, states={
                       'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    avantage_id = fields.Many2one(
        'hr.avantage', string=u'Type', required=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    amount = fields.Float(string=u'Montant', digits=dp.get_precision(
        'Account'), required=True, default=0.0, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    date_start = fields.Date(
        string=u'Date début', required=True, default=lambda *a: fields.Date.today(), readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    date_end = fields.Date(
        string=u'Date fin', required=True, default=lambda *a: fields.Date.today(), readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé', required=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'Confirmé'),
        ('validate', 'Validé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string=u'État', readonly=True, track_visibility='onchange', copy=False, default='draft',)

    saisie_line_id = fields.Many2one('hr.saisie.line', string=u'Ligne de saisie',)

    @api.one
    @api.depends("avantage_id")
    def _compute_code(self):
        if self.avantage_id:
            self.code = self.avantage_id.code

    code = fields.Char(
        string=u'Code', size=64, compute='_compute_code', store=True)

    @api.onchange('avantage_id')
    def _onchange_avantage_id(self):
        if self.avantage_id:
            self.can_reset = self.avantage_id.can_reset

    can_reset = fields.Boolean(string=u'Peut être réinitialisé', )

    notes = fields.Text(string=u'Notes', readonly=True, states={
                        'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

    _sql_constraints = [
        ('avantagedate_check', 'CHECK (date_end >= date_start)',
         'Vérifier les erreurs des dates !'),
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
        return super(hr_avantage_line, self).unlink()
