# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
import datetime


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _compute_contract_id(self):
        """ get the lastest contract """
        Contract = self.env['hr.contract']
        for employee in self:
            employee.contract_id = Contract.search([('employee_id', '=', employee.id), ('state', 'in', ['open','pending'])], order='date_start desc', limit=1)

    matricule = fields.Char('Matricule', copy=False)
    cin = fields.Char('CIN', copy=False)
    prenom = fields.Char(u'Prénom')
    date = fields.Date(string=u"Date d'embauche", default=fields.Date.today,
                       help=u"Cette date est requise pour le calcul de la prime d'ancienneté")
    anciennete = fields.Boolean(string=u"Prime d'ancienneté?", default=True,
                                help=u"Est ce que cet employé bénificie de la prime d'ancienneté")
    mode_reglement = fields.Selection(selection=(('virement', 'Virement'),
                                                 ('cheque', u'Chèque'),
                                                 ('espece', u'Espèce')),
                                      string=u'Mode de règlement', default='virement')
    agence = fields.Char(string=u'Agence')
    bank = fields.Many2one('res.bank', string='Banque Marocaine')
    compte = fields.Char(string=u'Compte bancaire')
    chargefam = fields.Integer(string=u'Nombre de personnes à charge', default=0)
    logement = fields.Float('Abattement Fr Logement', default=0.0)
    type_logement = fields.Selection(selection=(('normal', 'Normal'),
                                                ('social', 'Social')), default='normal', string='Type logement')
    superficie_logement = fields.Float(string=u'Superficie(m²)')
    prix_acquisition_logement = fields.Float(string=u"Prix d'acquisition")
    affilie = fields.Boolean(string=u'Affilié', default=True,
                             help=u'Est ce qu on va calculer les cotisations pour cet employé')
    address_home = fields.Char(string=u'Adresse Personnelle')
    address = fields.Char(string=u'Adresse Professionnelle')
    phone_home = fields.Char(string=u'Téléphone Personnel')
    ssnid = fields.Char(string='CNSS', copy=False)
    payslip_count = fields.Integer(compute='get_payslip_count')
    #anciennete
    annees_anciennete = fields.Float(string=u'Ancienneté', compute='calc_seniority')
    taux_anciennete = fields.Float(string=u'Taux ancienneté(%)', compute='calc_seniority')

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if name:
            domain = ['|','|',('matricule', operator, name),('name',operator,name),('prenom',operator,name)] + (args or [])
            return self.search(domain, limit=limit).name_get()
        return super(HrEmployee, self).name_search(name, args, operator, limit=limit)

    @api.multi
    @api.onchange('bank_account_id')
    def onchange_bank_account_id(self):
        for rec in self:
            if rec.bank_account_id:
                rec.bank = rec.bank_account_id.bank_id
                rec.compte = rec.bank_account_id.acc_number

    @api.multi
    @api.depends('date')
    def calc_seniority(self):
        for rec in self:
            if rec.date:
                date_embauche = str(rec.date).split('-')
                seniority_date = datetime.date(int(date_embauche[0]), int(date_embauche[1]), int(date_embauche[2]))
                today = datetime.date.today()
                years = today.year - seniority_date.year
                if today.month < seniority_date.month or (today.month == seniority_date.month and today.day < seniority_date.day):
                    years -= 1
                rec.annees_anciennete = years

                objet_anciennete = self.env['hr.payroll_ma.anciennete']
                liste = objet_anciennete.sudo().search([])
                for tranche in liste:
                    if(years >= tranche.debuttranche) and (years < tranche.fintranche):
                        rec.taux_anciennete = tranche.taux
                        break

    def get_parametre(self):
        params = self.env['hr.payroll_ma.parametres']
        return params.search([], limit=1)
    # Contrainte sur logement social
    @api.one
    @api.constrains('superficie_logement', 'prix_acquisition_logement', 'type_logement')
    def _check_param_logement_social(self):
        if self.type_logement == 'social':

            dictionnaire = self.get_parametre()
            # On vérifie la superficie
            if self.superficie_logement > dictionnaire['superficie_max_logement_social']:
                raise ValidationError(u"La superficie indiquée n'est pas conforme aux normes du logement social")
            # On vérifie le prix d'acquisition
            if self.prix_acquisition_logement > dictionnaire['prix_achat_max_logement_social']:
                raise ValidationError(u"Le prix d'acquisition n'est pas conforme aux normes du logement social")

    # contrainte sur le RIB
    @api.one
    @api.constrains('compte')
    def _check_rib(self):
        if self.mode_reglement == 'virement':
            compte = self.compte.replace(' ', '')
            if len(compte) != 24 or not compte.isdigit():
                raise ValidationError(u"Le RIB doit être constitué de 24 chiffres")

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            if rec.prenom:
                result.append((rec.id, rec.name + ' ' + rec.prenom))
            else:
                result.append((rec.id, rec.name))
        return result

    @api.multi
    def get_payslip_count(self):
        for rec in self:
            count = len(self.env['hr.payroll_ma.bulletin'].sudo().search([('employee_id', '=', rec.id)]))
            rec.payslip_count = count


class HrContract(models.Model):
    _inherit = "hr.contract"

    working_days_per_month = fields.Integer(string=u'Jours travaillés par mois',default=26)
    hour_salary = fields.Float(u'Salaire Horaire')
    monthly_hour_number = fields.Float(u'Nombre Heures par mois')
    ir = fields.Boolean(u'IR?')
    cotisation = fields.Many2one('hr.payroll_ma.cotisation.type', string=u'Type cotisation', required=True)
    rubrique_ids = fields.One2many('hr.payroll_ma.ligne_rubrique', 'id_contract', string='Rubriques')
    actif = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id,
                                 string='Société', readonly=True, copy=False)

    @api.one
    @api.constrains('actif','state')
    def _check_unicite_contrat(self):
        contrat_ids = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id),
                                                      ('actif', '=', True),
                                                      ('state', 'in', ['open','pending'])])
        if len(contrat_ids) > 1:
            raise ValidationError(u'Plusieurs contrats actifs pour cet employé!')

    @api.multi
    def cloturer_contrat(self):
        for rec in self:
            rec.actif = False
            rec.date_end = fields.Date.context_today(self)

    @api.multi
    def activer_contrat(self):
        for rec in self:
            rec.actif = True
            rec.date_end = None

    @api.multi
    def net_to_brute(self):
        for rec in self:
            salaire_base = rec.wage
            cotisation = rec.cotisation
            personnes = rec.employee_id.chargefam
            params = self.env['hr.payroll_ma.parametres']
            objet_ir = self.env['hr.payroll_ma.ir']

            liste = objet_ir.search([])
            dictionnaire = rec.employee_id.get_parametre()
            abattement = personnes * dictionnaire.charge

            base = 0
            salaire_brute = salaire_base
            trouve=False
            trouve2=False
            while(trouve == False):
                salaire_net_imposable=0
                cotisations_employee=0
                for cot in cotisation.cotisation_ids :
                    if cot.plafonee and salaire_brute >= cot.plafond:
                        base = cot.plafond
                    else : base = salaire_brute

                    cotisations_employee += base * cot.tauxsalarial / 100
                fraispro = salaire_brute * dictionnaire.fraispro / 100
                if fraispro < dictionnaire.plafond:
                    salaire_net_imposable = salaire_brute - fraispro - cotisations_employee
                else :
                    salaire_net_imposable = salaire_brute - dictionnaire.plafond - cotisations_employee
                for tranche in liste:
                    if(salaire_net_imposable >= tranche.debuttranche/12) and (salaire_net_imposable < tranche.fintranche/12):
                        taux = (tranche.taux)
                        somme = (tranche.somme/12)

                ir = (salaire_net_imposable * taux / 100) - somme - abattement
                if(ir < 0):ir = 0
                salaire_net=salaire_brute - cotisations_employee - ir
                if(int(salaire_net)==int(salaire_base) and trouve2==False):
                    trouve2=True
                    salaire_brute-=1
                if(round(salaire_net,2)==salaire_base):trouve=True
                elif trouve2==False : salaire_brute+=0.5
                elif trouve2==True : salaire_brute+=0.01

            rec.wage = round(salaire_brute,2)
            return True


class HRHolidaysStatus(models.Model):
    _inherit = "hr.holidays.status"

    payed = fields.Boolean(string=u'Payé', default=True)
