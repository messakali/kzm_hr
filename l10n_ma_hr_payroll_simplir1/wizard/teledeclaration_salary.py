# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import base64
import calendar
from datetime import timedelta
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from lxml import etree
from lxml.etree import Element, SubElement
from odoo.exceptions import ValidationError as Warning

CONTRACT_TYPES = ['permanent', 'occasional', 'trainee']


class hr_teledeclaration_salary(models.TransientModel):
    _name = 'hr.teledeclaration.salary'

    fiscalyear_id = fields.Many2one(
        'date.range', string=u'Année', required=False, domain=[('type_id.fiscal_year', '=', True),('type_id.fiscal_year', '=', True),('active', '=', True)])
    period_id = fields.Many2one(
        'date.range', string=u'Période', required=False)
    date_from = fields.Date(string=u'Date début',  required=False)
    date_to = fields.Date(string=u'Date fin',  required=False)

    departments_id = fields.Many2many(
        'hr.department', 'teledeclaration_ir_department_rel', 'declaration_id', 'department_id', string=u'Limiter les départements', )

    state = fields.Selection([
        ('all', 'All'),
        ('done', 'Terminé'),
    ], string=u'État', required=True, default='done')

    company_child = fields.Boolean(string=u'Filiales', default=False,)
    company_parent = fields.Boolean(string=u'Sociétés mères', default=True,)

    is_first_page = fields.Boolean(string=u'Première page', default=True)
    name = fields.Char(string=u'Nom', size=64,)
    generated_file = fields.Binary(string=u'Fichier généré',)

    reference = fields.Char(
        string=u'Declaration reference', size=64, required=True,)

    def _get_periods(self):
        tab = []
        date_from = fields.Datetime.from_string(self.date_from)
        date_to = fields.Datetime.from_string(self.date_to)
        while date_from < date_to:
            month_range = calendar.monthrange(date_from.year, date_from.month)
            if date_from.year == date_to.year and date_from.month == \
                    date_to.month and month_range[1] > date_to.day:
                tab.append((date_from, date_to),)
                break
            dd = date_from.replace(day=date_from.day)
            df = date_from.replace(day=month_range[1])
            tab.append((dd, df),)
            date_from = df + timedelta(days=1)
        return [(fields.Datetime.to_string(x[0]), fields.Datetime.to_string(x[1]))
                for x in tab]

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
        'res.company', string=u'Sociétés',  required=True, )

    @api.onchange('fiscalyear_id')
    def _onchange_fiscalyear_id(self):
        self.period_id = False
        self.date_start = False
        self.date_end = False
        if self.fiscalyear_id:
            period_objs = self.env['date.range'].search(['&', ('date_start', '>=', self.fiscalyear_id.date_start), ('date_start', '<=', self.fiscalyear_id.date_end)])
            self.date_from = self.fiscalyear_id.date_start
            self.date_to = self.fiscalyear_id.date_end
            period_ids = [
                x.id for x in period_objs if x.active == True and x.type_id.fiscal_year == False]
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

    @api.multi
    def action_retour(self):
        self.ensure_one()
        action = self.env.ref(
            'l10n_ma_hr_payroll.hr_teledeclaration_salary_wizard_action').read()[0]
        action['res_id'] = self.id
        self.is_first_page = True
        self._generate_file()
        return action

    @api.multi
    def action_generate(self):
        self = self.with_context({
            'date_start': self.date_from,
            'date_end': self.date_to,
        })
        self.ensure_one()
        action = self.env.ref(
            'l10n_ma_hr_payroll_simplir.hr_teledeclaration_salary_wizard_action').read()[0]
        action['res_id'] = self.id
        self.is_first_page = False
        self._generate_file()
        return action

    @api.multi
    def _get_departments(self):
        if not self.departments_id:
            return False
        department_ids = [x.id for x in self.departments_id]
        department_ids = self.env['hr.department'].search(
            [('id', 'child_of', department_ids)])
        return department_ids.mapped('id')

    @api.multi
    def _get_companies(self):
        return self.company_ids.mapped('id')

    @api.multi
    def _get_payslips(self, contract_type=False):
        payslip_domain = [
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('company_id', 'in', self._get_companies()),
        ]
        if self._get_departments():
            payslip_domain.append(
                ('department_id', 'in', self._get_departments()),)
        if self.state != 'all':
            payslip_domain.append(('state', '=', self.state),)
        if contract_type:
            assert contract_type in CONTRACT_TYPES, _(
                "Contract type sould be in the list")
            payslip_domain.append(
                ('contract_id.type_id.type', '=', contract_type),)
        return self.env['hr.payslip'].search(payslip_domain)

    @api.multi
    def _generate_file(self):
        output = StringIO()
        output.write(self._get_data())
        contents = output.getvalue()
        output.close()
        generated_data = base64.encodestring(contents)
        self.generated_file = generated_data
        self.name = 'TraitementEtSalaire_' + self.date_from[:4] + '.xml'

    @api.multi
    def _check_company_data(self, company):
        if not company.vat:
            raise Warning(
                _('Veuillez spécifier l\'identifiant fiscal pour la société [%s]') % company.name)
        if not company.simpleir_employee_id:
            raise Warning(
                _('Veuillez spécifier le contribuale au service Simpl-IR pour la société [%s]') % company.name)
        if not company.commune_id:
            raise Warning(
                _('Veuillez spécifier la commune pour la société [%s]') % company.name)

    @api.multi
    def _write_node(self, tag, text):
        var = Element(tag)
        if isinstance(text, bool):
            var.text = ''
        elif isinstance(text, (int, float, long, complex)):
            var.text = str(text)
        else:
            var.text = text or ''
        return var

    @api.multi
    def _get_data(self):
        company = self.env['res.company'].get_company_root()
        emp = company.simpleir_employee_id
        self._check_company_data(company)
        NSMAP = {"xsi": "http://www.w3.org/2001/XMLSchema-instance", }
        root = Element("TraitementEtSalaire", nsmap=NSMAP)
        root.append(self._write_node('identifiantFiscal', company.vat))
        root.append(self._write_node('nom', emp.nom))
        root.append(self._write_node('prenom', emp.prenom))
        root.append(self._write_node('raisonSociale', company.name))
        root.append(self._write_node('exerciceFiscalDu', self.date_from))
        root.append(self._write_node('exerciceFiscalAu', self.date_to))
        root.append(self._write_node('annee', self.date_to[:4]))
        commune = Element('commune')
        commune.append(self._write_node('code', company.commune_id.code))
        root.append(commune)
        root.append(
            self._write_node('adresse', company.partner_id.contact_address.strip().replace('\n', ', ')))
        root.append(self._write_node('numeroCIN', emp.cin))
        root.append(self._write_node('numeroCNSS', emp.cnss))
        root.append(self._write_node('numeroCE', emp.carte_sejour))
        root.append(self._write_node('numeroRC', company.company_registry))
        root.append(self._write_node('identifiantTP', company.identifiant_tp))
        root.append(self._write_node('numeroFax', company.fax))
        root.append(self._write_node('numeroTelephone', company.phone))
        root.append(self._write_node('email', company.email))
        root.append(self._write_node('effectifTotal', company.nbr_employees))
        root.append(
            self._write_node('nbrPersoPermanent', company.nbr_employees_permanent))
        root.append(
            self._write_node('nbrPersoOccasionnel', company.nbr_employees_occasional))
        root.append(
            self._write_node('nbrStagiaires', company.nbr_employees_trainees))

        # Brut imposable
        totalMtRevenuBrutImposablePP = self.env['hr.dictionnary'].compute_value(
            code='BRUT_IMPOSABLE',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='p',
            company_id=self._get_companies(),
        )
        root.append(
            self._write_node('totalMtRevenuBrutImposablePP', totalMtRevenuBrutImposablePP))
        # Net imposable
        totalMtRevenuNetImposablePP = self.env['hr.dictionnary'].compute_value(
            code='NET_IMPOSABLE',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='p',
            company_id=self._get_companies(),
        )
        root.append(
            self._write_node('totalMtRevenuNetImposablePP', totalMtRevenuNetImposablePP))
        # Total des deductions
        totalMtTotalDeductionPP = self.env['hr.dictionnary'].compute_value(
            code='TOTAL_DEDUCTION',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='p',
            company_id=self._get_companies(),
        )
        root.append(
            self._write_node('totalMtTotalDeductionPP', totalMtTotalDeductionPP))
        # IR preleve / permanent
        totalMtIrPrelevePP = self.env['hr.dictionnary'].compute_value(
            code='IR',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='p',
            company_id=self._get_companies(),
        )
        root.append(
            self._write_node('totalMtIrPrelevePP', totalMtIrPrelevePP))
        # Brut / occasionnel
        totalMtBrutSommesPO = self.env['hr.dictionnary'].compute_value(
            code='BRUT',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='o',
            company_id=self._get_companies(),
        )
        root.append(
            self._write_node('totalMtBrutSommesPO', totalMtBrutSommesPO))
        # IR preleve Occasionnel
        totalIrPrelevePO = self.env['hr.dictionnary'].compute_value(
            code='IR',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='o',
            company_id=self._get_companies(),
        )
        root.append(
            self._write_node('totalIrPrelevePO', totalIrPrelevePO))
        # Brut traitement salaire STG
        totalMtBrutTraitSalaireSTG = self.env['hr.dictionnary'].compute_value(
            code='SALAIRE_BASE',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='t',
            company_id=self._get_companies(),
        )
        root.append(
            self._write_node('totalMtBrutTraitSalaireSTG', totalMtBrutTraitSalaireSTG))
        # Brut traitement salaire STG
        totalMtBrutIndemnitesSTG = self.env['hr.dictionnary'].compute_value(
            code='INDEMNITE',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='t',
            company_id=self._get_companies(),
        )
        root.append(
            self._write_node('totalMtBrutIndemnitesSTG', totalMtBrutIndemnitesSTG))
        # Total des montants des retenus STG
        totalMtRetenuesSTG = self.env['hr.dictionnary'].compute_value(
            code='RETENU',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='t',
            company_id=self._get_companies(),
        )
        root.append(
            self._write_node('totalMtRetenuesSTG', totalMtRetenuesSTG))
        # Montant revenu net imposable STG
        totalMtRevenuNetImpSTG = self.env['hr.dictionnary'].compute_value(
            code='NET_IMPOSABLE',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='t',
            company_id=self._get_companies(),
        )
        root.append(
            self._write_node('totalMtRevenuNetImpSTG', totalMtRevenuNetImpSTG))
        # Total somme paye RTS
        montantPermanent = self.env['hr.dictionnary'].compute_value(  # A
            code='BRUT',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='p',
            company_id=self._get_companies(),
        )
        montantOccasionnel = self.env['hr.dictionnary'].compute_value(  # B
            code='BRUT',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='o',
            company_id=self._get_companies(),
        )
        montantStagiaire = self.env['hr.dictionnary'].compute_value(  # C
            code='BRUT',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            contract_type='t',
            company_id=self._get_companies(),
        )
        # Total somme paye RTS
        totalSommePayeRTS = montantPermanent + \
            montantOccasionnel + montantStagiaire
        root.append(
            self._write_node('totalSommePayeRTS', totalSommePayeRTS))
        # Montant revenu net imposable STG
        totalmtAnuuelRevenuSalarial = self.env['hr.dictionnary'].compute_value(
            code='SALAIRE_BASE',
            date_start=self.date_from,
            date_stop=self.date_to,
            department_ids=self._get_departments(),
            state=self.state,
            company_id=self._get_companies(),
        )
        root.append(
            self._write_node('totalmtAnuuelRevenuSalarial', totalmtAnuuelRevenuSalarial))
        # Total montant abondement
        totalmtAbondement = 0
        root.append(
            self._write_node('totalmtAbondement', totalmtAbondement))
        # Montant Permanent
        root.append(
            self._write_node('montantPermanent', montantPermanent))
        # Montant Occasionnel
        root.append(
            self._write_node('montantOccasionnel', montantOccasionnel))
        # Montant Stagiaire
        root.append(
            self._write_node('montantStagiaire', montantStagiaire))
        # Reference declaration
        root.append(
            self._write_node('referenceDeclaration', self.reference))
        # List Personnel Permanent
        listPersonnelPermanent = self._get_listPersonnelPermanent()
        root.append(listPersonnelPermanent)
        # List Personnel Occasionnel
        listPersonnelOccasionnel = self._get_listPersonnelOccasionnel()
        root.append(listPersonnelOccasionnel)
        # List Stagiaires
        listStagiaires = self._get_listStagiaires()
        root.append(listStagiaires)
        # List Bénificaires
        listBeneficiaires = self._get_listBeneficiaires()
        root.append(listBeneficiaires)
        # List Bénificaires
        listBeneficiairesPlanEpargne = self._get_listBeneficiairesPlanEpargne()
        root.append(listBeneficiairesPlanEpargne)
        # List Bénificaires
        listVersements = self._get_listVersements()
        root.append(listVersements)

        return etree.tostring(root, xml_declaration=True, encoding="utf-8", pretty_print=True)

    @api.multi
    def _get_listPersonnelPermanent(self):
        listPersonnelPermanent = Element('listPersonnelPermanent')
        all_payslips = self._get_payslips('permanent')
        all_employees = all_payslips.mapped('employee_id')
        for emp in all_employees:
            payslips = all_payslips.filtered(
                lambda r: r.employee_id.id == emp.id)
            payslip_ids = payslips.mapped('id')
            tmp = Element('PersonnelPermanent')
            tmp.append(
                self._write_node('nom', emp.nom))
            tmp.append(
                self._write_node('prenom', emp.prenom))
            adressePersonnelle = ' '
            if emp.address_home_id:
                adressePersonnelle = emp.address_home_id.contact_address.strip().replace(
                    '\n', ', ')
            tmp.append(
                self._write_node('adressePersonnelle', adressePersonnelle))
            tmp.append(
                self._write_node('numCNI', emp.cin or ''))
            tmp.append(
                self._write_node('numCE', emp.carte_sejour or ''))
            tmp.append(
                self._write_node('numPPR', emp.ppr or ''))
            tmp.append(
                self._write_node('numCNSS', emp.cnss or ''))
            tmp.append(
                self._write_node('ifu', emp.identification_id or ''))
            mtBrutTraitementSalaire = self.env['hr.dictionnary'].compute_value(
                code='SALAIRE_BASE',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtBrutTraitementSalaire', mtBrutTraitementSalaire))
            periode = self.env['hr.dictionnary'].compute_value(
                code='NBR_JOURS',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('periode', periode))
            mtExonere = self.env['hr.dictionnary'].compute_value(
                code='EXONORE',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtExonere', mtExonere))
            mtEcheances = self.env['hr.dictionnary'].compute_value(
                code='INTERET',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtEcheances', mtEcheances))
            nbrReductions = self.env['hr.dictionnary'].compute_value(
                code='NBR_REDUCTION',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('nbrReductions', nbrReductions))
            mtIndemnite = self.env['hr.dictionnary'].compute_value(
                code='INDEMNITE',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtIndemnite', mtIndemnite))
            mtAvantages = self.env['hr.dictionnary'].compute_value(
                code='AVANTAGE',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtAvantages', mtAvantages))
            mtRevenuBrutImposable = self.env['hr.dictionnary'].compute_value(
                code='BRUT_IMPOSABLE',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtRevenuBrutImposable', mtRevenuBrutImposable))
            mtFraisProfess = self.env['hr.dictionnary'].compute_value(
                code='FP',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtFraisProfess', mtFraisProfess))
            mtCotisationAssur = self.env['hr.dictionnary'].compute_value(
                code='ASSURANCE_RETRAITE_SALARIALE',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtCotisationAssur', mtCotisationAssur))
            mtAutresRetenues = self.env['hr.dictionnary'].compute_value(
                code='RETENU',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            ) - mtCotisationAssur
            tmp.append(
                self._write_node('mtAutresRetenues', mtAutresRetenues))
            mtRevenuNetImposable = self.env['hr.dictionnary'].compute_value(
                code='NET_IMPOSABLE',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtRevenuNetImposable', mtRevenuNetImposable))
            mtTotalDeduction = self.env['hr.dictionnary'].compute_value(
                code='TOTAL_DEDUCTION',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtTotalDeduction', mtTotalDeduction))
            irPreleve = self.env['hr.dictionnary'].compute_value(
                code='IR',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('irPreleve', irPreleve))
            tmp.append(
                self._write_node('casSportif', 'false'))
            tmp.append(
                self._write_node('numMatricule', emp.otherid or ''))
            tmp.append(
                self._write_node('datePermis', emp.date_ph or ''))
            tmp.append(
                self._write_node('dateAutorisation', emp.date_ac or ''))
            refSituationFamiliale = Element('refSituationFamiliale')
            refSituationFamiliale.append(
                self._write_node('code', emp.marital or ''))
            refTaux = Element('refTaux')
            refTaux.append(
                self._write_node('code', payslips[0].company_id.fp_id.name or ''))
            tmp.append(refSituationFamiliale)
            tmp.append(refTaux)
            listPersonnelPermanent.append(tmp)
        return listPersonnelPermanent

    @api.multi
    def _get_listPersonnelOccasionnel(self):
        listPersonnelOccasionnel = Element('listPersonnelOccasionnel')
        all_payslips = self._get_payslips('occasional')
        all_employees = all_payslips.mapped('employee_id')
        for emp in all_employees:
            payslips = all_payslips.filtered(
                lambda r: r.employee_id.id == emp.id)
            contract = payslips[0].contract_id
            payslip_ids = payslips.mapped('id')
            tmp = Element('PersonnelOccasionnel')
            tmp.append(
                self._write_node('nom', emp.nom))
            tmp.append(
                self._write_node('prenom', emp.prenom))
            adressePersonnelle = ' '
            if emp.address_home_id:
                adressePersonnelle = emp.address_home_id.contact_address.strip().replace(
                    '\n', ', ')
            tmp.append(
                self._write_node('adressePersonnelle', adressePersonnelle))
            tmp.append(
                self._write_node('numCNI', emp.cin or ''))
            tmp.append(
                self._write_node('numCE', emp.carte_sejour or ''))
            tmp.append(
                self._write_node('ifu', emp.identification_id or ''))
            mtBrutSommes = self.env['hr.dictionnary'].compute_value(
                code='BRUT',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtBrutSommes', mtBrutSommes))
            irPreleve = self.env['hr.dictionnary'].compute_value(
                code='IR',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('irPreleve', irPreleve))
            tmp.append(
                self._write_node('profession', contract.job_id and contract.job_id.name or ''))
            listPersonnelOccasionnel.append(tmp)
        return listPersonnelOccasionnel

    @api.multi
    def _get_listStagiaires(self):
        listStagiaires = Element('listStagiaires')
        all_payslips = self._get_payslips('trainee')
        all_employees = all_payslips.mapped('employee_id')
        for emp in all_employees:
            payslips = all_payslips.filtered(
                lambda r: r.employee_id.id == emp.id)
            contract = payslips[0].contract_id
            payslip_ids = payslips.mapped('id')
            tmp = Element('Stagiaire')
            tmp.append(
                self._write_node('nom', emp.nom))
            tmp.append(
                self._write_node('prenom', emp.prenom))
            adressePersonnelle = ' '
            if emp.address_home_id:
                adressePersonnelle = emp.address_home_id.contact_address.strip().replace(
                    '\n', ', ')
            tmp.append(
                self._write_node('adressePersonnelle', adressePersonnelle))
            tmp.append(
                self._write_node('numCNI', emp.cin or ''))
            tmp.append(
                self._write_node('numCE', emp.carte_sejour or ''))
            tmp.append(
                self._write_node('numCNSS', emp.cnss or ''))
            tmp.append(
                self._write_node('ifu', emp.identification_id or ''))
            mtBrutTraitementSalaire = self.env['hr.dictionnary'].compute_value(
                code='SALAIRE_BASE',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtBrutTraitementSalaire', mtBrutTraitementSalaire))
            mtBrutIndemnites = self.env['hr.dictionnary'].compute_value(
                code='INDEMNITE',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtBrutIndemnites', mtBrutIndemnites))
            mtRetenues = self.env['hr.dictionnary'].compute_value(
                code='RETENU',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtRetenues', mtRetenues))
            mtRevenuNetImposable = self.env['hr.dictionnary'].compute_value(
                code='NET_IMPOSABLE',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('mtRevenuNetImposable', mtRevenuNetImposable))
            periode = self.env['hr.dictionnary'].compute_value(
                code='NBR_JOURS',
                date_start=self.date_from,
                date_stop=self.date_to,
                department_ids=self._get_departments(),
                state=self.state,
                company_id=self._get_companies(),
                payslip_ids=payslip_ids,
            )
            tmp.append(
                self._write_node('periode', periode))
            listStagiaires.append(tmp)
        return listStagiaires

    @api.multi
    def _get_listBeneficiaires(self):
        listBeneficiaires = Element('listBeneficiaires')
        return listBeneficiaires

    @api.multi
    def _get_listBeneficiairesPlanEpargne(self):
        listBeneficiairesPlanEpargne = Element('listBeneficiairesPlanEpargne')
        return listBeneficiairesPlanEpargne

    @api.multi
    def _get_listVersements(self):
        listVersements = Element('listVersements')
        periods = self._get_periods()
        for date_from, date_to in periods:
            VersementTraitementSalaire = Element('VersementTraitementSalaire')
            VersementTraitementSalaire.append(
                self._write_node('mois', int(date_from[5:7]))
            )
            versements = self.env['hr.common.report'].search([
                ('date_from','>=', date_from),
                ('date_to','<=', date_to),
                ('code','=', 'ir'),
                ('state','=', 'paid'),
            ], order='voucher_date desc')
            totalVersement = sum([x.ir_total for x in versements])
            dateDerniereVersment = versements and versements[0].voucher_date or 'False'
            VersementTraitementSalaire.append(
                self._write_node('totalVersement', totalVersement)
            )
            VersementTraitementSalaire.append(
                self._write_node('dateDerniereVersment', dateDerniereVersment)
            )
            # BEGIN DETAIL
            listDetailPaiement = Element('listDetailPaiement')
            for versement in versements:
                DetailPaiementTraitementSalaire = Element('DetailPaiementTraitementSalaire')
                DetailPaiementTraitementSalaire.append(
                    self._write_node('reference', versement.voucher_ref or '')
                )
                DetailPaiementTraitementSalaire.append(
                    self._write_node('totalVerse', versement.ir_total)
                )
                DetailPaiementTraitementSalaire.append(
                    self._write_node('principal', versement.ir_principal)
                )
                DetailPaiementTraitementSalaire.append(
                    self._write_node('penalite', versement.ir_penalite)
                )
                DetailPaiementTraitementSalaire.append(
                    self._write_node('majorations', versement.ir_majoration)
                )
                DetailPaiementTraitementSalaire.append(
                    self._write_node('dateVersement', versement.voucher_date)
                )
                refMoyenPaiement = Element('refMoyenPaiement')
                refMoyenPaiement.append(
                    self._write_node('code', versement.voucher_mode)
                )
                DetailPaiementTraitementSalaire.append(refMoyenPaiement)
                listDetailPaiement.append(DetailPaiementTraitementSalaire)
            VersementTraitementSalaire.append(listDetailPaiement)
            # END DETAIL
            listVersements.append(VersementTraitementSalaire)
        return listVersements
