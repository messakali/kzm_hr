# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from dateutil.relativedelta import relativedelta
import math


class hr_avance_line(models.Model):
    _name = 'hr.avance.line'
    _description = u'Avances / Prêts'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'display_name'

    _track = {
        'state': {
            'l10n_ma_hr_payroll.mt_avance_line_confirmed': lambda self, cr, uid, obj, ctx=None: obj.state == 'confirm',
            'l10n_ma_hr_payroll.mt_avance_line_validated': lambda self, cr, uid, obj, ctx=None: obj.state == 'validate',
            'l10n_ma_hr_payroll.mt_avance_line_done': lambda self, cr, uid, obj, ctx=None: obj.state == 'done',
            'l10n_ma_hr_payroll.mt_avance_line_refused': lambda self, cr, uid, obj, ctx=None: obj.state == 'refuse',
        },
    }

    @api.multi
    @api.depends('name','avance_id')
    def _compute_display_name(self):
        for obj in self:
            obj.display_name = obj.name or (obj.avance_id and obj.avance_id.name) or 'Avance'
    display_name = fields.Char(string='Name', size = 64 , compute='_compute_display_name',   )
    @api.one
    def generate_lines(self):
        self.line_ids.unlink()
        rate = self.rate / 100.
        interest_rate = self.avance_id.interest_rate / 100.
        echeance = self.amount
        if rate > 0:
            echeance = self.amount * \
                (rate / (1 - (1 + rate) ** (-1 * self.echeance_nbr)))
        self.echeance = echeance
        capital_restant_before = self.amount
        capital_restant_after = capital_restant_before
        for i in range(self.echeance_nbr):
            date_tmp = fields.Date.from_string(
                self.date_start) + relativedelta(months=i * self.every)
            date = fields.Datetime.to_string(date_tmp)
            capital_restant_before = capital_restant_after
            interest = capital_restant_before * rate
            interest_tva = interest * interest_rate
            amortissement = 0
            if interest > 0:
                amortissement = echeance - interest
            echeance_tva = echeance + interest_tva
            capital_restant_after = capital_restant_before - amortissement
            self.line_ids.create({
                'avance_line_id': self.id,
                'date': date,
                'capital_restant_before': capital_restant_before,
                'interest': interest,
                'interest_tva': interest_tva,
                'amortissement': amortissement,
                'echeance_ht': echeance,
                'echeance_ttc': echeance_tva,
                'capital_restant_after': capital_restant_after,
                'avance': math.ceil(self.amount / self.echeance_nbr),
            })

    @api.one
    @api.depends("date_start", "echeance_nbr", "every")
    def _compute_date_end(self):
        if self.date_start:
            date_start = fields.Date.from_string(self.date_start)
            date_end = date_start + \
                relativedelta(
                    months=self.echeance_nbr * self.every) + relativedelta(days=-1)
            self.date_end = fields.Date.to_string(date_end)
        else:
            self.date_end = False

    name = fields.Char(string=u'Description', size=128, required=False, readonly=True, states={
                       'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    avance_id = fields.Many2one(
        'hr.avance', string=u'Type', required=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    amount = fields.Float(string=u'Montant', digits=dp.get_precision(
        'Account'), required=True, default=0.0, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    date = fields.Date(
        string=u'Date de l\'opération', default=lambda *a: fields.Date.today(), readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    date_start = fields.Date(
        string=u'Date début', required=True, default=lambda *a: fields.Date.today(), readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    date_end = fields.Date(
        string=u'Date fin',  compute='_compute_date_end', store=True, readonly=True, )
    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé', required=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'Confirmé'),
        ('validate', 'Validé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string=u'État', readonly=True, track_visibility='onchange', copy=False, default='draft',)

    voucher_date = fields.Date(string=u'Date de règlement', track_visibility='onchange', readonly=True, )
    voucher_ok = fields.Boolean(string=u'Règlement effectué', default=False, track_visibility='onchange', readonly=True, )

    rate = fields.Float(
        string=u'Taux de remboursement', digits=dp.get_precision('Account'), readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    echeance_nbr = fields.Integer(
        string=u'# échéance',  required=True, default=1, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    echeance = fields.Float(
        string=u'Echéance', digits=dp.get_precision('Account'), readonly=True, )
    line_ids = fields.One2many(
        'hr.avance.line.line', 'avance_line_id', string=u'Lignes', readonly=True, )

    echeance_line_ids = fields.One2many(
        string=u'Echéances', related='line_ids',)

    interest_rate = fields.Float(
        string=u'Taux d\'intérêt', compute='_compute_code_interest_rate', store=True)

    every = fields.Integer(string=u'Périodicité', default=1, required=True,  readonly=True, states={
                           'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            if self.journal_id.type == 'cash':
                self.voucher_mode = 'ES'
            else:
                if self.voucher_mode not in ['CH', 'VIR']:
                    self.voucher_mode = False
        else:
            self.voucher_mode = False
    journal_id = fields.Many2one('account.journal',
                                 string=u'Mode de règlement',
                                 domain=[('type', 'in', ['bank', 'cash'])],
                                 readonly=True, states={
                                     'draft': [('readonly', False)], 'confirm': [('readonly', False)]}
                                 )
    move_id = fields.Many2one('account.move', string=u'Écriture comptable', readonly=True,   )

    @api.onchange('voucher_mode')
    def _onchange_voucher_mode(self):
        journals = self.env['account.journal'].search([('type', 'in', ['bank', 'cash'])])
        journal_cash = journals.filtered(lambda r: r.type=='cash')
        journal_bank = journals.filtered(lambda r: r.type=='bank')
        if self.voucher_mode:
            if self.voucher_mode == 'ES':
                journal = journal_cash and journal_cash[0] or False
            else:
                journal = journal_bank and journal_bank[0] or False
        else:
            journal = False
        if self.journal_id != journal:
            self.journal_id = journal

    voucher_mode = fields.Selection([
        ('ES', u'Espèces'),
        ('CH', u'Chèque'),
        ('VIR', u'Virement'),
    ], string=u'Mode de règlement', track_visibility='onchange', required=False, )

    @api.one
    @api.depends("avance_id")
    def _compute_code_interest_rate(self):
        if self.avance_id:
            self.code = self.avance_id.code
            self.interest_rate = self.avance_id.interest_rate

    code = fields.Char(
        string=u'Code', size=64, compute='_compute_code_interest_rate', store=True,)

    @api.onchange('avance_id')
    def _onchange_avance_id(self):
        if self.avance_id:
            self.can_reset = self.avance_id.can_reset
            self.rate = 0
            self.every = 1

    can_reset = fields.Boolean(string=u'Peut être réinitialisé', readonly=True, states={
                               'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

    notes = fields.Text(string=u'Notes', readonly=True, states={
                        'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

    _sql_constraints = [
        ('avancedate_check', 'CHECK (date_end >= date_start)',
         'Vérifier les erreurs des dates !'),
        ('amount_check', 'CHECK (amount != 0)',
         'Le montant doit être différent du zéro !'),
    ]

    @api.model
    def set_confirm(self):
        for record in self:
            test_date, test_amount = True, True
            record.employee_id.check_limits(
                self.date_start, self.amount, self, test_date=test_date, test_amount=test_amount)
            if not record.line_ids:
                record.generate_lines()
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
        for line in self.line_ids:
            line.set_cancel()
            line.unlink()
        self.state = 'draft'

    @api.model
    def _create_move(self):
        own = self.env['ir.config_parameter'].get_param('paie_acc','0') == '2'
        if not own :
            return True
        avance = self.avance_id
        if not avance.instant_move:
            return True
        if self.move_id:
            raise Warning(_("Une écriture comptable a été déjà créée"))
        if not self.employee_id.address_home_id:
            raise Warning(_('L\'employé doit avoir une addresse personnelle.'))
        journal = self.journal_id
        account_debit = avance.account_debit
        account_credit = journal.default_credit_account_id
        analytic_account_id = avance.analytic_account_id
        company = self.employee_id.company_id.main_company_id
        if not account_debit:
            raise Warning(
                _("Veuillez définir un compte de crédit pour [%s]") % avance.name)
        if not account_credit:
            raise Warning(
                _("Veuillez définir un compte crédit par défaut pour le journal [%s]") % journal.name)
        res = self.move_id.account_move_prepare(
            journal_id=journal.id,
            date=self.date,
            ref=_('Avance pour %s') % self.employee_id.name,
            company_id=company.id)
        res.update({'name': avance.name})
        move = self.move_id.create(res)
        credit = {
            'move_id': move.id,
            'name': move.name,
            'date': move.date,
            'date_maturity': move.date,
            'partner_id': self.employee_id.address_home_id.id,
            'ref': move.ref,
            'analytic_account_id':  False,
            'account_id': self.get_account_from_code(company, account_credit.code).id,
            'credit': self.amount,
            'debit': 0.0,
        }
        debit = {
            'move_id': move.id,
            'name': move.name,
            'date': move.date,
            'date_maturity': move.date,
            'partner_id': self.employee_id.address_home_id.id,
            'ref': move.ref,
            'analytic_account_id': False,
            'account_id': self.get_account_from_code(company, account_debit.code).id,
            'credit': 0.0,
            'debit': self.amount,
        }
        move.line_id.create(credit)
        move.line_id.create(debit)
        self.move_id = move.id

    @api.model
    def set_validate(self):
        for record in self:
            record._create_move()
            record.employee_id.check_limits(self.date_start, self.amount, self)
            record.line_ids.filtered(lambda r: r.state == 'draft').set_done()
        self.state = 'validate'

    @api.model
    def set_done(self):
        self.state = 'done'

    @api.model
    def set_cancel(self):
        self.move_id.unlink()
        for line in self.line_ids:
            line.set_cancel()
        self.state = 'cancel'

    @api.multi
    def unlink(self):
        for obj in self:
            if obj.state != 'draft':
                raise Warning(
                    _('Vous ne pouvez pas supprimer un document qui n\'est pas en état brouillon'))
        return super(hr_avance_line, self).unlink()

    @api.multi
    def get_account_from_code(self, company, code):
        code = code.rstrip('0')
        accounts = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('code', 'like', code),
        ])
        for acc in accounts:
            if acc.code.startswith(code):
                return acc
        raise Warning(
            _('Le compte qui a comme code [%s] est introuvable dans le système') % code)
