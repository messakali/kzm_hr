# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


# Classe : Paramètres de la paie
class HrPayrollMaParametres(models.Model):
    _name = 'hr.payroll_ma.parametres'
    _description = 'Parametres'

    arrondi = fields.Boolean("Arrondi", default=True)
    charge = fields.Float(string="Charges familiales", help="Les charges de famille déduites de IR")
    fraispro = fields.Float(string="Frais Professionnels")
    plafond = fields.Float(string="Plafond")
    credit_account_id = fields.Many2one('account.account', string=u'Compte de crédit IR')
    journal_id = fields.Many2one('account.journal', string=u'Journal')
    salary_credit_account_id = fields.Many2one('account.account', string=u'Compte de crédit')
    salary_debit_account_id = fields.Many2one('account.account', string=u'Compte de débit')
#   analytic_account_id = fields.Many2one('account.analytic.account', string='Compte analytique')
    salaire_max_logement_social = fields.Float("Salaire max", default=3000)
    superficie_max_logement_social = fields.Float(u"Superficie max (m²)", default=80)
    prix_achat_max_logement_social = fields.Float("Prix d'achat max", default=300000)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id,
                                 string='Société', readonly=True, copy=False)


# Classe : IR
class HrIr(models.Model):
    _name = 'hr.payroll_ma.ir'
    _description = 'IR'

    debuttranche = fields.Float(string=u"Début de Tranche")
    fintranche = fields.Float(string="Fin de tranche")
    taux = fields.Float(string="Taux")
    somme = fields.Float(string=u"Somme à déduire")


# Classe : Ancienneté
class HrAnciennete(models.Model):
    _name = 'hr.payroll_ma.anciennete'
    _description = "Tranches de la prime d'anciennete"

    debuttranche = fields.Float(string=u"Début Tranche")
    fintranche = fields.Float(string=u"Fin Tranche")
    taux = fields.Float(string=u"Taux")


# Classe : Cotisation
class HrCotisation(models.Model):
    _name = 'hr.payroll_ma.cotisation'
    _description = 'Cotisations'

    code = fields.Char(string="Code")
    name = fields.Char(string="Designation")
    tauxsalarial = fields.Float(string="Taux Salarial")
    tauxpatronal = fields.Float(string="Taux Patronal")
    plafonee = fields.Boolean(string=u'Cotisation plafonée')
    plafond = fields.Float(string=u"Plafond")
    credit_account_id = fields.Many2one('account.account', string=u'Compte de crédit')
    debit_account_id = fields.Many2one('account.account', string=u'Compte de débit')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id,
                                 string='Société', readonly=True, copy=False)


# Classe: Types de cotisations
class HrCotisationType(models.Model):
    _name = 'hr.payroll_ma.cotisation.type'
    _description = 'Types de cotisation'

    name = fields.Char(string=u"Désignation", required=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id,
                                 string='Société', readonly=True, copy=False)
    cotisation_ids = fields.Many2many('hr.payroll_ma.cotisation', 'salary_cotisation',
                                      'cotisation_id', 'cotisation_type_id', string='Cotisations', copy=False)


class HrRubriqueSettings(models.TransientModel):
    _name = 'hr.rubriques.settings'

    @api.model
    def _has_default_company(self):
        count = self.env['res.company'].search_count([])
        return bool(count == 1)

    company_id = fields.Many2one('res.company', string='Société', required=True)
    has_default_company = fields.Boolean(readonly=True,
                                         default=lambda self: self._has_default_company())
    has_rubriques = fields.Boolean(string='Has rubriques')
    has_cotisation = fields.Boolean(string='Has cotisation')
    has_chart_of_accounts = fields.Boolean(string='Company has a chart of accounts')
    chart_template_id = fields.Many2one('account.chart.template', string='Template',
                                        domain="[('visible','=', True)]")
    has_parametre = fields.Boolean(string='Has parametres')
    has_journal = fields.Boolean(string='Has journal')

    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.company_id:
            company = self.company_id
            self.chart_template_id = company.chart_template_id
            self.has_chart_of_accounts = len(company.chart_template_id) > 0 or False
            count_rubrique = self.env['hr.payroll_ma.rubrique'].search_count([('company_id', '=', company.id)])
            count_cotisation = self.env['hr.payroll_ma.cotisation'].search_count([('company_id', '=', company.id)])
            count_parametre = self.env['hr.payroll_ma.parametres'].search_count([('company_id', '=', company.id)])
            count_journal = self.env['account.journal'].search_count([('company_id', '=', company.id), ('code', '=', 'Paie')])
            if count_rubrique > 0:
                self.has_rubriques = True
            else:
                self.has_rubriques = False

            if count_cotisation > 0:
                self.has_cotisation = True
            else:
                self.has_cotisation = False

            if count_parametre > 0:
                self.has_parametre = True
            else:
                self.has_parametre = False

            if count_journal > 0:
                self.has_journal = True
            else:
                self.has_journal = False

    @api.multi
    def get_account(self, code, company_id):
        if self.company_id and code:
            return self.env['account.account'].search([('code', 'like', code),
                                                       ('company_id', '=', company_id.id)], limit=1).id

    @api.multi
    def prepare_data_rubrique(self, rubrique, sequence):
        if rubrique:
            credit_code = rubrique.credit_account_id.code
            debit_code = rubrique.debit_account_id.code
            if credit_code:
                credit_code = credit_code[:4]
            if debit_code:
                debit_code = debit_code[:4]
            return {
                'name': rubrique.name,
                'categorie': rubrique.categorie,
                'sequence': sequence,
                'type': rubrique.type,
                'plafond': rubrique.plafond,
                'imposable': rubrique.imposable,
                'ir': rubrique.ir,
                'anciennete': rubrique.anciennete,
                'absence': rubrique.absence,
                'note': rubrique.note,
                'credit_account_id': self.get_account(credit_code, self.company_id),
                'debit_account_id': self.get_account(debit_code, self.company_id),
                'heures_sup': rubrique.heures_sup,
                'company_id': self.company_id.id,
                }

    @api.multi
    def create_rubrique(self):
        i = 1
        if self.has_rubriques :
            raise UserError('Les rubriques de cette société ont été déjâ générés')
        if not self.has_chart_of_accounts:
            raise UserError("Veuillez d'abord configurer le plan comptable de cette société")
        while i < 25:
            vals = {}
            model = 'hr_payroll_ma.rubrique'+str(i)
            model = str(model)
            rubrique_id = self.env.ref(model)
            if rubrique_id:
                rubrique_id = rubrique_id.id
                rubrique = self.env['hr.payroll_ma.rubrique'].sudo().browse(rubrique_id)
                vals = self.prepare_data_rubrique(rubrique, i)
                if vals:
                    self.env['hr.payroll_ma.rubrique'].create(vals)
                i += 1
        hsup_25 = self.env['hr.payroll_ma.rubrique'].sudo().browse(self.env.ref('kzm_payroll_ma.hsup_25').id)
        hsup_50 = self.env['hr.payroll_ma.rubrique'].sudo().browse(self.env.ref('kzm_payroll_ma.hsup_50').id)
        hsup_100 = self.env['hr.payroll_ma.rubrique'].sudo().browse(self.env.ref('kzm_payroll_ma.hsup_100').id)
        jrs_chomes_payes = self.env['hr.payroll_ma.rubrique'].sudo().browse(self.env.ref('kzm_payroll_ma.jrs_chomes_payes').id)
        jrs_conges_payes = self.env['hr.payroll_ma.rubrique'].sudo().browse(self.env.ref('kzm_payroll_ma.jrs_conges_payes').id)
        if self.prepare_data_rubrique(hsup_25, 25):
            self.env['hr.payroll_ma.rubrique'].create(self.prepare_data_rubrique(hsup_25, 25))
        if self.prepare_data_rubrique(hsup_50, 26):
            self.env['hr.payroll_ma.rubrique'].create(self.prepare_data_rubrique(hsup_50, 26))
        if self.prepare_data_rubrique(hsup_100, 27):
            self.env['hr.payroll_ma.rubrique'].create(self.prepare_data_rubrique(hsup_100, 27))
        if self.prepare_data_rubrique(jrs_chomes_payes,28):
            self.env['hr.payroll_ma.rubrique'].create(self.prepare_data_rubrique(jrs_chomes_payes, 28))
        if self.prepare_data_rubrique(jrs_conges_payes, 29):
            self.env['hr.payroll_ma.rubrique'].create(self.prepare_data_rubrique(jrs_conges_payes, 29))
        self.has_rubriques = True
        return True

    @api.multi
    def prepare_data_cotisation(self, cotisation):
        if cotisation:
            return {
                'name': cotisation.name,
                'code': cotisation.code,
                'tauxsalarial': cotisation.tauxsalarial,
                'tauxpatronal': cotisation.tauxpatronal,
                'plafonee': cotisation.plafonee,
                'plafond': cotisation.plafond,
                'company_id': self.company_id.id,
            }

    @api.multi
    def create_cotisation(self):
        i = 1
        if self.has_cotisation:
            raise UserError('Les cotisations de cette société ont été déjâ générés')
        while i < 7:
            vals = {}
            model = 'hr_payroll_ma.cotisation_data' + str(i)
            model = str(model)
            cotisation_id = self.env.ref(model)
            if cotisation_id:
                cotisation = self.env['hr.payroll_ma.cotisation'].sudo().browse(cotisation_id.id)
                vals = self.prepare_data_cotisation(cotisation)
                if vals:
                    self.env['hr.payroll_ma.cotisation'].create(vals)
                i += 1
        return True

    @api.multi
    def create_parametre(self):
        i = 1
        if self.has_parametre:
            raise UserError('Les paramètres  de cette société ont été déjâ générés')
        parametre_id = self.env.ref('kzm_payroll_ma.parametres_data8')
        if parametre_id:
            parametre = self.env['hr.payroll_ma.parametres'].sudo().browse(parametre_id.id)
            vals = {
                'charge': parametre.charge,
                'fraispro': parametre.fraispro,
                'plafond': parametre.plafond,
                'company_id': self.company_id.id,
            }
            param_id = self.env['hr.payroll_ma.parametres'].create(vals)
        return param_id

    @api.multi
    def create_journal(self):
        i = 1
        if self.has_journal:
            raise UserError('Le journal de paie de cette société existe déjâ dans la base')
        jouranl_id = self.env.ref('kzm_payroll_ma.salary_journal')
        if jouranl_id:
            journal = self.env['account.journal'].sudo().browse(jouranl_id.id)
            vals = {
                'name': journal.name,
                'code': journal.code,
                'type': journal.type,
                'company_id': self.company_id.id,
            }
            journal_id = self.env['account.journal'].create(vals)
        return journal_id

    @api.multi
    def generate_data_paie(self):
        self.create_rubrique()
        self.create_cotisation()
        self.create_parametre()
        self.create_journal()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/web',
        }
