# encoding: utf-8

from odoo import models, fields, api, _
import time
import odoo.addons.decimal_precision as dp


class res_company(models.Model):
    _inherit = ['res.company', 'mail.thread', 'ir.needaction_mixin']
    _name = 'res.company'

    @api.multi
    def fix_accounts_reconciliation(self):
        accounts = self.env['account.account'].search([('reconcile', '=', False)]).filtered(
            lambda r: r.code.startswith('34') or r.code.startswith('44'))
        for account in accounts:
            account.reconcile = True

    @api.multi
    def fix_fr_lang(self):
        langs = self.env['res.lang'].search([('code', '=', 'fr_FR')])
        for lang in langs:
            lang.write({
                'date_format' : '%d/%m/%Y',
                'grouping' : '[3,3,3,-1]',
                'thousands_sep' : u'\u00A0',
            })

    @api.multi
    def fix_config_general(self):
        configs = self.env['base.config.settings'].search([])
        for config in configs:
            config.execute()

    @api.multi
    def get_company_root(self):
        company = self.env.user.company_id
        while company.parent_id:
            company = company.parent_id
        return company

    @api.one
    @api.depends("parent_id")
    def _compute_main_company(self):
        main_company_id = self.sudo()
        while main_company_id.parent_id:
            main_company_id = main_company_id.parent_id
        self.main_company_id = main_company_id

    main_company_id = fields.Many2one(
        'res.company', string=u'Main company', compute='_compute_main_company',)

    @api.one
    @api.depends('fp_id')
    def _compute_fp_taux(self):
        if self.fp_id:
            self.fp_taux = self.fp_id.rate
        else:
            self.fp_taux = 0

    @api.one
    @api.depends('fp_taux')
    def _compute_fp_taux_str(self):
        self.fp_taux_str = str(self.fp_taux) + ' %'


    @api.one
    def _compute_effective(self):
        date = self.env.context.get('date', time.strftime('%Y-%m-%d'))
        date_start = self.env.context.get('date_start', False)
        date_stop = self.env.context.get('date_stop', False)
        if date_start and date_stop:
            main_domain = [
                ('is_contract_valid_by_context',
                 'in', (date_start, date_stop,)),
                ('employee_id.company_id', 'child_of', self.id)]
        else:
            main_domain = [
                ('is_contract_valid_by_context', '=', date),
                ('employee_id.company_id', 'child_of', self.id)]
        # PERMANENT
        domain = main_domain[:]
        domain.append(('type_id.type', '=', 'permanent'))
        contracts = self.env['hr.contract'].search(domain)
        self.nbr_employees_permanent = len(contracts.mapped('employee_id'))
        # OCCASIONNEL
        domain = main_domain[:]
        domain.append(('type_id.type', '=', 'occasional'))
        contracts = self.env['hr.contract'].search(domain)
        self.nbr_employees_occasional = len(contracts.mapped('employee_id'))
        # OCCASIONNEL
        domain = main_domain[:]
        domain.append(('type_id.type', '=', 'trainee'))
        contracts = self.env['hr.contract'].search(domain)
        self.nbr_employees_trainees = len(contracts.mapped('employee_id'))
        # EFFECTIF
        domain = main_domain[:]
        contracts = self.env['hr.contract'].search(domain)
        self.nbr_employees = len(contracts.mapped('employee_id'))

    initial = fields.Char(string=u'Initial', size=64,)

    cnss_day_limit = fields.Integer(string=u'Dernier jour de la regularisation', default=10,  required=True,  )


    _sql_constraints = [
        ('initial_unique', 'UNIQUE (initial)',
         'The initial of the company must be unique !'),
    ]

    simpleir_employee_id = fields.Many2one(
        'hr.employee', string=u'Contribuable (Simple IR)', track_visibility='onchange')
    manager_id = fields.Many2one(
        'hr.employee', string=u'Gérant', track_visibility='onchange')

    nbr_employees_permanent = fields.Integer(
        string=u'Nombre des permanents', compute="_compute_effective")
    nbr_employees_occasional = fields.Integer(
        string=u'Nombre des occasionnels', compute="_compute_effective")
    nbr_employees_trainees = fields.Integer(
        string=u'Nombre des stagiaires', compute="_compute_effective")
    nbr_employees = fields.Integer(
        string=u'Total des employés', compute="_compute_effective")

    working_hours = fields.Many2one(
        'resource.calendar', string=u'Temps de travail', track_visibility='onchange')

    payroll_journal_id = fields.Many2one('account.journal',
                                         string=u'Journal',
                                         default=lambda self: self.env['account.journal'].search(
                                             [('code', 'like', 'OD'), ], limit=1),
                                         required=True, track_visibility='onchange'
                                         )
    smig_by_hour = fields.Float(
        string=u'SMIG horaire',
        digits=dp.get_precision('Salary'),
        default=13.46,
        required=True, track_visibility='onchange'
    )
    rate_hours_on_day = fields.Float(
        string=u'Taux de conversion des heures en jours lors de la modification du contrat',
        digits=dp.get_precision('Salary Rate'),
        default=lambda self: 7.34615,
        required=True, track_visibility='onchange',
        help='Ce taux sera utilisé juste lorsqu\'un changement est effectué sur un contrat, il affecte les conversion automatique sur les données d\'un contrat',
    )
    default_hours_on_worked_day = fields.Float(
        string=u'Nombre d\'heures dans un jour travaillé',
        digits=dp.get_precision('Salary Rate'),
        default=lambda self: 7.34615,
        required=True, track_visibility='onchange'
    )
    default_hours_on_leave = fields.Float(
        string=u'Nombre d\'heures dans un congé',
        digits=dp.get_precision('Salary Rate'),
        default=lambda self: 7.34615,
        required=True, track_visibility='onchange'
    )
    default_hours_on_holiday = fields.Float(
        string=u'Nombre d\'heures dans un jour férié',
        digits=dp.get_precision('Salary Rate'),
        default=8,
        required=True, track_visibility='onchange'
    )

    nbr_days_declared = fields.Float(
        string=u'Nombre de jours déclaré',
        digits=dp.get_precision('Salary'),
        default=26,
        required=True, track_visibility='onchange'
    )
    nbr_hours_declared = fields.Float(
        string=u'Nombre d\'heures déclaré',
        digits=dp.get_precision('Salary'),
        default=191,
        required=True, track_visibility='onchange'
    )

    rh_users_id = fields.Many2many(
        'res.users', 'company_id', 'user_id', 'company_rh_user_rel', string=u'Responsable RH', track_visibility='onchange')

    based_on_ids = fields.Many2many(
        comodel_name='hr.contract.base',
        relation='res_company_based_on_rel',
        column1='company_id',
        column2='based_on_id',
        string=u'Basé sur',  default=lambda self: self.env['hr.contract.base'].search([('code','in',['fixed_days','worked_hours'])]),  )

    cf_plafond = fields.Float('Plafond des charges familiales', digits=dp.get_precision(
        'Local 2'), required=True, default=180,)
    af_plafond = fields.Float('Plafond des charges familiales', digits=dp.get_precision(
        'Local 2'), required=True, default=180,)
    cf_amount = fields.Float('Montant pour une charge familiale', digits=dp.get_precision(
        'Local 2'), required=True, default=30,)
    fp_plafond = fields.Float('Plafond des frais professionels', digits=dp.get_precision(
        'Local 2'), required=True, default=2500,)
    fp_taux = fields.Float('Taux des frais professionels', digits=dp.get_precision(
        'Local 4'),  compute='_compute_fp_taux', store=True,)
    fp_id = fields.Many2one(
        'l10n.ma.fp', string=u'Taux des frais professionels', required=False,
        default=lambda self: self.env['l10n.ma.fp'].search([('rate', '=', 20)], limit=1),)
    fp_taux_str = fields.Char('Taux des frais professionels', size=64,
                              compute='_compute_fp_taux_str', store=True, readonly=True,)
    nbr_af1_plafond = fields.Integer(
        string=u'Plafond de nombre des allocations familiales (1ere tranche)', default=3, required=True)
    nbr_af2_plafond = fields.Integer(
        string=u'Plafond de nombre des allocations familiales (2eme tranche)', default=6, required=True)
    af1_amount = fields.Float('Montant des allocations familiales (1ere tranche)', digits=dp.get_precision(
        'Local 2'), required=True, default=200,)
    af2_amount = fields.Float('Montant des allocations familiales (2eme tranche)', digits=dp.get_precision(
        'Local 2'), required=True, default=36,)

    code_digits = fields.Integer('# digits', required=True, default=0)
    code_digits_min = fields.Integer('# digits min', readonly=True,)


    @api.one
    def process_code_digits(self):
        # FIXME: Trim should be auto and check 5141 problem
        accounts = self.env['account.account'].search(
            [('company_id', '=', self.id)])
#         for account in accounts :
#             if account.type <> 'view' :
#                 code = int(account.code[::-1])
#                 code = str(code)[::-1]
#                 if len(code) > self.code_digits :
#                     raise Warning(_('The code [%s] block the operation.\nTry to trim it firstly to %s digits.') % (code, self.code_digits,))
        for account in accounts:
            if account.type <> 'view':
                part1 = account.code[:self.code_digits_min - 1]
                part2 = account.code[self.code_digits_min - 1:]
                part2 = part2.strip('0')
                code = part1 + '0' * \
                    (self.code_digits - len(str(part1)) - len(part2)) + part2
                account.code = code

    @api.one
    @api.constrains('fp_taux', 'code_digits')
    def _check_taux(self):
        if self.fp_taux < 0 or self.fp_taux > 100:
            raise Warning(_('Le taux doit etre compris entre 0 et 100'))
        if self.code_digits < self.code_digits_min:
            raise Warning(
                _('Le nombre de chiffre doitre superieur a %s') % self.code_digits_min)


    @api.multi
    def write(self, vals):
        res = super(res_company, self).write(vals)
        for parent in self:
            for child in parent.child_ids :
                child.write({
                    'cf_plafond' : parent.cf_plafond,
                    'af_plafond' : parent.af_plafond,
                    'cf_amount' : parent.cf_amount,
                    'fp_plafond' : parent.fp_plafond,
                    'nbr_af1_plafond' : parent.nbr_af1_plafond,
                    'nbr_af2_plafond' : parent.nbr_af2_plafond,
                    'af1_amount' : parent.af1_amount,
                    'af2_amount' : parent.af2_amount,
                    'cnss_day_limit' : parent.cnss_day_limit,
                    'manager_id' : parent.manager_id and parent.manager_id.id or False,
                    'simpleir_employee_id' : parent.simpleir_employee_id and parent.simpleir_employee_id.id or False,
                    'payroll_journal_id' : parent.payroll_journal_id and parent.payroll_journal_id.id or False,
                })
        return res

    avance_amount_limit_min = fields.Float(
        string=u'Minimum', digits=dp.get_precision('Account'),  default=0.0)
    avance_amount_limit_max = fields.Float(
        string=u'Maximum', digits=dp.get_precision('Account'),  default=5000)
    avance_amount_limit_day_from = fields.Integer(
        string=u'De jour',  default=1)
    avance_amount_limit_day_to = fields.Integer(string=u'Au jour', default=31)

    rubrique_amount_limit_min = fields.Float(
        string=u'Minimum', digits=dp.get_precision('Account'),  default=0.0)
    rubrique_amount_limit_max = fields.Float(
        string=u'Maximum', digits=dp.get_precision('Account'),  default=5000)
    rubrique_amount_limit_day_from = fields.Integer(
        string=u'De jour',  default=1)
    rubrique_amount_limit_day_to = fields.Integer(string=u'Au jour', default=31)

    avantage_amount_limit_min = fields.Float(
        string=u'Minimum', digits=dp.get_precision('Account'),  default=0.0)
    avantage_amount_limit_max = fields.Float(
        string=u'Maximum', digits=dp.get_precision('Account'),  default=5000)
    avantage_amount_limit_day_from = fields.Integer(
        string=u'De jour',  default=1)
    avantage_amount_limit_day_to = fields.Integer(string=u'Au jour', default=31)

    cdi_base_salary_rate = fields.Float(string=u'Salaire de base', digits=dp.get_precision('Account'), )
    cdi_hsupp_rate = fields.Float(string=u'Heures supplémentaires', digits=dp.get_precision('Account'),  )
    cdi_imposable_rate = fields.Float(string=u'Éléments imposables', digits=dp.get_precision('Account'),  )
    cdi_exonore_rate = fields.Float(string=u'Éléments non imposables', digits=dp.get_precision('Account'),  )
    cdi_expenses_rate = fields.Float(string=u'Notes de frais', digits=dp.get_precision('Account'),  )
    cdi_legal_leave_rate = fields.Float(string=u'Congé légal', digits=dp.get_precision('Account'),  )
    cdi_seniority_rate = fields.Float(string=u'Ancienneté', digits=dp.get_precision('Account'),  )

    cdd_base_salary_rate = fields.Float(string=u'Salaire de base', digits=dp.get_precision('Account'), )
    cdd_hsupp_rate = fields.Float(string=u'Heures supplémentaires', digits=dp.get_precision('Account'),  )
    cdd_imposable_rate = fields.Float(string=u'Éléments imposables', digits=dp.get_precision('Account'),  )
    cdd_exonore_rate = fields.Float(string=u'Éléments non imposables', digits=dp.get_precision('Account'),  )
    cdd_expenses_rate = fields.Float(string=u'Notes de frais', digits=dp.get_precision('Account'),  )
    cdd_legal_leave_rate = fields.Float(string=u'Congé légal', digits=dp.get_precision('Account'),  )
    cdd_seniority_rate = fields.Float(string=u'Ancienneté', digits=dp.get_precision('Account'),  )

    @api.multi
    def generate_avance_limits(self):
        self.ensure_one()
        self.message_post(_('Générer les limites des avances'))
        avance_exist_ids = self.avance_limit_ids.search(
            [('company_id', '=', self.id)]).mapped('avance_id.id')
        for avance in self.env['hr.avance'].search([('id', 'not in', avance_exist_ids)]):
            self.avance_limit_ids.create({
                'company_id': self.id,
                'avance_id': avance.id,
                'day_from': self.avance_amount_limit_day_from,
                'day_to': self.avance_amount_limit_day_to,
                'amount_from': self.avance_amount_limit_min,
                'amount_to': self.avance_amount_limit_max,
            })

    @api.multi
    def generate_rubrique_limits(self):
        self.ensure_one()
        self.message_post(_('Générer les limites des rubriques'))
        rubrique_exist_ids = self.rubrique_limit_ids.search(
            [('company_id', '=', self.id)]).mapped('rubrique_id.id')
        for rubrique in self.env['hr.rubrique'].search([('id', 'not in', rubrique_exist_ids)]):
            self.rubrique_limit_ids.create({
                'company_id': self.id,
                'rubrique_id': rubrique.id,
                'day_from': self.rubrique_amount_limit_day_from,
                'day_to': self.rubrique_amount_limit_day_to,
                'amount_from': self.rubrique_amount_limit_min,
                'amount_to': self.rubrique_amount_limit_max,
            })

    @api.multi
    def generate_avantage_limits(self):
        self.ensure_one()
        self.message_post(_('Générer les limites des avantages'))
        avantage_exist_ids = self.avantage_limit_ids.search(
            [('company_id', '=', self.id)]).mapped('avantage_id.id')
        for avantage in self.env['hr.avantage'].search([('id', 'not in', avantage_exist_ids)]):
            self.avantage_limit_ids.create({
                'company_id': self.id,
                'avantage_id': avantage.id,
                'day_from': self.avantage_amount_limit_day_from,
                'day_to': self.avantage_amount_limit_day_to,
                'amount_from': self.avantage_amount_limit_min,
                'amount_to': self.avantage_amount_limit_max,
            })

    @api.multi
    def generate_holiday_status_limits(self):
        self.ensure_one()
        self.message_post(_('Générer les limites pour les congés'))
        holiday_status_exist_ids = self.holiday_status_limit_ids.search(
            [('company_id', '=', self.id)]).mapped('holiday_status_id.id')
        for holiday_status in self.env['hr.holidays.status'].search([('id', 'not in', holiday_status_exist_ids)]):
            self.holiday_status_limit_ids.create({
                'company_id': self.id,
                'holiday_status_id': holiday_status.id,
            })

    @api.multi
    def reset_avance_limits(self):
        self.ensure_one()
        self.message_post(_('Réinitialiser les limites des avances'))
        self.avance_limit_ids.search([('company_id', '=', self.id)]).unlink()

    @api.multi
    def reset_rubrique_limits(self):
        self.ensure_one()
        self.message_post(_('Réinitialiser les limites des rubriques'))
        self.rubrique_limit_ids.search([('company_id', '=', self.id)]).unlink()

    @api.multi
    def reset_avantage_limits(self):
        self.ensure_one()
        self.message_post(_('Réinitialiser les limites des avantages'))
        self.avantage_limit_ids.search([('company_id', '=', self.id)]).unlink()


    avance_limit_ids = fields.One2many(
        'hr.avance.limit', 'company_id', string=u'Limites des avances', track_visibility='onchange')
    rubrique_limit_ids = fields.One2many(
        'hr.rubrique.limit', 'company_id', string=u'Limites des rubriques', track_visibility='onchange')
    avantage_limit_ids = fields.One2many(
        'hr.avantage.limit', 'company_id', string=u'Limites des avantages', track_visibility='onchange')


class hr_template_limit(models.Model):
    _name = 'hr.template.limit'
    _description = 'Limit template'

    company_id = fields.Many2one(
        'res.company', string=u'Société', required=True)
    day_from = fields.Integer(string=u'De jour', default=1,  required=True,)
    day_to = fields.Integer(string=u'Au jour',  default=31, required=True,)
    amount_from = fields.Float(string=u'Montant de', digits=dp.get_precision(
        'Account'), default=0.0,  required=True,)
    amount_to = fields.Float(string=u'Montant à', digits=dp.get_precision(
        'Account'),   default=100000, required=True, )


class hr_avance_limit(models.Model):
    _name = 'hr.avance.limit'
    _inherit = 'hr.template.limit'
    _description = 'Advance limit'

    avance_id = fields.Many2one('hr.avance', string=u'Avance',  required=True, )


class hr_rubrique_limit(models.Model):
    _name = 'hr.rubrique.limit'
    _inherit = 'hr.template.limit'
    _description = 'Rubrique limit'

    rubrique_id = fields.Many2one(
        'hr.rubrique', string=u'Rubrique',  required=True, )


class hr_avantage_limit(models.Model):
    _name = 'hr.avantage.limit'
    _inherit = 'hr.template.limit'
    _description = 'Advantage limit'

    avantage_id = fields.Many2one(
        'hr.avantage', string=u'Avantage',  required=True, )
