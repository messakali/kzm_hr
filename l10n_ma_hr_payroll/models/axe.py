# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning

# TOREAD : Implement on other case :
# 1 - Create a MIN_SEQUENCE
# 2 - Add condition in the functions create and write
# 3 - Create the function _get_new_item_dicts() that take
# predefined args and return defined tuple
# It's all

TAXABLE = '_TAXABLE'
EXONORE = '_EXONORE'

TAXABLE_SANS_RESTE = '_TAXABLE_SANS_RESTE'
TAXABLE_AVEC_RESTE = '_TAXABLE_AVEC_RESTE'

RESTE_TAXABLE = '_RESTE_TAXABLE'
EXONORE_SANS_RESTE = '_EXONORE_SANS_RESTE'

HORAIRE = '_HORAIRE'
JOURNALIER = '_JOURNALIER'

PARENT = '_PARENT'
SALARIALE = '_SALARIALE'
PATRONALE = '_PATRONALE'

SALARIALE_PLAFOND = '_SALARIALE_PLAFOND'
PATRONALE_PLAFOND = '_PATRONALE_PLAFOND'

MIN_STATUS = 'MIN_STATUS'
MIN_AVANTAGE = 'MIN_AVANTAGE'
MIN_RUBRIQUE = 'MIN_RUBRIQUE'
MIN_COTISATION = 'MIN_COTISATION'
MIN_INTERET = 'MIN_INTERET'
MIN_AVANCE = 'MIN_AVANCE'


class hr_axe(models.Model):
    _name = 'hr.axe'
    _description = 'Axe to create rules'

    cotisation_id = fields.Many2one('hr.cotisation', string=u'Cotisation',)
    avance_id = fields.Many2one('hr.avance', string=u'Avance',)
    avantage_id = fields.Many2one('hr.avantage', string=u'Avantage',)
    rubrique_id = fields.Many2one('hr.rubrique', string=u'Rubrique',)
    holiday_status_id = fields.Many2one(
        'hr.holidays.status', string=u'Type de congé',)

    rule_parent_id = fields.Many2one('hr.salary.rule', string=u'Règle mère',)
    rule_salariale_id = fields.Many2one(
        'hr.salary.rule', string=u'Règle salariale',)
    rule_salariale_plafond_id = fields.Many2one(
        'hr.salary.rule', string=u'Règle salariale plafonnée',)
    rule_patronale_id = fields.Many2one(
        'hr.salary.rule', string=u'Règle patronale',)
    rule_patronale_plafond_id = fields.Many2one(
        'hr.salary.rule', string=u'Règle patronale plafonnée',)

    # HELPERS
    @api.multi
    def _get_category(self, code):
        category = self.env['hr.salary.rule.category'].search(
            [('code', '=', code)], limit=1)
        if not category:
            raise Warning(
                _('Veuillez définir une catégorie avec le code [%s]') % code)
        return category.id

    @api.multi
    def _get_min(self, code):
        return int(self.env['ir.config_parameter'].get_param(code, '500'))

    @api.multi
    def _get_rule(self, code):
        rule = self.env['hr.salary.rule'].search(
            [('code', '=', code)], limit=1)
        if not rule:
            raise Warning(
                _('Veuillez définir une règle avec le code [%s]') % code)
        return rule.id

    @api.multi
    def _clean_python_code(self, code):
        code = code.replace('taux_horaire',' inputs.SALAIRE_PAR_HEURE.amount ')
        code = code.replace('taux_journalier',' inputs.SALAIRE_PAR_JOUR.amount ')
        code = code.replace('base_salariale',' categories.BASE_SALARIALE ')
        code = code.replace('nombre_de_jours',' categories.PERIODE_JOURS ')
        code = code.replace('nombre_de_heures',' categories.PERIODE_HEURES ')
        code = code.replace('montant_anciennete',' categories.PRIME_ANCIENNETE ')
        code = code.replace('anciennete',' inputs.ANCIENNETE.amount ')
        code = code.replace('heures_supp',' categories.HS ')
        code = code.replace('smig',' payslip.company_id.smig_by_hour ')
        code = code.replace('distance',' employee.distance_home ')
        code = code.replace('urbain',' employee.habitation_type == \'urbain\' ')
        code = code.replace('nbr_enfants',' employee.children ')
        code = code.replace('plafond_ind_kilometrique',' plafond_ind_kilometrique(payslip) ')
        return str(code)

    @api.multi
    def _clean(self):
        self.ensure_one()
        if self.rule_parent_id:
            self.rule_parent_id.condition_select = 'none'
            self.rule_parent_id.amount_select = 'fix'
            self.rule_parent_id.quantity = '0'
            self.rule_parent_id.amount_fix = 0
        if self.rule_salariale_id:
            self.rule_salariale_id.condition_select = 'none'
            self.rule_salariale_id.amount_select = 'fix'
            self.rule_salariale_id.quantity = '0'
            self.rule_salariale_id.amount_fix = 0
        if self.rule_salariale_plafond_id:
            self.rule_salariale_plafond_id.condition_select = 'none'
            self.rule_salariale_plafond_id.amount_select = 'fix'
            self.rule_salariale_plafond_id.quantity = '0'
            self.rule_salariale_plafond_id.amount_fix = 0
        if self.rule_patronale_id:
            self.rule_patronale_id.condition_select = 'none'
            self.rule_patronale_id.amount_select = 'fix'
            self.rule_patronale_id.quantity = '0'
            self.rule_patronale_id.amount_fix = 0
        if self.rule_patronale_plafond_id:
            self.rule_patronale_plafond_id.condition_select = 'none'
            self.rule_patronale_plafond_id.amount_select = 'fix'
            self.rule_patronale_plafond_id.quantity = '0'
            self.rule_patronale_plafond_id.amount_fix = 0

    @api.multi
    def _get_holidays_dicts(self, status):
        min_status = status.search([], order='sequence asc', limit=1)
        min_sequence = min_status and min_status.sequence or 0
        rule_parent_id_data = {
            'name': status.name,
            'code': status.code + PARENT,
            'sequence': self._get_min(MIN_STATUS),
            'parent_rule_id': self._get_rule('SALAIRES'),
            'category_id': self._get_category('AUTRES_TOTAUX'),
            'show_on_payslip': 'never',
            'auto': True,
            'holiday_status_id': status.id,
        }
        #GAIN_OR_AUTRE_GAIN = not status.is_hs and status.majoration and 'AUTRE_GAIN' or 'GAIN'
        GAIN_OR_AUTRE_GAIN =  'AUTRE_GAIN'
        rule_salariale_id_data = not status.is_hs and not status.is_rappel and {
            'name': status.name,
            'code': status.code + JOURNALIER,
            'sequence': self._get_min(MIN_STATUS) + status.sequence - min_sequence + 1,
            'show_on_payslip': status.show_on_payslip,
            'category_id': status.is_retained and self._get_category('PERTE') or self._get_category(GAIN_OR_AUTRE_GAIN),
            'condition_select': 'python',
            'condition_python': 'result = contract.based_on in ["fixed_days","worked_days","attended_days","timesheet_days"]',
            'amount_select': 'flexible_percentage',
            'quantity': 'worked_days.' + status.code + '.number_of_days',
            'rate_val': '100',
            'base_val': 'inputs.SALAIRE_PAR_JOUR.amount * ' + str(1 + status.majoration / 100.),
            'analytic_account_id': status.analytic_account_id and status.analytic_account_id.id or False,
            'account_tax_id': status.account_tax_id and status.account_tax_id.id or False,
            'account_debit': status.account_debit and status.account_debit.id or False,
            'account_credit': status.account_credit and status.account_credit.id or False,
            'auto': True,
            'holiday_status_id': status.id,
        } or {}
        rule_salariale_plafond_id_data = {}
        rule_patronale_id_data = not status.is_rappel and {
            'name': status.name,
            'code': status.code + HORAIRE,
            'sequence': self._get_min(MIN_STATUS) + status.sequence - min_sequence + 1,
            'show_on_payslip': status.show_on_payslip,
            'category_id': (status.is_hs and self._get_category('HS')) or (status.is_retained and self._get_category('PERTE')) or self._get_category(GAIN_OR_AUTRE_GAIN),
            'condition_select': status.is_hs and 'none' or 'python',
            'condition_python': 'result = contract.based_on in ["fixed_hours","worked_hours","attended_hours","timesheet_hours"]',
            'amount_select': 'flexible_percentage',
            'quantity':  'worked_days.' + status.code + '.number_of_hours',
            'rate_val': '100',
            'base_val': 'inputs.SALAIRE_PAR_HEURE.amount * ' + str(1 + status.majoration / 100.),
            'analytic_account_id': status.analytic_account_id and status.analytic_account_id.id or False,
            'account_tax_id': status.account_tax_id and status.account_tax_id.id or False,
            'account_debit': status.account_debit and status.account_debit.id or False,
            'account_credit': status.account_credit and status.account_credit.id or False,
            'auto': True,
            'holiday_status_id': status.id,
        } or {}
        rule_patronale_plafond_id_data = {}
        return rule_parent_id_data, rule_salariale_id_data, rule_salariale_plafond_id_data, rule_patronale_id_data, rule_patronale_plafond_id_data

    @api.multi
    def _get_avance_dicts(self, avance):
        is_interest = avance.interest_rate and True or False
        rule_parent_id_data = {
            'name': avance.name,
            'code': avance.code + PARENT,
            'sequence': is_interest and self._get_min(MIN_INTERET) or self._get_min(MIN_AVANCE),
            'parent_rule_id': self._get_rule('SALAIRES'),
            'category_id': self._get_category('AUTRES_TOTAUX'),
            'show_on_payslip': 'never',
            'auto': True,
            'avance_id': avance.id,
        }
        rule_salariale_id_data = {
            'name': avance.name,
            'code': avance.code,
            'sequence': is_interest and self._get_min(MIN_INTERET) or self._get_min(MIN_AVANCE),
            'show_on_payslip': avance.show_on_payslip,
            'category_id': avance.is_retained and self._get_category('INTERET') or self._get_category('AVANCE'),
            'condition_select': 'none',
            'amount_select': 'flexible_percentage',
            'quantity': '1',
            'rate_val': str(avance.rate_salariale),
            'base_val': 'avance(payslip, "' + avance.code + '", ' + str(is_interest) + ' , categories, inputs)',
            'analytic_account_id':  avance.analytic_account_id and avance.analytic_account_id.id or False,
            'account_tax_id':  avance.account_tax_id and avance.account_tax_id.id or False,
            'account_debit':  avance.account_debit and avance.account_debit.id or False,
            'account_credit':  avance.account_credit and avance.account_credit.id or False,
            'auto': True,
            'avance_id': avance.id,
        }
        rule_salariale_plafond_id_data = {}
        rule_patronale_id_data = {}
        rule_patronale_plafond_id_data = {}
        return rule_parent_id_data, rule_salariale_id_data, rule_salariale_plafond_id_data, rule_patronale_id_data, rule_patronale_plafond_id_data

    @api.multi
    def _get_avantage_dicts(self, avantage):
        min_avantage = avantage.search([], order='sequence asc', limit=1)
        min_sequence = min_avantage and min_avantage.sequence or 0
        rule_parent_id_data = {
            'name': avantage.name,
            'code': avantage.code + PARENT,
            'sequence': self._get_min(MIN_AVANTAGE),
            'parent_rule_id': self._get_rule('SALAIRES'),
            'category_id': self._get_category('AUTRES_TOTAUX'),
            'show_on_payslip': 'never',
            'auto': True,
            'avantage_id': avantage.id,
        }
        rule_salariale_id_data = {
            'name': avantage.name,
            'code': avantage.code,
            'sequence': self._get_min(MIN_AVANTAGE) + avantage.sequence - min_sequence + 1,
            'show_on_payslip': avantage.show_on_payslip,
            'category_id': avantage.type == 'nature' and self._get_category('NATURE') or self._get_category('ARGENT'),
            'condition_select': 'none',
            'amount_select': 'flexible_percentage',
            'quantity': '1',
            'rate_val': str(avantage.rate_salariale),
            'base_val': 'avantage(payslip, "' + avantage.code + '")',
            'analytic_account_id': avantage.analytic_account_id and avantage.analytic_account_id.id or False,
            'account_tax_id': avantage.account_tax_id and avantage.account_tax_id.id or False,
            'account_debit': avantage.account_debit and avantage.account_debit.id or False,
            'account_credit': avantage.account_credit and avantage.account_credit.id or False,
            'auto': True,
            'avantage_id': avantage.id,
        }
        rule_salariale_plafond_id_data = {}
        rule_patronale_id_data = {}
        rule_patronale_plafond_id_data = {}
        return rule_parent_id_data, rule_salariale_id_data, rule_salariale_plafond_id_data, rule_patronale_id_data, rule_patronale_plafond_id_data

    @api.multi
    def _get_cotisation_dicts(self, cotisation):
        min_cotisation = cotisation.search([], order='sequence asc', limit=1)
        min_sequence = min_cotisation and min_cotisation.sequence or 0
        rule_parent_id_data = {
            'name': cotisation.name,
            'code': cotisation.code + PARENT,
            'sequence': self._get_min(MIN_COTISATION),
            'category_id': self._get_category('AUTRES_TOTAUX'),
            'show_on_payslip': 'never',
            'auto': True,
            'cotisation_id': cotisation.id,
        }
        rule_salariale_id_data = {
            'name': cotisation.name,
            'code': cotisation.code + SALARIALE,
            'sequence': self._get_min(MIN_COTISATION) + cotisation.sequence - min_sequence + 1,
            'show_on_payslip': cotisation.show_on_payslip,
            'category_id': self._get_category('COTISATION_SALARIALE'),
            'condition_select': cotisation.plafond_salariale > 0 and 'python' or 'none',
            'condition_python': 'result = categories.BRUT_IMPOSABLE < ' + str(cotisation.plafond_salariale),
            'amount_select': 'flexible_percentage',
            'quantity': '1',
            'rate_val': cotisation.rate_salariale > 0 and str(cotisation.rate_salariale) or '0',
            'base_val': cotisation.rate_salariale > 0 and 'categories.BRUT_IMPOSABLE' or '0',
            'register_id': cotisation.contribution_id and cotisation.contribution_id.id or False,
            'analytic_account_id': cotisation.analytic_account_id and cotisation.analytic_account_id.id or False,
            'account_tax_id': cotisation.account_tax_id and cotisation.account_tax_id.id or False,
            'account_debit': cotisation.account_debit and cotisation.account_debit.id or False,
            'account_credit': cotisation.account_credit and cotisation.account_credit.id or False,
            'auto': True,
            'cotisation_id': cotisation.id,
        }
        rule_salariale_plafond_id_data = {
            'name': cotisation.name,
            'code': cotisation.code + SALARIALE_PLAFOND,
            'sequence': self._get_min(MIN_COTISATION) + cotisation.sequence - min_sequence + 1,
            'show_on_payslip': cotisation.show_on_payslip,
            'category_id': self._get_category('COTISATION_SALARIALE'),
            'condition_select': 'python',
            'condition_python': 'result = categories.BRUT_IMPOSABLE >= ' + str(cotisation.plafond_salariale),
            'amount_select': 'flexible_percentage',
            'quantity': '1',
            'rate_val': cotisation.rate_salariale > 0 and cotisation.plafond_salariale > 0 and str(cotisation.rate_salariale) or '0',
            'base_val': cotisation.rate_salariale > 0 and cotisation.plafond_salariale > 0 and str(cotisation.plafond_salariale) or '0',
            'register_id': cotisation.contribution_id and cotisation.contribution_id.id or False,
            'analytic_account_id': cotisation.analytic_account_id and cotisation.analytic_account_id.id or False,
            'account_tax_id': cotisation.account_tax_id and cotisation.account_tax_id.id or False,
            'account_debit': cotisation.account_debit and cotisation.account_debit.id or False,
            'account_credit': cotisation.account_credit and cotisation.account_credit.id or False,
            'auto': True,
            'cotisation_id': cotisation.id,
        }
        rule_patronale_id_data = {
            'name': cotisation.name,
            'code': cotisation.code + PATRONALE,
            'sequence': self._get_min(MIN_COTISATION) + cotisation.sequence - min_sequence + 1,
            'show_on_payslip': cotisation.show_on_payslip,
            'category_id': self._get_category('COTISATION_PATRONALE'),
            'condition_select': cotisation.plafond_patronale > 0 and 'python' or 'none',
            'condition_python': 'result = categories.BRUT_IMPOSABLE < ' + str(cotisation.plafond_patronale),
            'amount_select': 'flexible_percentage',
            'quantity': '1',
            'rate_val':  cotisation.rate_patronale > 0 and str(cotisation.rate_patronale) or '0',
            'base_val': cotisation.rate_patronale > 0 and 'categories.BRUT_IMPOSABLE' or '0',
            'register_id': cotisation.contribution_id and cotisation.contribution_id.id or False,
            'analytic_account_id': cotisation.analytic_account_id and cotisation.analytic_account_id.id or False,
            'account_tax_id': cotisation.account_tax_id and cotisation.account_tax_id.id or False,
            'account_debit': cotisation.account_debit and cotisation.account_debit.id or False,
            'account_credit': cotisation.account_credit and cotisation.account_credit.id or False,
            'auto': True,
            'cotisation_id': cotisation.id,
        }
        rule_patronale_plafond_id_data = {
            'name': cotisation.name,
            'code': cotisation.code + PATRONALE_PLAFOND,
            'sequence': self._get_min(MIN_COTISATION) + cotisation.sequence - min_sequence + 1,
            'show_on_payslip': cotisation.show_on_payslip,
            'category_id': self._get_category('COTISATION_PATRONALE'),
            'condition_select': 'python',
            'condition_python': 'result = categories.BRUT_IMPOSABLE >= ' + str(cotisation.plafond_patronale),
            'amount_select': 'flexible_percentage',
            'quantity': '1',
            'rate_val':  cotisation.rate_patronale > 0 and cotisation.plafond_patronale > 0 and str(cotisation.rate_patronale) or '0',
            'base_val': cotisation.rate_patronale > 0 and cotisation.plafond_patronale > 0 and str(cotisation.plafond_patronale) or '0',
            'register_id': cotisation.contribution_id and cotisation.contribution_id.id or False,
            'analytic_account_id': cotisation.analytic_account_id and cotisation.analytic_account_id.id or False,
            'account_tax_id': cotisation.account_tax_id and cotisation.account_tax_id.id or False,
            'account_debit': cotisation.account_debit and cotisation.account_debit.id or False,
            'account_credit': cotisation.account_credit and cotisation.account_credit.id or False,
            'auto': True,
            'cotisation_id': cotisation.id,
        }
        return rule_parent_id_data, rule_salariale_id_data, rule_salariale_plafond_id_data, rule_patronale_id_data, rule_patronale_plafond_id_data

    @api.multi
    def _get_rubrique_dicts(self, rubrique):
        min_rubrique = rubrique.search([], order='sequence asc', limit=1)
        min_sequence = min_rubrique and min_rubrique.sequence or 0
        rule_parent_id_data = {
            'name': rubrique.name,
            'code': rubrique.code + PARENT,
            'sequence': self._get_min(MIN_RUBRIQUE),
            'parent_rule_id': self._get_rule('SALAIRES'),
            'category_id': self._get_category('AUTRES_TOTAUX'),
            'show_on_payslip': 'never',
            'auto': True,
            'rubrique_id': rubrique.id,
        }
        is_plafonne = False
        if rubrique.plafond_salariale_type in ['fix', 'rate'] and rubrique.plafond_salariale > 0 or rubrique.plafond_salariale_type in ['code']:
            is_plafonne = True
        compute_code = '0'
        if rubrique.auto_compute:
            compute_code = self._clean_python_code(rubrique.compute_code)
        # Rubrique  totalement exonorée
        rule_salariale_id_data = not is_plafonne and rubrique.rate_salariale > 0  and {
            'name': rubrique.name,
            'code': rubrique.code + EXONORE,
            'sequence': self._get_min(MIN_RUBRIQUE) + rubrique.sequence - min_sequence + 1,
            'show_on_payslip': rubrique.show_on_payslip,
            'category_id': self._get_category('EXONORE'),
            'condition_select': 'none',
            'amount_select': 'code',
            'quantity': '1',
            #'rate_val': str(rubrique.rate_salariale),
            #'base_val': 'rubrique(payslip, "' + rubrique.code + '")',
            'amount_python_compute' : (rubrique.auto_compute and compute_code or ('value = rubrique(payslip, "' + rubrique.code + '")')) + '\nresult = value',
            'register_id': rubrique.contribution_id and rubrique.contribution_id.id or False,
            'analytic_account_id': rubrique.analytic_account_id and rubrique.analytic_account_id.id or False,
            'account_tax_id': rubrique.account_tax_id and rubrique.account_tax_id.id or False,
            'account_debit': rubrique.account_debit and rubrique.account_debit.id or False,
            'account_credit': rubrique.account_credit and rubrique.account_credit.id or False,
            'auto': True,
            'rubrique_id': rubrique.id,
        } or {}
        # Rubrique exonore plafonnee sans reste
        plafond_condition = '999999'
        if rubrique.plafond_salariale_type == 'fix':
            plafond_condition = 'plafond = ' + str(rubrique.plafond_salariale)
        if rubrique.plafond_salariale_type == 'rate':
            plafond_condition = 'plafond = (' + str(rubrique.plafond_salariale) + '/100.0 * categories.BASE_SALARIALE)'
        if rubrique.plafond_salariale_type == 'code':
            plafond_condition = self._clean_python_code(rubrique.code_python)

        rule_salariale_plafond_id_data = rubrique.rate_salariale > 0 and is_plafonne and {
            'name': rubrique.name,
            'code': rubrique.code + EXONORE_SANS_RESTE,
            'sequence': self._get_min(MIN_RUBRIQUE) + rubrique.sequence - min_sequence + 1,
            'show_on_payslip': rubrique.show_on_payslip,
            'category_id': self._get_category('EXONORE'),
            'condition_select': 'none',
            'condition_python': '',
            'amount_select': 'flexible_percentage',
            # 'quantity': '1',
            # 'rate_val': str(rubrique.rate_salariale),
            # 'base_val': 'rubrique(payslip, "' + rubrique.code + '") >= ' + plafond_condition + ' and ' + plafond_condition + ' or rubrique(payslip, "' + rubrique.code + '")',
            'amount_select': 'code',
            #'amount_python_compute' : 'total = rubrique(payslip, "' + rubrique.code + '")\nresult = (total >= '+ plafond_condition+ ') and ('+ plafond_condition+') or total',
            'amount_python_compute' : (rubrique.auto_compute and compute_code or ('value = rubrique(payslip, "' + rubrique.code + '")')) + '\n' + plafond_condition + '\nresult = value > plafond and plafond or value',
            'register_id': rubrique.contribution_id and rubrique.contribution_id.id or False,
            'analytic_account_id': rubrique.analytic_account_id and rubrique.analytic_account_id.id or False,
            'account_tax_id': rubrique.account_tax_id and rubrique.account_tax_id.id or False,
            'account_debit': rubrique.account_debit and rubrique.account_debit.id or False,
            'account_credit': rubrique.account_credit and rubrique.account_credit.id or False,
            'auto': True,
            'rubrique_id': rubrique.id,
        } or {}
        # Rubrique exonore non plafonnees avec le reste
        rule_patronale_id_data = rubrique.rate_salariale > 0 and is_plafonne and {
            'name': rubrique.name,
            'code': rubrique.code + RESTE_TAXABLE,
            'sequence': self._get_min(MIN_RUBRIQUE) + rubrique.sequence - min_sequence + 1,
            'show_on_payslip': rubrique.show_on_payslip,
            'category_id': self._get_category('TAXABLE'),
            'condition_select': 'none',
            # 'amount_select': 'flexible_percentage',
            # 'quantity': '1',
            # 'rate_val':  str(rubrique.rate_salariale),
            # 'base_val': 'rubrique(payslip, "' + rubrique.code + '") >= ' + plafond_condition + ' and (rubrique(payslip, "' + rubrique.code + '") - ' + plafond_condition + ') or 0 ',
            'amount_select': 'code',
            #'amount_python_compute' : 'total = rubrique(payslip, "' + rubrique.code + '")\nresult = (total >= '+ plafond_condition+ ') and (total - '+ plafond_condition+') or 0',
            'amount_python_compute' : (rubrique.auto_compute and compute_code or ('value = rubrique(payslip, "' + rubrique.code + '")')) + '\n' + plafond_condition + '\nresult = value > plafond and (value - plafond) or 0',
            'register_id': rubrique.contribution_id and rubrique.contribution_id.id or False,
            'analytic_account_id': rubrique.analytic_account_id and rubrique.analytic_account_id.id or False,
            'account_tax_id': rubrique.account_tax_id and rubrique.account_tax_id.id or False,
            'account_debit': rubrique.account_debit and rubrique.account_debit.id or False,
            'account_credit': rubrique.account_credit and rubrique.account_credit.id or False,
            'auto': True,
            'rubrique_id': rubrique.id,
        } or {}
        # Rubrique taxable (aucun plafond)
        rule_patronale_plafond_id_data = rubrique.rate_patronale > 0 and {
            'name': rubrique.name,
            'code': rubrique.code + TAXABLE,
            'sequence': self._get_min(MIN_RUBRIQUE) + rubrique.sequence - min_sequence + 1,
            'show_on_payslip': rubrique.show_on_payslip,
            'category_id': self._get_category('TAXABLE'),
            'condition_select': 'none',
            'amount_select': 'flexible_percentage',
            'amount_select': 'code',
            'quantity': '1',
            #'rate_val': str(rubrique.rate_salariale),
            #'base_val': 'rubrique(payslip, "' + rubrique.code + '")',
            'amount_python_compute' : (rubrique.auto_compute and compute_code or ('value = rubrique(payslip, "' + rubrique.code + '")'))+'\nresult = value',
            'register_id': rubrique.contribution_id and rubrique.contribution_id.id or False,
            'analytic_account_id': rubrique.analytic_account_id and rubrique.analytic_account_id.id or False,
            'account_tax_id': rubrique.account_tax_id and rubrique.account_tax_id.id or False,
            'account_debit': rubrique.account_debit and rubrique.account_debit.id or False,
            'account_credit': rubrique.account_credit and rubrique.account_credit.id or False,
            'auto': True,
            'rubrique_id': rubrique.id,
        } or {}
        return rule_parent_id_data, rule_salariale_id_data, rule_salariale_plafond_id_data, rule_patronale_id_data, rule_patronale_plafond_id_data

    # CREATION
    @api.model
    def create(self, vals):
        res = {}
        ok = self.env['ir.config_parameter'].get_param('axe_write', 'False') == 'True'
        if ok:
            if vals.get('holiday_status_id', False):
                holiday_status_id = vals.get('holiday_status_id')
                res = self.create_rules_for_object(
                    holiday_status_id, 'hr.holidays.status', self._get_holidays_dicts)
            elif vals.get('cotisation_id', False):
                cotisation_id = vals.get('cotisation_id')
                res = self.create_rules_for_object(
                    cotisation_id, 'hr.cotisation', self._get_cotisation_dicts)
            elif vals.get('rubrique_id', False):
                rubrique_id = vals.get('rubrique_id')
                res = self.create_rules_for_object(
                    rubrique_id, 'hr.rubrique', self._get_rubrique_dicts)
            elif vals.get('avance_id', False):
                avance_id = vals.get('avance_id')
                res = self.create_rules_for_object(
                    avance_id, 'hr.avance', self._get_avance_dicts)
            elif vals.get('avantage_id', False):
                avantage_id = vals.get('avantage_id')
                res = self.create_rules_for_object(
                    avantage_id, 'hr.avantage', self._get_avantage_dicts)
            # Implement other cases
        vals.update(res)
        return super(hr_axe, self).create(vals)

    @api.multi
    def create_rules_for_object(self, object_id, model, func):
        obj = self.env[model].browse(object_id)
        rule = self.env['hr.salary.rule']
        rule_parent_id_data, rule_salariale_id_data, rule_salariale_plafond_id_data, rule_patronale_id_data, rule_patronale_plafond_id_data = func(
            obj)
        rule_parent_id = False
        rule_salariale_id = False
        rule_salariale_plafond_id = False
        rule_patronale_id = False
        rule_patronale_plafond_id = False
        if rule_parent_id_data:
            rule_parent_id = rule.create(rule_parent_id_data)
            rule_parent_id = rule_parent_id and rule_parent_id.id or False
        custom_parent_rule_id = model == 'hr.cotisation'
        if rule_salariale_id_data:
            rule_salariale_id_data.update(
                {'parent_rule_id': rule_parent_id})
            rule_salariale_id = rule.create(rule_salariale_id_data)
            rule_salariale_id = rule_salariale_id and rule_salariale_id.id or False
        if rule_salariale_plafond_id_data:
            rule_salariale_plafond_id_data.update(
                {'parent_rule_id': rule_parent_id})
            rule_salariale_plafond_id = rule.create(
                rule_salariale_plafond_id_data)
            rule_salariale_plafond_id = rule_salariale_plafond_id and rule_salariale_plafond_id.id or False
        if rule_patronale_id_data:
            rule_patronale_id_data.update(
                {'parent_rule_id': custom_parent_rule_id and rule_salariale_id or rule_parent_id})
            rule_patronale_id = rule.create(
                rule_patronale_id_data)
            rule_patronale_id = rule_patronale_id and rule_patronale_id.id or False
        if rule_patronale_plafond_id_data:
            rule_patronale_plafond_id_data.update(
                {'parent_rule_id': custom_parent_rule_id and rule_salariale_plafond_id or rule_parent_id})
            rule_patronale_plafond_id = rule.create(
                rule_patronale_plafond_id_data)
            rule_patronale_plafond_id = rule_patronale_plafond_id and rule_patronale_plafond_id.id or False
        return {
            'rule_parent_id': rule_parent_id,
            'rule_salariale_id': rule_salariale_id,
            'rule_salariale_plafond_id': rule_salariale_plafond_id,
            'rule_patronale_id': rule_patronale_id,
            'rule_patronale_plafond_id': rule_patronale_plafond_id,
        }

    # UPDATING
    @api.multi
    def write(self, vals):
        res = {}
        ok = self.env['ir.config_parameter'].get_param('axe_write', 'False') == 'True'
        if ok:
            for axe in self:
                if axe.holiday_status_id:
                    res = axe.update_rules_for_object(
                        axe.holiday_status_id.id, 'hr.holidays.status', self._get_holidays_dicts)
                elif axe.cotisation_id:
                    res = axe.update_rules_for_object(
                        axe.cotisation_id.id, 'hr.cotisation', self._get_cotisation_dicts)
                elif axe.rubrique_id:
                    res = axe.update_rules_for_object(
                        axe.rubrique_id.id, 'hr.rubrique', self._get_rubrique_dicts)
                elif axe.avance_id:
                    res = axe.update_rules_for_object(
                        axe.avance_id.id, 'hr.avance', self._get_avance_dicts)
                elif axe.avantage_id:
                    res = axe.update_rules_for_object(
                        axe.avantage_id.id, 'hr.avantage', self._get_avantage_dicts)
            # implement other case
        vals.update(res)
        return super(hr_axe, self).write(vals)

    @api.multi
    def update_rules_for_object(self, object_id, model, func):
        self.ensure_one()
        self._clean()
        obj = self.env[model].browse(object_id)
        rule_parent_id_data, rule_salariale_id_data, rule_salariale_plafond_id_data, rule_patronale_id_data, rule_patronale_plafond_id_data = func(
            obj)
        res = {}
        rule_parent_id = self.rule_parent_id and self.rule_parent_id.id or False
        rule_salariale_id = False
        rule_salariale_plafond_id = False
        rule_patronale_id = False
        rule_patronale_plafond_id = False
        custom_parent_rule_id = model == 'hr.cotisation'
        if rule_parent_id_data:
            if self.rule_parent_id:
                self.rule_parent_id.write(rule_parent_id_data)
            else:
                rule_parent_id = self.rule_parent_id.create(
                    rule_parent_id_data)
        if rule_salariale_id_data:
            rule_salariale_id_data.update(
                {'parent_rule_id': rule_parent_id})
            if self.rule_salariale_id:
                self.rule_salariale_id.write(rule_salariale_id_data)
            else:
                rule_salariale_id = self.rule_salariale_id.create(
                    rule_salariale_id_data)
                res.update({'rule_salariale_id': rule_salariale_id.id})
        if rule_salariale_plafond_id_data:
            rule_salariale_plafond_id_data.update(
                {'parent_rule_id': rule_parent_id})
            if self.rule_salariale_plafond_id:
                self.rule_salariale_plafond_id.write(
                    rule_salariale_plafond_id_data)
            else:
                rule_salariale_plafond_id = self.rule_salariale_plafond_id.create(
                    rule_salariale_plafond_id_data)
                res.update(
                    {'rule_salariale_plafond_id': rule_salariale_plafond_id.id})
        if rule_patronale_id_data:
            rule_patronale_id_data.update(
                {'parent_rule_id': custom_parent_rule_id and self.rule_salariale_id.id or rule_parent_id})
            if self.rule_patronale_id:
                self.rule_patronale_id.write(rule_patronale_id_data)
            else:
                rule_patronale_id = self.rule_patronale_id.create(
                    rule_patronale_id_data)
                res.update({'rule_patronale_id': rule_patronale_id.id})
        if rule_patronale_plafond_id_data:
            rule_patronale_plafond_id_data.update(
                {'parent_rule_id': custom_parent_rule_id and self.rule_salariale_plafond_id.id or rule_parent_id})
            if self.rule_patronale_plafond_id:
                self.rule_patronale_plafond_id.write(
                    rule_patronale_plafond_id_data)
            else:
                rule_patronale_plafond_id = self.rule_patronale_plafond_id.create(
                    rule_patronale_plafond_id_data)
                res.update(
                    {'rule_patronale_plafond_id': rule_patronale_plafond_id.id})
        return res

    # UNLINK
    @api.multi
    def unlink(self):
        ok = self.env['ir.config_parameter'].get_param('axe_unlink', 'False') == 'True'
        for axe in self:
            if ok and axe.rule_patronale_plafond_id:
                axe.rule_patronale_id.child_ids.unlink()
                axe.rule_patronale_id.unlink()
            if ok and axe.rule_patronale_id:
                axe.rule_patronale_plafond_id.child_ids.unlink()
                axe.rule_patronale_plafond_id.unlink()
            if ok and axe.rule_salariale_plafond_id:
                axe.rule_salariale_plafond_id.child_ids.unlink()
                axe.rule_salariale_plafond_id.unlink()
            if ok and axe.rule_salariale_id:
                axe.rule_salariale_id.child_ids.unlink()
                axe.rule_salariale_id.unlink()
            if ok and axe.rule_parent_id:
                axe.rule_parent_id.child_ids.unlink()
                axe.rule_parent_id.unlink()
        return super(hr_axe, self).unlink()
