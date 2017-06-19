# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import time
import odoo.addons.decimal_precision as dp
import math

from odoo.exceptions import Warning


class hr_common_report(models.Model):
    _name = 'hr.common.report'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Rapports communs'
    _order = 'date_from desc'

    @api.one
    def _compute_name(self):
        df, dt = self.date_from, self.date_to
        l = list(set([self.type_id.name, df[5:7] + df[:4], dt[5:7] + dt[:4]]))
        self.name = '/'.join(l)

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
        ('paid', 'Paid'),
        ('cancel', 'Annulé'),
    ], string=u'État', default='draft', readonly=True, track_visibility='onchange')

    type_id = fields.Many2one('hr.common.report.type', string=u'Type de rapport',  required=True, states={
                              'draft': [('readonly', False)]}, readonly=True,)
    voucher_mode = fields.Selection([
        ('ES', u'Espèces'),
        ('CH', u'Chèque'),
        ('SIR', u'Télépaiement'),
    ],
        string=u'Mode de règlement',
        required=False,
        readonly=True,
        states={'done': [('readonly', False), ('required', True)]},
    )

    ir_quittance = fields.Char(string=u'Quittance', size=64, readonly=True,
                               states={'done': [('readonly', False)]}, )
    voucher_ref = fields.Char(string=u'Réf. règlement', size=64, readonly=True,
                              states={'done': [('readonly', False)]}, )
    voucher_date = fields.Date(string=u'Date règlement',
                               required=False,
                               readonly=True,
                               states={
                                   'done': [('readonly', False), ('required', True)]},
                               )

    edition_date = fields.Date(
        string=u'Date', default=lambda self: fields.Date.today(),  required=True,)
    edition_city = fields.Char(string=u'Ville', size=64, required=True, default=lambda self: self.env.user.company_id.main_company_id.city or '',  )

    total_brut = fields.Float(
        string=u'Total Brut', digits=dp.get_precision('Account'),  readonly=True,)
    total_brut_imposable = fields.Float(
        string=u'Total Brut Imposable', digits=dp.get_precision('Account'), readonly=True, )
    total_net_imposable = fields.Float(
        string=u'Total Net Imposable', digits=dp.get_precision('Account'),  readonly=True,)
    total_prestation_sociale = fields.Float(
        string=u'Total Prestations Sociales', digits=dp.get_precision('Account'),  readonly=True,)
    total_prestation_sociale_base = fields.Float(
        string=u'Total Base Prestations Sociales', digits=dp.get_precision('Account'), readonly=True,)
    total_prestation_familiale = fields.Float(
        string=u'Total Prestations Familiales', digits=dp.get_precision('Account'), readonly=True, )
    total_prestation_familiale_base = fields.Float(
        string=u'Total Base Prestations Familiales', digits=dp.get_precision('Account'), readonly=True, )
    total_tax_formation_professionnelle = fields.Float(
        string=u'Total Taxe de Formation Professionelle', digits=dp.get_precision('Account'), readonly=True, )
    total_tax_formation_professionnelle_base = fields.Float(
        string=u'Total Base Taxe de Formation Professionelle', digits=dp.get_precision('Account'),  readonly=True,)
    total_amo_base = fields.Float(
        string=u'Total AMO Base', digits=dp.get_precision('Account'), readonly=True, )
    total_amo_base_base = fields.Float(
        string=u'Total Base AMO', digits=dp.get_precision('Account'), readonly=True, )
    total_amo_solidarite = fields.Float(
        string=u'Total AMO Solidarite', digits=dp.get_precision('Account'),  readonly=True,)
    total_amo_solidarite_base = fields.Float(
        string=u'Total Base AMO Solidarite', digits=dp.get_precision('Account'), readonly=True, )
    total_amo = fields.Float(
        string=u'Total AMO', digits=dp.get_precision('Account'),  readonly=True,)
    total_cnss = fields.Float(
        string=u'Total CNSS', digits=dp.get_precision('Account'), readonly=True, )

    @api.multi
    def _get_payslips(self):
        domain = [
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('company_id', 'in', [x.id for x in self.company_ids]),
        ]
        if self.departments_id:
            domain.append(
                ('department_id', 'in', [x.id for x in self.departments_id]),)
        if self.payslip_state != 'all':
            domain.append(('state', '=', self.payslip_state),)
        return self.env['hr.payslip'].search(domain)

    ir_penalite = fields.Float(string=u'Penalité', digits=dp.get_precision(
        'Account'),  states={'draft': [('readonly', False)]}, readonly=True,)
    ir_majoration = fields.Float(string=u'Majoration', digits=dp.get_precision(
        'Account'), states={'draft': [('readonly', False)]}, readonly=True, )
    ir_total_verse = fields.Float(string=u'Total versé',
                                  digits=dp.get_precision('Account'),
                                  readonly=True, )
    ir_principal = fields.Float(string=u'Principal',
                                digits=dp.get_precision('Account'),
                                readonly=True,)

    @api.one
    @api.depends('ir_penalite', 'ir_majoration', 'ir_principal')
    def _compute_ir_total(self):
        self.ir_total = math.ceil(
            self.ir_penalite + self.ir_majoration + self.ir_principal)

    ir_total = fields.Float(string=u'Total',
                            digits=dp.get_precision('Account'),
                            readonly=True,
                            compute='_compute_ir_total',
                            store=True)

    cimr_penalite = fields.Float(string=u'Penalité', digits=dp.get_precision(
        'Account'),  states={'draft': [('readonly', False)]}, readonly=True,)
    cimr_majoration = fields.Float(string=u'Majoration', digits=dp.get_precision(
        'Account'), states={'draft': [('readonly', False)]}, readonly=True, )
    cimr_total_verse = fields.Float(string=u'Total versé',
                                    digits=dp.get_precision('Account'),
                                    readonly=True, )
    cimr_principal = fields.Float(string=u'Principal',
                                  digits=dp.get_precision('Account'),
                                  readonly=True,)

    @api.one
    @api.depends('cimr_penalite', 'cimr_majoration', 'cimr_principal')
    def _compute_cimr_total(self):
        self.cimr_total = math.ceil(
            self.cimr_penalite + self.cimr_majoration + self.cimr_principal)

    cimr_total = fields.Float(string=u'Total',
                              digits=dp.get_precision('Account'),
                              readonly=True,
                              compute='_compute_cimr_total',
                              store=True)

    mutuelle_penalite = fields.Float(string=u'Penalité', digits=dp.get_precision(
        'Account'),  states={'draft': [('readonly', False)]}, readonly=True,)
    mutuelle_majoration = fields.Float(string=u'Majoration', digits=dp.get_precision(
        'Account'), states={'draft': [('readonly', False)]}, readonly=True, )
    mutuelle_total_verse = fields.Float(string=u'Total versé',
                                    digits=dp.get_precision('Account'),
                                    readonly=True, )
    mutuelle_principal = fields.Float(string=u'Principal',
                                  digits=dp.get_precision('Account'),
                                  readonly=True,)
    
    @api.one
    @api.depends('mutuelle_penalite', 'mutuelle_majoration', 'mutuelle_principal')
    def _compute_mutuelle_total(self):
        self.mutuelle_total = math.ceil(
            self.mutuelle_penalite + self.mutuelle_majoration + self.mutuelle_principal)

    mutuelle_total = fields.Float(string=u'Total',
                              digits=dp.get_precision('Account'),
                              readonly=True,
                              compute='_compute_mutuelle_total',
                              store=True)
    
    cs_penalite = fields.Float(string=u'Penalite', digits=dp.get_precision(
        'Account'),  states={'draft': [('readonly', False)]}, readonly=True,)
    cs_majoration = fields.Float(string=u'Majoration', digits=dp.get_precision(
        'Account'), states={'draft': [('readonly', False)]}, readonly=True, )
    cs_principal = fields.Float(string=u'Principal',
                                digits=dp.get_precision('Account'),
                                readonly=True,)

    @api.one
    @api.depends('cs_penalite', 'cs_majoration', 'cs_principal')
    def _compute_cs_total(self):
        self.cs_total = math.ceil(
            self.cs_penalite + self.cs_majoration + self.cs_principal)

    cs_total = fields.Float(string=u'Total',
                            digits=dp.get_precision('Account'),
                            readonly=True,
                            compute='_compute_cs_total',
                            store=True)

    @api.one
    def compute_general_data(self):
        payslip_ids = self._get_payslips().mapped('id')
        total_brut_imposable = self.env['hr.dictionnary'].compute_value(
            code='BRUT_IMPOSABLE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        total_net_imposable = self.env['hr.dictionnary'].compute_value(
            code='NET_IMPOSABLE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        total_brut = self.env['hr.dictionnary'].compute_value(
            code='BRUT',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        self.write({
            'total_brut_imposable': total_brut_imposable,
            'total_net_imposable': total_net_imposable,
            'total_brut': total_brut,
        })

    @api.one
    def compute_ir_data(self):
        self.compute_general_data()
        payslip_ids = self._get_payslips().mapped('id')
        ir_principal = self.env['hr.dictionnary'].compute_value(
            code='IR',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        self.write({
            'ir_principal': ir_principal,
            'ir_total_verse': self.total_brut_imposable,
        })

    @api.one
    def compute_cimr_data(self):
        self.compute_general_data()
        payslip_ids = self._get_payslips().mapped('id')
        cimr_principal = self.env['hr.dictionnary'].compute_value(
            code='CIMR',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        self.write({
            'cimr_principal': cimr_principal,
            'cimr_total_verse': self.total_brut_imposable,
        })

    @api.one
    def compute_mutuelle_data(self):
        self.compute_general_data()
        payslip_ids = self._get_payslips().mapped('id')
        mutuelle_principal = self.env['hr.dictionnary'].compute_value(
            code='MUTUELLE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        self.write({
            'mutuelle_principal': mutuelle_principal,
            'mutuelle_total_verse': self.total_brut_imposable,
        })

    @api.one
    def compute_cs_data(self):
        self.compute_general_data()
        payslip_ids = self._get_payslips().mapped('id')
        cs_principal = self.env['hr.dictionnary'].compute_value(
            code='CONTRIBUTION_SOLIDARITE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        self.write({
            'cs_principal': cs_principal,
        })

    @api.one
    def compute_anciennete_data(self):
        self.compute_general_data()
        payslip_ids = self._get_payslips().mapped('id')
        anciennete_total = self.env['hr.dictionnary'].compute_value(
            code='ANCIENNETE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        self.write({
            'anciennete_total': anciennete_total,
        })

    anciennete_total = fields.Float(
        string=u'Total ancienneté', digits=dp.get_precision('Account'), readonly=True,)

    @api.one
    def compute_cnss_amo_data(self):
        self.compute_general_data()
        payslip_ids = self._get_payslips().mapped('id')
        total_prestation_sociale = self.env['hr.dictionnary'].compute_value(
            code='PRESTATION_SOCIALE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        total_prestation_sociale_base = self.env['hr.dictionnary'].compute_value(
            code='PRESTATION_SOCIALE_BASE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        total_prestation_familiale = self.env['hr.dictionnary'].compute_value(
            code='PRESTATION_FAMILIALE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        total_prestation_familiale_base = self.env['hr.dictionnary'].compute_value(
            code='PRESTATION_FAMILIALE_BASE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        total_tax_formation_professionnelle = self.env['hr.dictionnary'].compute_value(
            code='TAX_FORMATION_PROFESSIONELLE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        total_tax_formation_professionnelle_base = self.env['hr.dictionnary'].compute_value(
            code='TAX_FORMATION_PROFESSIONELLE_BASE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        total_amo_base = self.env['hr.dictionnary'].compute_value(
            code='AMO_BASE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        total_amo_base_base = self.env['hr.dictionnary'].compute_value(
            code='AMO_BASE_BASE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        total_amo_solidarite = self.env['hr.dictionnary'].compute_value(
            code='AMO_OBLIGATOIRE_SOLIDARITE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )
        total_amo_solidarite_base = self.env['hr.dictionnary'].compute_value(
            code='AMO_OBLIGATOIRE_SOLIDARITE_BASE',
            payslip_ids=payslip_ids,
            state=self.payslip_state,
        )

        self.write({
            'total_amo_base': total_amo_base,
            'total_amo_base_base': total_amo_base_base,
            'total_amo_solidarite': total_amo_solidarite,
            'total_amo_solidarite_base': total_amo_solidarite_base,
            'total_amo': total_amo_solidarite + total_amo_base,
            'total_prestation_sociale': total_prestation_sociale,
            'total_prestation_sociale_base': total_prestation_sociale_base,
            'total_prestation_familiale': total_prestation_familiale,
            'total_prestation_familiale_base': total_prestation_familiale_base,
            'total_tax_formation_professionnelle': total_tax_formation_professionnelle,
            'total_tax_formation_professionnelle_base': total_tax_formation_professionnelle_base,
            'total_cnss': total_tax_formation_professionnelle + total_prestation_familiale + total_prestation_sociale,
        })

    @api.onchange('company_child', 'company_parent')
    def _onchange_company_child_parent(self):
        ids = []
        companies = self.env['res.company']
        if self.company_child:
            companies |= self.env['res.company'].search(
                [('parent_id', '!=', False)])
        if self.company_parent:
            companies |= self.env['res.company'].search(
                [('parent_id', '=', False)])
        self.company_ids = companies

    company_ids = fields.Many2many(
        'res.company', string=u'Sociétés',  required=True, states={'draft': [('readonly', False)]}, readonly=True, )

    code_helper = fields.Char(string=u'Code', size=64,)

    @api.onchange('code_helper')
    def _onchange_code_helper(self):
        if self.code_helper:
            self.type_id = self.env['hr.common.report.type'].search(
                [('code', '=', self.code_helper)])

    code = fields.Char(related='type_id.code', store=True,)
    workflow = fields.Boolean(related='type_id.workflow',  store=True,)

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
            self.date_start = self.fiscalyear_id.date_start
            self.date_end = self.fiscalyear_id.date_end
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
        self.date_start = False
        self.date_end = False
        if self.period_id:
            self.date_from = self.period_id.date_start
            self.date_to = self.period_id.date_end

    @api.one
    def set_draft(self):
        self.state = 'draft'

    @api.one
    def set_confirm(self):
        if self.code == 'ir':
            self.compute_ir_data()
        if self.code == 'cnss_amo':
            self.compute_cnss_amo_data()
        if self.code == 'cs':
            self.compute_cs_data()
        if self.code == 'cimr':
            self.compute_cimr_data()
        if self.code == 'mutuelle':
            self.compute_mutuelle_data()
        self.state = 'confirm'

    @api.one
    def set_done(self):
        self.state = 'done'

    @api.one
    def set_paid(self):
        self.state = 'paid'

    @api.one
    def set_cancel(self):
        self.state = 'cancel'

    @api.multi
    def action_print_cnss_amo_simple(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_cnss_declaration')

    @api.multi
    def action_print_anciennete(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_anciennete')

    @api.multi
    def action_print_cnss_amo_bordereau(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_cnss_declaration_versement')

    @api.multi
    def action_print_ir_simple(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_ir_declaration')

    @api.multi
    def action_print_ir_bordereau(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_ir_declaration_versement')

    @api.multi
    def action_print_cimr_simple(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_cimr_declaration')
    
    @api.multi
    def action_print_mutuelle_simple(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_mutuelle_declaration')

    @api.multi
    def action_print_cimr_bordereau(self):
        raise Warning(
            _('Please contact your administrator to add this feature'))

    @api.multi
    def action_print_cs_simple(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_cs_declaration')

    @api.multi
    def action_print_cs_bordereau(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_ma_hr_payroll.report_cs_declaration_versement')

# AUDIT
    @api.one
    def compute_audit_data(self):
        master_domain = [('company_id', 'in', self.company_ids.mapped('id'))]
        if self.departments_id:
            master_domain.append(
                ('department_id', 'in', self.departments_id.mapped('id')),)

        all_employees = self.env['hr.employee'].search(master_domain)

        emp_contract_ids = self.env['hr.employee'].search(master_domain) - self.env['hr.employee'].search([
            ('is_contract_valid_by_context', 'in', (self.date_from,self.date_to)),
        ])

        valid_contracts = self.env['hr.contract'].search(master_domain + [
            ('is_contract_valid_by_context', 'in', (self.date_from,self.date_to)),
        ])

        valid_employees = self.env['hr.employee'].search(master_domain + [
            ('is_contract_valid_by_context', 'in', (self.date_from,self.date_to)),
        ])

        all_payslips_domain = master_domain + [
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
        ]
        if self.payslip_state != 'all':
            all_payslips_domain.append(('state', '=', self.payslip_state))
        all_payslips = self.env['hr.payslip'].search(all_payslips_domain)

        more_payslips = []
        for emp in all_payslips.mapped('employee_id'):
            if len(all_payslips.filtered(lambda r: r.employee_id.id == emp.id))>1:
                more_payslips.append(emp.id)
        more_payslips = list(set(more_payslips))

        payslip_ids = valid_contracts - all_payslips.mapped('contract_id')

        self.write({
            'emp_mobile_ids': [(6, 0, all_employees.filtered(lambda r: not r.mobile_phone).mapped('id'))],
            'emp_bank_ids': [(6, 0, valid_employees.filtered(lambda r: not r.bank_account_id).mapped('id'))],
            'emp_contract_ids': [(6, 0, emp_contract_ids.mapped('id'))],
            'emp_smig_ids': [(6, 0, valid_contracts.filtered(lambda r: r.salary_by_hour < r.company_id.smig_by_hour).mapped('id'))],
            'emp_job_ids': [(6, 0, valid_contracts.filtered(lambda r: not r.job_id).mapped('id'))],
            'emp_cnss_ids': [(6, 0, valid_contracts.filtered(lambda r: r.cnss_ok).mapped('employee_id').filtered(lambda r: not r.check_cnss_conformite()[0]).mapped('id'))],
            'emp_cimr_ids': [(6, 0, valid_contracts.filtered(lambda r: r.cimr_ok).mapped('employee_id').filtered(lambda r: not r.cimr or len(r.cimr) != 7).mapped('id'))],
            'emp_department_ids': [(6, 0, valid_contracts.mapped('employee_id').filtered(lambda r: not r.department_id).mapped('id'))],
            'emp_payslip_ids': [(6, 0, payslip_ids.mapped('employee_id.id'))],
            'emp_more_payslip_ids': [(6, 0, more_payslips)],
            'emp_voucher_ids': [(6, 0, all_payslips.filtered(lambda r: r.state2 == 'done').mapped('id'))],
            'emp_accounting_ids': [(6, 0, all_payslips.filtered(lambda r: r.state == 'done' and not r.move_id).mapped('id'))],
        })

    emp_mobile_ids = fields.Many2many(
        comodel_name='hr.employee',
        column1='mobile_id',
        column2='employee_id',
        relation='audit_mobile_employee_rel',
        string=u'Mobile',  readonly=True, )

    emp_more_payslip_ids = fields.Many2many(
        comodel_name='hr.employee',
        column1='more_payslip_id',
        column2='employee_id',
        relation='audit_more_payslip_employee_rel',
        string=u'Plusieurs bulletins',  readonly=True, )

    emp_cnss_ids = fields.Many2many(
        comodel_name='hr.employee',
        column1='cnss_id',
        column2='employee_id',
        relation='audit_cnss_employee_rel',
        string=u'CNSS',  readonly=True, )

    emp_cimr_ids = fields.Many2many(
        comodel_name='hr.employee',
        column1='cimr_id',
        column2='employee_id',
        relation='audit_cimr_employee_rel',
        string=u'CIMR',  readonly=True, )

    emp_bank_ids = fields.Many2many(
        comodel_name='hr.employee',
        column1='bank_id',
        column2='employee_id',
        relation='audit_bank_employee_rel',
        string=u'RIB',  readonly=True, )

    emp_contract_ids = fields.Many2many(
        comodel_name='hr.employee',
        column1='contract_id',
        column2='employee_id',
        relation='audit_contract_employee_rel',
        string=u'Contrats',  readonly=True, )

    emp_smig_ids = fields.Many2many(
        comodel_name='hr.contract',
        column1='smig_id',
        column2='contract_id',
        relation='audit_smig_contract_rel',
        string=u'SMIG',  readonly=True, )

    emp_job_ids = fields.Many2many(
        comodel_name='hr.contract',
        column1='job_id',
        column2='contract_id',
        relation='audit_job_contract_rel',
        string=u'Postes',  readonly=True, )

    emp_department_ids = fields.Many2many(
        comodel_name='hr.employee',
        column1='department_id',
        column2='employee_id',
        relation='audit_department_employee_rel',
        string=u'Départements',  readonly=True, )

    emp_payslip_ids = fields.Many2many(
        comodel_name='hr.employee',
        column1='payslip_id',
        column2='employee_id',
        relation='audit_payslip_employee_rel',
        string=u'Bulletins de paie',  readonly=True, )

    emp_voucher_ids = fields.Many2many(
        comodel_name='hr.payslip',
        column1='voucher_id',
        column2='employee_id',
        relation='audit_voucher_payslip_rel',
        string=u'Règlements',  readonly=True, )

    emp_accounting_ids = fields.Many2many(
        comodel_name='hr.payslip',
        column1='accounting_id',
        column2='employee_id',
        relation='audit_accounting_payslip_rel',
        string=u'Comptabilité',  readonly=True, )


class hr_common_report_type(models.Model):
    _name = 'hr.common.report.type'
    _description = 'Type of common report'

    name = fields.Char(string=u'Nom', size=64, required=True,)
    code = fields.Char(string=u'Code', size=64,  required=True, )
    workflow = fields.Boolean(string=u'Workflow', default=True,)
