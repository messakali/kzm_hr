# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning


class hr_payslip_account(models.Model):
    _name = 'hr.payslip.account'
    _description = 'Comptabilisation des bulletins'

    @api.one
    def _compute_name(self):
        df, dt = self.date_from, self.date_to
        l = list(set([df[5:7] + df[:4], dt[5:7] + dt[:4]]))
        self.name = '/'.join(l)

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

    name = fields.Char(string=u'Nom', size=64, compute='_compute_name',)
    fiscalyear_id = fields.Many2one(
        'date.range', string=u'Année', required=False, states={'draft': [('readonly', False)]}, readonly=True, domain=[('type_id.fiscal_year', '=', True),('active', '=', True)] )
    period_id = fields.Many2one(
        'date.range', string=u'Période', required=False, states={'draft': [('readonly', False)]}, readonly=True, )
    date_from = fields.Date(string=u'Date début',  required=False, states={
                            'draft': [('readonly', False)]}, readonly=True, )
    date_to = fields.Date(string=u'Date fin',  required=False, states={
                          'draft': [('readonly', False)]}, readonly=True, )

    departments_id = fields.Many2many(
        'hr.department', 'report_common_department_rel', 'report_common_id', 'department_id', string=u'Limiter les départements', states={'draft': [('readonly', False)]}, readonly=True, )

    payslip_state = fields.Selection([
        ('all', 'All'),
        ('done', 'Terminé'),
    ], string=u'État', required=True, default='done', states={'draft': [('readonly', False)]}, readonly=True, )

    company_child = fields.Boolean(string=u'Filiales',  states={
                                   'draft': [('readonly', False)]}, readonly=True, default=True,)
    company_parent = fields.Boolean(string=u'Sociétés mères',  states={
                                    'draft': [('readonly', False)]}, readonly=True, default=True,)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'Confirmé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string=u'État', default='draft', readonly=True, track_visibility='onchange')

    payslip_ids = fields.Many2many('hr.payslip', string=u'Bulletins de paie', states={
        'draft': [('readonly', False)]}, readonly=True)

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
        'res.company', string=u'Sociétés',  required=True, states={'draft': [('readonly', False)]}, readonly=True, )

    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        if self.company_ids:
            self.journal_id = self.company_ids[
                0].main_company_id.payroll_journal_id

    move_id = fields.Many2one(
        'account.move', string=u'Écriture comptable',  readonly=True, )
    date = fields.Date(
        string=u'Date', required=True, default=lambda self: fields.Date.today())
    journal_id = fields.Many2one(
        'account.journal', string=u'Journal',  required=True, )

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id and self.journal_id.default_debit_account_id:
            self.account_debit_id = self.journal_id.default_debit_account_id
        else:
            self.account_debit_id = self.env['account.account'].search([
                ('code', 'like', '61711'),
#                 ('type', '!=', 'view'),
            ])
        if self.journal_id and self.journal_id.default_credit_account_id:
            self.account_credit_id = self.journal_id.default_credit_account_id
        else:
            self.account_credit_id = self.env['account.account'].search([
                ('code', 'like', '4432'),
#                 ('type', '!=', 'view'),
            ])

    account_debit_id = fields.Many2one(
        'account.account', string=u'Compte débit par défaut')
    account_credit_id = fields.Many2one(
        'account.account', string=u'Compte crédit par défaut')

    @api.multi
    def _get_payslips(self):
        domain = [
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('cnss_ok', '=', True),
            ('move_id', '=', False),
            ('company_id', 'in', [x.id for x in self.company_ids]),
        ]
        if self.departments_id:
            domain.append(
                ('department_id', 'in', [x.id for x in self.departments_id]),)
        if self.payslip_state != 'all':
            domain.append(('state', '=', self.payslip_state),)
        return self.env['hr.payslip'].search(domain)

    @api.one
    def generate(self):
        self.payslip_ids = [(6, 0, [x.id for x in self._get_payslips()])]

    @api.one
    def set_draft(self):
        self.state = 'draft'

    @api.one
    def set_confirm(self):
        if not self.payslip_ids:
            raise Warning(_('Aucun bulletin trouvé'))
        self.state = 'confirm'

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
            _('Le compte qui a comme code [%s] est introuvable') % code)

    @api.multi
    def action_print(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_paye_journal')

    @api.one
    def _create_move(self):
#         print self.env['account.move'].search([])
        own = self.env['ir.config_parameter'].get_param('paie_acc','0') == '2'
        if not own :
            return True
        tab = []
        company = False
        for slip in self.payslip_ids:
#             print slip
            if slip.move_id:
#                 print slip.move_id
                raise Warning(_('Le bulletin '+ slip.name +' a déjà une écriture comptable'))
            if not company:
                company = slip.company_id.main_company_id
            for line in slip.details_by_salary_rule_category:
                if not line.total:
                    continue
                rule = line.salary_rule_id
                code = partner_id = analytic_account_id = False
                credit, debit = 0.0,  0.0
                if rule.account_debit and rule.account_debit.code and rule.account_debit.code.isdigit():
                    code = rule.account_debit.code.rstrip('0')
                    debit = line.total
                    analytic_account_id = rule.analytic_account_id
                    partner_id = rule.register_id and rule.register_id.partner_id.id or False
                if rule.account_credit and rule.account_credit.code and rule.account_credit.code.isdigit():
                    code = rule.account_credit.code.rstrip('0')
                    credit = line.total
                    analytic_account_id = rule.analytic_account_id
                    partner_id = rule.register_id and rule.register_id.partner_id.id or False
                if code:
                    found = False
                    for i, item in enumerate(tab):
                        if tab[i]['code'] == code and tab[i]['partner_id'] == partner_id and tab[i]['analytic_account_id'] == analytic_account_id:
                            tab[i]['credit'] += credit
                            tab[i]['debit'] += debit
                            found = True
                    if not found:
                        tab.append({
                            'code': code,
                            'credit': credit,
                            'debit': debit,
                            'partner_id': partner_id,
                            'analytic_account_id': analytic_account_id,
                        })
            if company:
                ref = _(
                    'Paie - période %s') % (self.date_from[5:7] + '/' + self.date_from[:4],)
                res = {
                'journal_id': self.journal_id.id,
                'date': self.date,
                'ref': ref,
                'company_id': company.id,
            }
                
            
            res.update({'name': ref})
            move = self.move_id.create(res)
            
            total_debit = total_credit = 0.0

            for line in tab:
                code = line.get('code')
                account = self.get_account_from_code(company, code)
                if line.get('credit') != 0:
                    credit = {
                        'move_id': move.id,
                        'name': move.name,
                        'date': move.date,
                        'date_maturity': move.date,
                        'ref': move.ref,
                        'analytic_account_id':  line.get('analytic_account_id'),
                        'account_id': account.id,
                        'partner_id': line.get('partner_id'),
                        'debit': 0.0,
                        'credit': line.get('credit'),
                    }
                    total_credit += line.get('credit')
                    move.line_ids.create(credit)
                if line.get('debit') != 0:
                    debit = {
                        'move_id': move.id,
                        'name': move.name,
                        'date': move.date,
                        'date_maturity': move.date,
                        'ref': move.ref,
                        'analytic_account_id':  line.get('analytic_account_id'),
                        'account_id': account.id,
                        'partner_id': line.get('partner_id'),
                        'debit': line.get('debit'),
                        'credit': 0.0,
                    }
                    total_debit += line.get('debit')
                    move.line_ids.create(debit)
            if total_debit != total_credit:
                difference = abs(total_debit - total_credit)
                if total_debit > total_credit and not self.account_credit_id:
                    raise Warning(
                        _('Veuillez configurer le compte crédit par défaut pour l\'écart : [%s]') % difference)
                if total_debit < total_credit and not self.account_debit_id:
                    raise Warning(
                        _('Veuillez configurer le compte débit par défaut pour l\'écart : [%s]') % difference)
                diff_line = {
                    'move_id': move.id,
                    'name': move.name,
                    'date': move.date,
                    'date_maturity': move.date,
                    'ref': move.ref,
                    'account_id': False,
                    'partner_id': False,
                    'debit': 0.0,
                    'debit': 0.0,
                }
                if total_debit > total_credit:
                    diff_line.update({
                        'account_id': self.get_account_from_code(company, self.account_credit_id.code).id,
                        'credit': difference,
                    })
                if total_debit < total_credit:
                    diff_line.update({
                        'account_id': self.get_account_from_code(company, self.account_debit_id.code).id,
                        'credit': difference,
                    })
                move.line_id.create(diff_line)
            self.move_id = move
            for slip in self.payslip_ids:
                slip.move_id = move

    @api.one
    def set_done(self):
        self._create_move()
        self.state = 'done'

    @api.one
    def set_cancel(self):
        self.move_id.unlink()
        self.state = 'cancel'

    @api.multi
    def unlink(self):
        for obj in self:
            if obj.state != 'draft':
                raise Warning(_('Vous ne pouvez pas supprimer un enregistrement qui n\'est pas en état brouillon'))
        return super(hr_payslip_account, self).unlink()
