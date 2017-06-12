# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.exceptions import Warning as UserError

MOIS = [u'Janvier', u'Février', u'Mars', u'Avril', u'Mai', u'Juin',
        u'Juillet', u'Août', u'Septembre', u'Octobre', u'Novembre', u'Décembre']


class hr_pasylip_run(models.Model):
    _inherit = 'hr.payslip.run'

    state = fields.Selection([
                            ('draft', u'Brouillon'),
                            ('charged', u'Lot chargé'),
                            ('confirm', u'Bulletins confirmés'),
                            ('cancel', u'Bulletins annulés'),
                            ('done', u'Terminé'),
            ], string=u'État', readonly=True, default='draft', required=True,  )

    @api.multi
    def set_done(self):
        for obj in self:
            if not obj.slip_ids:
                raise UserError(_('Veuillez générer les bulletins de paie'))
            obj.state = 'charged'

    @api.multi
    def marquer_lot_charge(self):
        for obj in self:
            if not obj.slip_ids:
                raise UserError(_('Veuillez générer les bulletins de paie'))
            obj.state = 'charged'

    @api.multi
    def cancel_slips(self):
        for obj in self:
            for slip in obj.slip_ids:
                slip.cancel_sheet()
            obj.state = 'cancel'

    @api.multi
    def reset_slips(self):
        for obj in self:
            for slip in obj.slip_ids:
                if slip.state != 'cancel':
                    slip.cancel_sheet()
                if slip.state == 'cancel':
                    slip.signal_workflow('draft')
            obj.state = 'draft'

    @api.onchange('fiscalyear_id')
    def _onchange_fiscalyear_id(self):
        self.period_id = False
        self.date_start = False
        self.date_end = False
        if self.fiscalyear_id:
            period_objs = self.env['date.range'].search([('type_id', '=', self.fiscalyear_id.id)])
            date_start = [p.date_start for p in period_objs]
            if date_start:
                self.date_start = min(date_start)
            date_end = [p.date_end for p in period_objs]
            if date_end:
                self.date_end = max(date_end)
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
            self.date_start = self.period_id.date_start
            self.date_end = self.period_id.date_end

    fiscalyear_id = fields.Many2one(
        'date.range.type', string=u'Année', readonly=True, states={'draft': [('readonly', False)]}, required=False, domain=[('fiscal_year', '=', True),('active', '=', True)])
    period_id = fields.Many2one(
        'date.range', string=u'Période', readonly=True, states={'draft': [('readonly', False)]}, required=False)

    date_start = fields.Date()
    date_end = fields.Date()
    slip_ids = fields.One2many()

    summary = fields.Html(string=u'Résumé', compute='_compute_summary')
    journal_id = fields.Many2one(required=False,)

    @api.model
    def create(self, vals):
        audit = self.env['hr.common.report'].search([
            ('date_from', '=', vals.get('date_start')),
            ('date_to', '=', vals.get('date_end')),
            ('type_id.code', '=', 'audit'),
        ])
        city = self.env.user.company_id.city
        audit_type = self.env['hr.common.report.type'].search(
            [('code', '=', 'audit')], limit=1)
        if not audit:
            if audit_type:
                self.env['hr.common.report'].create({
                    'date_from': vals.get('date_start'),
                    'date_to': vals.get('date_end'),
                    'type_id': audit_type.id,
                    'edition_city': city or _('Not defined'),
                    'company_ids': [(6, 0, self.env['res.company'].search([]).mapped('id'))],
                })
        return super(hr_pasylip_run, self).create(vals)

    @api.multi
    def print_slips(self):
        assert len(self), _("Veuillez exécuter cette action juste pour un seul lot")
        if not self.slip_ids:
            raise Warning(_("Aucun bulletins de paie attaché à ce lot"))
        return self.env['report'].get_action(self.slip_ids, 'l10n_ma_hr_payroll.report_slip_simple')

    @api.one
    def confirm_slips(self):
        for slip in self.slip_ids:
            slip.compute_sheet()
            slip.process_sheet()
        if self.slip_ids:
            self.state = 'confirm'
        else:
            raise UserError(_('Aucun bulletin attaché à ce lot')) 

    @api.multi
    def re_reset_params(self):
        for slip in self.slip_ids:
            slip.reset_params()

    @api.multi
    def re_compute_sheets(self):
        for slip in self.slip_ids:
            slip.compute_sheet()

    @api.multi
    def close_payslip_run(self):
        for run in self:
            if not run.slip_ids:
                raise Warning(_("Aucun bulletins de paie attaché à ce lot"))
            for slip in run.slip_ids:
                if slip.state not in ['done', 'cancel']:
                    raise Warning(
                        _("Bulletin de paie [%s] doit être validé ou annulé") % slip.name)
                if not slip.voucher_mode:
                    raise Warning(
                        _("Mode de règlement est obligatoire pour le bulletin de paie [%s]") % slip.name)
                if not slip.voucher_date:
                    raise Warning(
                        _("Date de règlement est requis pour le bulletin de paie [%s]") % slip.name)
            run.state = 'done'

    @api.multi
    def create_account_moves(self):
        for run in self:
            if not run.slip_ids:
                raise Warning(_("Aucun bulletins de paie attaché à ce lot"))
            slips = run.slip_ids.filtered(lambda r: not r.move_id)
            if not slips:
                raise Warning(
                    _('Aucun bulletin de paie non comptabilisé dans ce lot'))
            journal = slips.mapped(
                'company_id')[0].main_company_id.payroll_journal_id
            if not journal:
                raise Warning(_('Veuillez configurer le journal de paie pour la société'))
            for slip in slips:
                if slip.state != 'done':
                    raise Warning(
                        _("Bulletin de paie [%s] doit être validé") % slip.name)

            payslip_account = self.env['hr.payslip.account'].create({
                'fiscalyear_id': run.fiscalyear_id.id,
                'period_id': run.period_id.id,
                'date_from': run.date_start,
                'date_to': run.date_end,
                'company_ids': [(6, 0, slips.mapped('company_id.id'))],
                'payslip_ids': [(6, 0, slips.mapped('id'))],
                'journal_id': journal.id,
                'date': run.date_end,
            })
            payslip_account._onchange_journal_id()
            action = self.env.ref(
                'l10n_ma_hr_payroll.act_open_hr_payslip_account_view').read()[0]
            action['res_id'] = payslip_account.id
            action['view_mode'] = 'form'
            action['views'] = filter(
                lambda r: r[1] == u'form', action['views'])
            return action

    @api.multi
    def open_audit_action(self):
        return {
            'name': _('Audit'),
            'context': {
                'default_date_from': self.date_start,
                'default_date_to': self.date_end,
                'default_code_helper': 'audit',
            },
            'domain': [
                ('date_from', '=', self.date_start),
                ('date_to', '=', self.date_end),
                ('code', '=', 'audit'),
            ],
            'res_model': u'hr.common.report',
            'type': u'ir.actions.act_window',
            'view_mode': u'tree,form',
            'view_type': u'form',
            'views': [(False, u'tree'), (False, u'form')],
        }

    @api.one
    def _compute_audit_count(self):
        self.audit_count = self.env['hr.common.report'].search_count([
            ('date_from', '=', self.date_start),
            ('date_to', '=', self.date_end),
            ('type_id.code', '=', 'audit'),
        ])

    audit_count = fields.Integer(
        string=u'Audits', compute='_compute_audit_count',)

    @api.one
    def _compute_slip_count(self):
        self.slip_count = self.env['hr.payslip'].search_count(
            [('payslip_run_id', '=', self.id)])

    slip_count = fields.Integer(
        string=u'Bulletins de paie', compute='_compute_slip_count',)

    @api.depends('date_start', 'date_end', 'slip_ids')
    def _compute_summary(self):
        if self.date_start or self.date_end:
            the_date = self.date_start or self.date_end
            month = the_date[5:7]
            if month:
                month = int(month) - 1
                self.name = _('Lot') + ' ' + MOIS[month] + " " + the_date[:4]
        if self.date_start and self.date_end:
            employees = self.env['hr.employee'].search(
                [('is_contract_valid', '=', self.date_end)])
            slips_done = self.env['hr.payslip'].search(
                [('date_to', '>=', self.date_start),
                 ('date_to', '<=', self.date_end),
                 ('state', '=', 'done')])
            employees_done = slips_done.mapped('employee_id')
            slips_draft = self.env['hr.payslip'].search(
                [('date_to', '>=', self.date_start),
                 ('date_to', '<=', self.date_end),
                 ('state', '=', 'draft')])
            employees_draft = slips_draft.mapped('employee_id')
            slips_cancel = self.env['hr.payslip'].search(
                [('date_to', '>=', self.date_start),
                 ('date_to', '<=', self.date_end),
                 ('state', '=', 'cancel')])
            employees_cancel = slips_cancel.mapped('employee_id')
            slips_verify = self.env['hr.payslip'].search(
                [('date_to', '>=', self.date_start),
                 ('date_to', '<=', self.date_end),
                 ('state', '=', 'verify')])
            employees_verify = slips_verify.mapped('employee_id')
            self.summary = _("""<b>%s</b> : Total des employés.<br />
            <hr />
            <b>%s</b> : Bulletins brouillon.<br />
            <b>%s</b> : Bulletins annulés.<br />
            <b>%s</b> : Bulletins terminés.<br />
            <b>%s</b> : À vérifier.<br />""") % (len(employees), len(employees_draft), len(employees_cancel), len(employees_done), len(employees_verify))
        else:
            self.summary = ""
