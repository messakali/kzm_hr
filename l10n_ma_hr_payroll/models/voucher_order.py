# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import time
from odoo.exceptions import Warning
import odoo.addons.decimal_precision as dp

class hr_voucher_order(models.Model):
    _name = 'hr.voucher.order'
    _description = 'Ordre de virement'
    _order = 'date_from desc'

    fiscalyear_id = fields.Many2one(
        'date.range.type', string=u'Année', required=False, states={'draft': [('readonly', False)]}, readonly=True,)
    period_id = fields.Many2one(
        'date.range', string=u'Période', required=False, states={'draft': [('readonly', False)]}, readonly=True,)
    date_from = fields.Date(
        string=u'Date début',  required=False, states={'draft': [('readonly', False)]}, readonly=True,)
    date_to = fields.Date(
        string=u'Date fin',  required=False, states={'draft': [('readonly', False)]}, readonly=True,)

    voucher_date = fields.Date(
        string=u'Date de réglement', required=True, states={'draft': [('readonly', False)]}, readonly=True,)
    ref = fields.Char(
        string=u'Référence', size=64, states={'draft': [('readonly', False)]}, readonly=True, )
    name = fields.Char(
        string=u'Nom', size=64, states={'draft': [('readonly', False)]}, readonly=True, )

    departments_id = fields.Many2many(
        'hr.department', 'ir_declaration_department_rel', 'declaration_id', 'department_id', string=u'Limiter les départements', states={'draft': [('readonly', False)]}, readonly=True, )

    payslip_state = fields.Selection([
        ('all', 'Tous'),
        ('done', 'Terminé'),
    ], string=u'État des bulletins de paie', required=True, default='done', states={'draft': [('readonly', False)]}, readonly=True,)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string=u'État', default='draft', readonly=True,)
    company_child = fields.Boolean(
        string=u'Filiales', default=False, states={'draft': [('readonly', False)]}, readonly=True, )
    company_parent = fields.Boolean(
        string=u'Sociétés mères', default=True, states={'draft': [('readonly', False)]}, readonly=True, )

    espece = fields.Boolean(string=u'Espèce', default=False, states={'draft': [('readonly', False)]}, readonly=True,  )
    cheque = fields.Boolean(string=u'Chèque',default=False,  states={'draft': [('readonly', False)]}, readonly=True,  )
    virement = fields.Boolean(string=u'Virement', default=True, states={'draft': [('readonly', False)]}, readonly=True,  )

    source = fields.Selection([
        ('slip', 'Bulletins de paie'),
        ('avance', 'Avances'),
    ], string='Source', required=True, )

    line_ids = fields.One2many(
        'hr.voucher.order.line', 'voucher_id', string=u'Lignes', states={'draft': [('readonly', False)]}, readonly=True,)

    @api.one
    @api.depends("line_ids")
    def _compute_lines(self):
        self.es_line_ids = self.line_ids.filtered(
            lambda r: r.voucher_mode == 'ES')
        self.count_es_line_ids = len(self.es_line_ids)
        self.ch_line_ids = self.line_ids.filtered(
            lambda r: r.voucher_mode == 'CH')
        self.count_ch_line_ids = len(self.ch_line_ids)
        self.vir_line_ids = self.line_ids.filtered(
            lambda r: r.voucher_mode == 'VIR')
        self.count_vir_line_ids = len(self.vir_line_ids)

    es_line_ids = fields.Many2many(
        'hr.voucher.order.line', 'voucher_id', 'line_id', 'voucher_line_es_rel', string=u'Espèces', compute='_compute_lines',)
    count_es_line_ids = fields.Integer(string=u'Espèces', compute='_compute_lines', )

    ch_line_ids = fields.Many2many(
        'hr.voucher.order.line', 'voucher_id', 'line_id', 'voucher_line_ch_rel', string=u'Chèque', compute='_compute_lines',)
    count_ch_line_ids = fields.Integer(string=u'Chèques', compute='_compute_lines', )

    vir_line_ids = fields.Many2many(
        'hr.voucher.order.line', 'voucher_id', 'line_id', 'voucher_line_vir_rel', string=u'Virement', compute='_compute_lines',)
    count_vir_line_ids = fields.Integer(string=u'Virements', compute='_compute_lines', )

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
        self.company_ids = self.env['res.company'].browse(ids)
    company_ids = fields.Many2many(
        'res.company', string=u'Sociétés',  required=True, states={'draft': [('readonly', False)]}, readonly=True,)

    @api.multi
    def _get_bank_ids(self):
        return self.env['res.company'].search([
            ('parent_id', '=', False)
        ], limit=1).mapped('bank_ids.id')

    @api.onchange('company_ids')
    def _onchange_bank_id(self):
        return {
            'domain': {
                'bank_id': [('id', 'in', self._get_bank_ids())],
            }
        }

    @api.multi
    def _get_default_bank(self):
        banks = self._get_bank_ids()
        return len(banks) == 1 and banks[0] or False

    bank_id = fields.Many2one('res.partner.bank', string=u'Banque de la société',
                              required=True, default=lambda self: self._get_default_bank(),
                              states={'draft': [('readonly', False)]}, readonly=True,)

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
        self.date_from = False
        self.date_to = False
        if self.period_id:
            self.date_from = self.period_id.date_start
            self.date_to = self.period_id.date_end

    # @api.multi
    # def action_print_pdf(self):
    #     return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_voucher_order')
    #
    # @api.multi
    # def action_generate_xls(self):
    #     raise Warning(
    #         _('Please contact your admnistrator to enable this feature'))

    @api.multi
    def open_es_slips(self) :
         return self.open_slips(domain=[('voucher_mode','=','ES')], context={'default_voucher_mode' : 'ES'}, name='Bulletins pour especes')

    @api.multi
    def open_ch_slips(self) :
         return self.open_slips(domain=[('voucher_mode','=','CH')], context={'default_voucher_mode' : 'CH'}, name='Bulletins pour cheques')

    @api.multi
    def open_vir_slips(self) :
         return self.open_slips(domain=[('voucher_mode','=','VIR')], context={'default_voucher_mode' : 'VIR'}, name='Bulletins pour virements')

    @api.multi
    def open_slips(self, domain=[], context=[], name=_('Payslips')) :
        self.ensure_one()
        if self.source=='slip':
            action = self.env.ref('hr_payroll.action_view_hr_payslip_form').read([])
            item_domain = [('id','in', self.line_ids.mapped('slip_id.id'))]
        else:
            action = self.env.ref('l10n_ma_hr_payroll.act_open_hr_avance_line_view').read([])
            item_domain = [('id','in', self.line_ids.mapped('avance_line_id.id'))]
        action = action and action[0] or {}
        old_domain = eval(action.get('domain', False) or '[]')
        old_domain += domain + item_domain
        action.update({'domain': str(old_domain)})
        old_context = eval(action.get('context', []))
        old_context.update(context)
        action.update({'context': str(old_context)})
        return action

    @api.one
    def set_draft(self):
        self.state = 'draft'
        self.load()
        for line in self.line_ids:
            if line.slip_id:
                line.slip_id.write({
                    'voucher_ok': False,
                    'voucher_date': False,
                })
            elif line.avance_line_id:
                line.avance_line_id.write({
                    'voucher_ok': False,
                    'voucher_date': False,
                })

    @api.one
    def set_cancel(self):
        self.state = 'cancel'
        for line in self.line_ids:
            if line.slip_id:
                line.slip_id.write({
                    'voucher_ok': False,
                    'voucher_date': False,
                })
            elif line.avance_line_id:
                line.avance_line_id.write({
                    'voucher_ok': False,
                    'voucher_date': False,
                })

    @api.one
    def set_done(self):
        self.state = 'done'
        for line in self.line_ids:
            if line.slip_id:
                line.slip_id.write({
                    'voucher_ok': True,
                    'voucher_date': self.voucher_date,
                })
            elif line.avance_line_id:
                line.avance_line_id.write({
                    'voucher_ok': True,
                    'voucher_date': self.voucher_date,
                })

    @api.multi
    def _get_payslips(self):
        domain = [
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('company_id', 'in', self.company_ids.mapped('id')),
            ('voucher_ok', '=', False),
        ]
        if self.departments_id:
            department_ids = [x.id for x in self.departments_id]
            domain.append(('department_id', 'in', department_ids),)
        if self.payslip_state != 'all':
            domain.append(('state', '=', self.payslip_state),)
        return self.env['hr.payslip'].search(domain)

    @api.multi
    def _get_avances(self):
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', 'in', ['confirm','validate','done']),
        ]
        if self.departments_id:
            department_ids = [x.id for x in self.departments_id]
            domain.append(('employee_id.department_id', 'in', department_ids),)
        return self.env['hr.avance.line'].search(domain)

    @api.multi
    def load(self):
        for voucher in self:
            voucher.line_ids.unlink()
            if voucher.source == 'slip':
                payslips = voucher._get_payslips()
                for slip in payslips:
                    if slip.voucher_mode == 'VIR' and not voucher.virement :
                        continue
                    if slip.voucher_mode == 'CH' and not voucher.cheque :
                        continue
                    if slip.voucher_mode == 'ES' and not voucher.espece :
                        continue
                    bank = slip.employee_id.bank_account_id
                    self.line_ids.create({
                        'voucher_id': self.id,
                        'slip_id': slip.id,
                        'name': self.ref,
                        'bank_id': bank and bank.id or False,
                    })
            else:
                avances = voucher._get_avances()
                for avance in avances:
                    bank = avance.employee_id.bank_account_id
                    self.line_ids.create({
                        'voucher_id': self.id,
                        'avance_line_id': avance.id,
                        'name': self.ref,
                        'bank_id': bank and bank.id or False,
                    })


    @api.multi
    def unlink(self):
        for obj in self:
            if obj.state != 'draft':
                raise Warning(
                    _('Vous ne pouvez pas supprimer un enregistrement qui n\'est pas en état brouillon'))
        return super(hr_voucher_order, self).unlink()


class hr_voucher_order_line(models.Model):
    _name = 'hr.voucher.order.line'
    _description = 'Voucher Order Lines'

    name = fields.Char(string=u'Référence', size=64,)
    voucher_id = fields.Many2one(
        'hr.voucher.order', string=u'Ordre de règlement', required=True,  ondelete='cascade',  )
    slip_id = fields.Many2one(
        'hr.payslip', string=u'Bulletin de paie', readonly=True, required=False, ondelete='cascade',  )
    avance_line_id = fields.Many2one(
        'hr.avance.line', string=u'Avance', readonly=True, required=False, ondelete='cascade',  )
    bank_id = fields.Many2one('res.partner.bank', string=u'Banque',  )

    @api.multi
    @api.depends(
        'slip_id',
        'slip_id.voucher_mode',
        'avance_line_id',
        'avance_line_id.voucher_mode',
        )
    def _compute_related(self):
        for obj in self:
            if obj.slip_id:
                obj.voucher_mode = obj.slip_id.voucher_mode
                obj.amount = obj.slip_id.salary_net
                obj.employee_id = obj.slip_id.employee_id
            elif obj.avance_line_id:
                obj.voucher_mode = obj.avance_line_id.voucher_mode
                obj.amount = obj.avance_line_id.amount
                obj.employee_id = obj.avance_line_id.employee_id
            else:
                obj.voucher_mode = False
                obj.amount = 0
                obj.employee_id = False

    employee_id = fields.Many2one('hr.employee', string='Employé', readonly=True,
        compute='_compute_related',  store=True, )
    amount = fields.Float(string=u'Total à payer', digits=dp.get_precision('Account'),
        compute='_compute_related',  store=True, )
    voucher_mode = fields.Selection([
        ('ES', u'Espèces'),
        ('CH', u'Chèque'),
        ('VIR', u'Virement'),
    ], string=u'Mode de règlement', compute='_compute_related',  store=True,  )
