# -*- coding: utf-8 -*-

from odoo import fields, models, api, osv
from odoo.exceptions import ValidationError
import datetime

import base64
from lxml import etree
# import xml.etree.ElementTree as etree
import xml.etree.ElementTree as ET
import zipfile
import os
directory = os.path.dirname(__file__)
xmlns_uris = {'p': 'http://www.w3.org/2001/XMLSchema-instance',
              'q': 'http://traitementSalaire.xsd'}


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    otherid = fields.Char('Num CE')


class Etat9421(models.Model):
    _name = 'etat.9421'
    _description = 'etat 9421'

    @api.model
    def get_company(self):
        company = self.env['res.company'].search([('id', '=', 1)])
        if company:
            return company[0].id
        else:
            return False

    name = fields.Char(string=u"Intitulé rapport")
    company_id = fields.Many2one('res.company', string=u'Société', default=get_company)
    annee = fields.Integer(string=u"Année fiscale")
    etat_line_ids = fields.One2many('etat.9421.line', 'id_etat')
    file_id = fields.Binary(string=u'Fichier')
    name_file = fields.Char(string=u'Nom du Fichier')

    # Champs calculés
    effectif = fields.Integer(compute='get_effectif', string="Effectif")
    nb_pp = fields.Integer(compute='get_effectif', string="Effectif Permanents")
    nb_po = fields.Integer(compute='get_effectif', string="Effectif Occasionnels")
    nb_stg = fields.Integer(compute='get_effectif', string="Effectif stagiaires")

    # Totaux permanents
    total_sbi_pp = fields.Float(compute='get_totaux', string="totalMtRevenuBrutImposablePP")
    total_sni_pp = fields.Float(compute='get_totaux', string="totalMtRevenuNetImposablePP")
    total_ir_pp = fields.Float(compute='get_totaux', string="totalMtIrPrelevePP")
    total_ded_pp = fields.Float(compute='get_totaux', string="totalMtTotalDeductionPP")

    # Totaux occasionnels
    total_sb_po = fields.Float(string="totalMtBrutSommesPO")
    total_ir_po = fields.Float(string="totalIrPrelevePO")

    # Totaux stagiaires
    total_brut_stg = fields.Float(string="totalMtBrutTraitSalaireSTG")
    total_ind_stg = fields.Float(string="totalMtBrutIndemnitesSTG")
    total_ret_stg = fields.Float(string="totalMtRetenuesSTG")
    total_net_stg = fields.Float(string="totalMtRevenuNetImpSTG")

    # Totaux spéciaux
    somme_rts = fields.Float(string="totalSommePayeRTS", compute='get_somme_rts')
    tot_rev_annuel = fields.Float(string="totalmtAnuuelRevenuSalarial", compute='get_somme_rts')
    mt_abondement = fields.Float(string="totalmtAbondement")
    mt_permanent = fields.Float(string="montantPermanent")
    mt_occasionnel = fields.Float(string="montantOccasionnel")
    mt_stagiaire = fields.Float(string="montantStagiaire")
    ref_declaration = fields.Char(string="referenceDeclaration", default='345678')

    @api.multi
    @api.depends('total_sbi_pp', 'total_sb_po', 'total_brut_stg')
    def get_somme_rts(self):
        for rec in self:
            rec.somme_rts = rec.total_sbi_pp + rec.total_sb_po + rec.total_brut_stg

    @api.multi
    def get_totaux(self):
        tot_sb_pp = 0
        tot_sb_stg = 0
        tot_sbi = 0
        tot_sni = 0
        tot_ir = 0
        tot_ir_pp = 0
        tot_ded = 0
        total_indm = 0
        tot_ded_stg = 0
        tot_sni_stg = 0
        for rec in self:
            for line in rec.etat_line_ids:
                if line.employee_id.contract_id.type_id == self.env.ref('hr_contract.hr_contract_type_emp'):
                    tot_sbi += line.s_sbi
                    tot_sni += line.s_sni
                    tot_ir += line.s_igr
                    tot_ded += line.s_total_deductions
                if line.employee_id.contract_id.type_id == self.env.ref('hr_contract.hr_contract_type_wrkr'):
                    tot_sb_pp += line.s_salaire_brut
                    tot_ir_pp += line.s_igr
                if line.employee_id.contract_id.type_id == self.env.ref('hr_contract.hr_contract_type_sub'):
                    tot_sb_stg += line.s_salaire_brut
                    total_indm += line.s_indemnites
                    tot_ded_stg += line.s_total_deductions
                    tot_sni_stg += line.s_sni
        # personnel permanent
        rec.total_sbi_pp = tot_sbi
        rec.total_sni_pp = tot_sni
        rec.total_ir_pp = tot_ir
        rec.total_ded_pp = tot_ded
        # personnel occasionnel
        rec.total_sb_po = tot_sb_pp
        rec.total_ir_po = tot_ir
        # stagiaire
        rec.total_brut_stg = tot_sb_stg
        rec.total_ind_stg = total_indm
        rec.total_ret_stg = tot_ded_stg
        rec.total_net_stg = tot_sni_stg

    @api.multi
    def get_effectif(self):
        for rec in self:
            count_pp = 0
            count_po = 0
            count_stg = 0
            for line in rec.etat_line_ids:
                if line.employee_id.contract_id.type_id == self.env.ref('hr_contract.hr_contract_type_emp'):
                    count_pp += 1
                if line.employee_id.contract_id.type_id == self.env.ref('hr_contract.hr_contract_type_wrkr'):
                    count_po += 1
                if line.employee_id.contract_id.type_id == self.env.ref('hr_contract.hr_contract_type_sub'):
                    count_stg += 1
            rec.nb_pp = count_pp
            rec.nb_po = count_po
            rec.nb_stg = count_stg
            rec.effectif = count_pp + count_po + count_stg

    @api.multi
    def generate_edi_file(self):
        societe = self.env['res.company'].search([('id', '=', 1)])
        for rec in self:
            societe = rec.company_id.partner_id
            niv_1 = etree.Element("TraitementEtSalaire")
            etree.SubElement(niv_1, "identifiantFiscal").text = societe.vat or ''
            etree.SubElement(niv_1, "nom").text = ""
            etree.SubElement(niv_1, "prenom").text = ""
            etree.SubElement(niv_1, "raisonSociale").text = societe.name
            etree.SubElement(niv_1, "exerciceFiscalDu").text = str(rec.annee) + "-01-01"
            etree.SubElement(niv_1, "exerciceFiscalDAu").text = str(rec.annee) + "-12-31"
            etree.SubElement(niv_1, "annee").text = str(rec.annee)
            commune = etree.SubElement(niv_1, "commune")
            etree.SubElement(commune, "code").text = str(societe.code_commune)
            adresse = ""
            if societe.street:
                adresse = societe.street.encode('utf8').decode('utf8',errors='xmlcharrefreplace') or ''
            if societe.street2:
                adresse = adresse+' '+societe.street2.encode('utf8').decode('utf8',errors='xmlcharrefreplace') or ''
            if societe.city:
                adresse = adresse+', '+societe.city.encode('utf8').decode('utf8',errors='xmlcharrefreplace') or ''
            if societe.zip:
                adresse = adresse+', '+societe.zip.encode('utf8').decode('utf8',errors='xmlcharrefreplace') or ''
            if societe.country_id:
                adresse = adresse+', '+societe.country_id.name.encode('utf8').decode('utf8',errors='xmlcharrefreplace') or ''
            print("adresse  : ",adresse)
            etree.SubElement(niv_1, "adresse").text = adresse
            etree.SubElement(niv_1, "numeroCIN").text = ""
            etree.SubElement(niv_1, "numeroCNSS").text = str(societe.cnss)
            etree.SubElement(niv_1, "numeroCE").text = str(societe.ice)
            etree.SubElement(niv_1, "numeroRC").text = str(societe.rc)
            etree.SubElement(niv_1, "identifiantTP").text = str(societe.itp)
            etree.SubElement(niv_1, "numeroFax").text = str(societe.fax)
            etree.SubElement(niv_1, "numeroTelephone").text = str(societe.phone)
            etree.SubElement(niv_1, "email").text = str(societe.email)

            etree.SubElement(niv_1, "effectifTotal").text = str(rec.effectif)

            etree.SubElement(niv_1, "nbrPersoPermanent").text = str(rec.nb_pp)
            etree.SubElement(niv_1, "nbrPersoOccasionnel").text = str(rec.nb_po)
            etree.SubElement(niv_1, "nbrStagiaires").text = str(rec.nb_stg)

            etree.SubElement(niv_1, "totalMtRevenuBrutImposablePP").text = str(rec.total_sbi_pp)
            etree.SubElement(niv_1, "totalMtRevenuNetImposablePP").text = str(rec.total_sni_pp)
            etree.SubElement(niv_1, "totalMtTotalDeductionPP").text = str(rec.total_ded_pp)
            etree.SubElement(niv_1, "totalMtIrPrelevePP").text = str(rec.total_ir_pp)

            etree.SubElement(niv_1, "totalMtBrutSommesPO").text = str(rec.total_sb_po)
            etree.SubElement(niv_1, "totalIrPrelevePO").text = str(rec.total_ir_po)

            etree.SubElement(niv_1, "totalMtBrutTraitSalaireSTG").text = str(rec.total_brut_stg)
            etree.SubElement(niv_1, "totalMtBrutIndemnitesSTG").text = str(rec.total_ind_stg)
            etree.SubElement(niv_1, "totalMtRetenuesSTG").text = str(rec.total_ret_stg)
            etree.SubElement(niv_1, "totalMtRevenuNetImpSTG").text = str(rec.total_net_stg)

            etree.SubElement(niv_1, "totalSommePayeRTS").text = str(rec.somme_rts)
            etree.SubElement(niv_1, "totalmtAnuuelRevenuSalarial").text = str(rec.tot_rev_annuel)
            etree.SubElement(niv_1, "totalmtAbondement").text = str(rec.mt_abondement)
            etree.SubElement(niv_1, "montantPermanent").text = str(rec.mt_permanent)
            etree.SubElement(niv_1, "montantOccasionnel").text = str(rec.mt_occasionnel)
            etree.SubElement(niv_1, "montantStagiaire").text = str(rec.mt_stagiaire)

            liste_pp1 = etree.SubElement(niv_1, "listPersonnelPermanent")

            for line in rec.etat_line_ids:
                if line.employee_id.contract_id.type_id == self.env.ref('hr_contract.hr_contract_type_emp'):
                    liste_pp = etree.SubElement(liste_pp1, "PersonnelPermanent")
                    etree.SubElement(liste_pp, "nom").text = str(line.employee_id.name)
                    etree.SubElement(liste_pp, "prenom").text = str(line.employee_id.prenom)
                    adresse = ""
                    if line.employee_id.address_home:
                        adresse = line.employee_id.address_home.encode('utf8')

                    etree.SubElement(liste_pp, "adressePersonnelle").text = adresse
                    etree.SubElement(liste_pp, "numCNI").text = str(line.employee_id.cin)
                    etree.SubElement(liste_pp, "numCE").text = str(line.employee_id.otherid)
                    etree.SubElement(liste_pp, "numPPR").text = str(line.employee_id.n_ppr)
                    etree.SubElement(liste_pp, "numCNSS").text = str(line.employee_id.ssnid)
                    etree.SubElement(liste_pp, "ifu").text = str(line.employee_id.ifu)

                    date_start = datetime.date(year=rec.annee, month=1, day=1)
                    date_end = datetime.date(year=rec.annee, month=12, day=31)
                    bulletins = self.env['hr.payroll_ma.bulletin'].search([('employee_id', '=', line.employee_id.id),
                                                                           ('period_id.date_start', '>=', date_start),
                                                                           ('period_id.date_end', '<=', date_end)])
                    salaire_base = 0
                    for bulletin in bulletins:
                        salaire_base += bulletin.salaire_base

                    etree.SubElement(liste_pp, "salaireBaseAnnuel").text = str(salaire_base)
                    etree.SubElement(liste_pp, "mtBrutTraitementSalaire").text = str(line.s_salaire_brut)
                    etree.SubElement(liste_pp, "periode").text = str(line.s_jrs)
                    operateur = 'in'
                    ids = tuple(bulletins.ids)
                    if len(bulletins) == 1:
                        operateur = '='
                        ids = bulletins.id
                    sql = """SELECT r.code as code, sum(l.subtotal_employee) as subtotal_employee
                            FROM hr_payroll_ma_bulletin_line l
                            JOIN hr_payroll_ma_rubrique r ON (r.name=l.name)
                            where l.id_bulletin %s %s and r.imposable = False and r.categorie = 'majoration'
                            group by code
                        """ % (operateur, ids)
                    self.env.cr.execute(sql)
                    data = self.env.cr.dictfetchall()
                    exonere = 0
                    for d in data:
                        exonere += d['subtotal_employee']
                    etree.SubElement(liste_pp, "mtExonere").text = str(exonere)
                    etree.SubElement(liste_pp, "mtEcheances").text = str(0.0)
                    etree.SubElement(liste_pp, "nbrReductions").text = str(line.nbr_reductions)
                    etree.SubElement(liste_pp, "mtIndemnite").text = str(line.s_ind_fp)
                    operateur = 'in'
                    ids = tuple(bulletins.ids)
                    if len(bulletins) == 1:
                        operateur = '='
                        ids = bulletins.id
                    sql = """SELECT r.code as code, sum(l.subtotal_employee) as subtotal_employee
                                                FROM hr_payroll_ma_bulletin_line l
                                                JOIN hr_payroll_ma_rubrique r ON (r.name=l.name)
                                                where l.id_bulletin %s %s and r.type = 'avantage' and r.categorie = 'majoration'
                                                group by code
                                            """ % (operateur, ids)
                    self.env.cr.execute(sql)
                    data_avn = self.env.cr.dictfetchall()
                    avantage = 0
                    for d in data_avn:
                        avantage += d['subtotal_employee']
                    etree.SubElement(liste_pp, "mtAvantages").text = str(avantage)
                    etree.SubElement(liste_pp, "mtRevenuBrutImposable").text = str(line.s_sbi)
                    etree.SubElement(liste_pp, "mtFraisProfess").text = str(line.s_frais_pro)
                    etree.SubElement(liste_pp, "mtCotisationAssur").text = str(line.s_cot_ass)
                    etree.SubElement(liste_pp, "mtAutresRetenues").text = str(line.s_autres_ret)
                    etree.SubElement(liste_pp, "mtRevenuNetImposable").text = str(line.s_sni)
                    etree.SubElement(liste_pp, "mtTotalDeduction").text = str(line.s_total_deductions)
                    etree.SubElement(liste_pp, "irPreleve").text = str(line.s_igr)
                    etree.SubElement(liste_pp, "casSportif").text = "false"
                    etree.SubElement(liste_pp, "numMatricule").text = str(line.employee_id.matricule)
                    etree.SubElement(liste_pp, "datePermis").text = ""
                    etree.SubElement(liste_pp, "dateAutorisation").text = ""
                    sit_fam = etree.SubElement(liste_pp, "refSituationFamiliale")
                    etree.SubElement(sit_fam, "code").text = str(line.situation)
                    taux = etree.SubElement(liste_pp, "refTaux")
                    etree.SubElement(taux, "code").text = str(societe.taux_fp)

                    # EXONERATION
                    exo = etree.SubElement(liste_pp, "listElementsExonere")
                    for d in data:
                        exopp = etree.SubElement(exo, "ElementExonerePP")
                        etree.SubElement(exopp, "montantExonere").text = str(d['subtotal_employee'])
                        exoppline = etree.SubElement(exopp, "refNatureElementExonere")
                        etree.SubElement(exoppline, "code").text = str(d['code'])

            liste_pp1 = etree.SubElement(niv_1, "listPersonnelExonere")
            for line in rec.etat_line_ids:
                if line.employee_id.contract_id.type_id == self.env.ref('kzm_edi_simplir.hr_contract_type_exempt'):
                    liste_pp = etree.SubElement(liste_pp1, "PersonnelExonere")
                    etree.SubElement(liste_pp, "nom").text = str(line.employee_id.name)
                    etree.SubElement(liste_pp, "prenom").text = str(line.employee_id.prenom)
                    adresse = ""
                    if line.employee_id.address_home:
                        adresse = line.employee_id.address_home.encode('utf8')

                    etree.SubElement(liste_pp, "adressePersonnelle").text = adresse.decode('utf8', errors='xmlcharrefreplace')
                    etree.SubElement(liste_pp, "numCNI").text = str(line.employee_id.cin)
                    etree.SubElement(liste_pp, "numCE").text = str(line.employee_id.otherid)
                    etree.SubElement(liste_pp, "numCNSS").text = str(line.employee_id.ssnid)
                    etree.SubElement(liste_pp, "ifu").text = str(line.employee_id.ifu)
                    etree.SubElement(liste_pp, "periode").text = str(line.s_jrs)
                    etree.SubElement(liste_pp, "dateRecrutement").text = str(line.employee_id.date)
                    etree.SubElement(liste_pp, "mtBrutTraitementSalaire").text = str(line.s_salaire_brut)
                    etree.SubElement(liste_pp, "mtIndemniteArgentNature").text = str(line.s_avantage_nature)
                    etree.SubElement(liste_pp, "mtIndemniteFraisPro").text = str(line.s_frais_pro)
                    etree.SubElement(liste_pp, "mtRevenuBrutImposable").text = str(line.s_sbi)
                    etree.SubElement(liste_pp, "mtRetenuesOperees").text = str(line.s_autres_ret)
                    etree.SubElement(liste_pp, "mtRevenuNetImposable").text = str(line.s_sni)

            liste_pp1 = etree.SubElement(niv_1, "listPersonnelOccasionnel")

            for line in rec.etat_line_ids:
                if line.employee_id.contract_id.type_id == self.env.ref('hr_contract.hr_contract_type_wrkr'):
                    liste_pp = etree.SubElement(liste_pp1, "PersonnelOccasionnel")
                    etree.SubElement(liste_pp, "nom").text = str(line.employee_id.name)
                    etree.SubElement(liste_pp, "prenom").text = str(line.employee_id.prenom)
                    adresse = ""
                    if line.employee_id.address_home:
                        adresse = line.employee_id.address_home.encode('utf8')

                    etree.SubElement(liste_pp, "adressePersonnelle").text = adresse.decode('utf8', errors='xmlcharrefreplace')
                    etree.SubElement(liste_pp, "numCNI").text = str(line.employee_id.cin)
                    etree.SubElement(liste_pp, "numCE").text = str(line.employee_id.otherid)
                    etree.SubElement(liste_pp, "ifu").text = str(line.employee_id.ifu)
                    etree.SubElement(liste_pp, "mtBrutSommes").text = str(line.s_salaire_brut)
                    etree.SubElement(liste_pp, "irPreleve").text = str(line.s_igr)
                    etree.SubElement(liste_pp, "profession").text = str(u'%s') % (line.employee_id.job_id.name)

            liste_pp1 = etree.SubElement(niv_1, "listStagiaires")
            for line in rec.etat_line_ids:
                if line.employee_id.contract_id.type_id == self.env.ref('hr_contract.hr_contract_type_wrkr'):
                    liste_pp = etree.SubElement(liste_pp1, "Stagiaire")
                    etree.SubElement(liste_pp, "nom").text = str(line.employee_id.name)
                    etree.SubElement(liste_pp, "prenom").text = str(line.employee_id.prenom)
                    adresse = ""
                    if line.employee_id.address_home:
                        adresse = line.employee_id.address_home.encode('utf8')

                    etree.SubElement(liste_pp, "adressePersonnelle").text = adresse.decode('utf8',
                                                                                        errors='xmlcharrefreplace')
                    etree.SubElement(liste_pp, "numCNI").text = str(line.employee_id.cin)
                    etree.SubElement(liste_pp, "numCE").text = str(line.employee_id.otherid)
                    etree.SubElement(liste_pp, "numCNSS").text = str(line.employee_id.ssnid)
                    etree.SubElement(liste_pp, "ifu").text = str(line.employee_id.ifu)
                    etree.SubElement(liste_pp, "mtBrutTraitementSalaire").text = str(line.s_salaire_brut)
                    etree.SubElement(liste_pp, "mtBrutIndemnites").text = str(line.s_ind_fp)
                    etree.SubElement(liste_pp, "mtRetenues").text = str(line.s_autres_ret)
                    etree.SubElement(liste_pp, "mtRevenuNetImposable").text = str(line.s_sni)
                    etree.SubElement(liste_pp, "periode").text = str(line.s_jrs)

            liste_pp1 = etree.SubElement(niv_1, "listDoctorants")
            for line in rec.etat_line_ids:
                if line.employee_id.contract_id.type_id == self.env.ref('kzm_edi_simplir.hr_contract_type_phd_student'):
                    liste_pp = etree.SubElement(liste_pp1, "Doctorant")
                    etree.SubElement(liste_pp, "nom").text = str(line.employee_id.name)
                    etree.SubElement(liste_pp, "prenom").text = str(line.employee_id.prenom)
                    adresse = ""
                    if line.employee_id.address_home:
                        adresse = line.employee_id.address_home.encode('utf8')

                    etree.SubElement(liste_pp, "adressePersonnelle").text = adresse.decode('utf8',
                                                                                           errors='xmlcharrefreplace')
                    etree.SubElement(liste_pp, "numCNI").text = str(line.employee_id.cin)
                    etree.SubElement(liste_pp, "numCE").text = str(line.employee_id.otherid)
                    etree.SubElement(liste_pp, "mtBrutIndemnites").text = str(line.s_ind_fp)

            liste_pp = etree.SubElement(niv_1, "listBeneficiaires")
            liste_pp = etree.SubElement(niv_1, "listBeneficiairesPlanEpargne")

            liste_pp1 = etree.SubElement(niv_1, "listVersements")
            for month in range(1, 13):
                date_start = datetime.date(year=rec.annee, month=month, day=1)
                date_end = self.last_day_of_month(datetime.date(rec.annee, month, 1))
                payments = self.env['hr.payroll_ma'].search(
                    [('date_start', '<=', date_start), ('date_end', '>=', date_end)])
                totalversement = 0
                principal = 0
                penalite = 0
                majoration = 0
                for payment in payments:
                    totalversement += payment.total_net
                    for bul in payment.bulletin_line_ids:
                        principal += bul.salaire_net_a_payer
                    penalite += payment.penalite
                    majoration += payment.majoration

                liste_pp = etree.SubElement(liste_pp1, "VersementTraitementSalaire")
                etree.SubElement(liste_pp, "mois").text = str(month)
                etree.SubElement(liste_pp, "totalVersement").text = str(totalversement)
                etree.SubElement(liste_pp, "dateDerniereVersment").text = str(date_start)

                if payments:
                    name = payments[0].period_id.name
                    date = payments[0].date_salary
                    ref = payments[0].ref_payment
                    num = payments[0].num_quittance
                else:
                    name = ""
                    date = ""
                    ref = ""
                    num = ""
                liste_pp2 = etree.SubElement(liste_pp, "listDetailPaiement")
                liste_pp3 = etree.SubElement(liste_pp2, "DetailPaiementTraitementSalaire")
                etree.SubElement(liste_pp3, "reference").text = str(name)
                etree.SubElement(liste_pp3, "totalVerse").text = str(totalversement)
                etree.SubElement(liste_pp3, "principal").text = str(principal)
                etree.SubElement(liste_pp3, "penalite").text = str(penalite)
                etree.SubElement(liste_pp3, "majorations").text = str(majoration)
                etree.SubElement(liste_pp3, "dateVersement").text = str(date)
                liste_pp4 = etree.SubElement(liste_pp3, "refMoyenPaiement")
                etree.SubElement(liste_pp4, "code").text = str(ref)
                etree.SubElement(liste_pp, "numQuittance").text = str(num)
            # self.annotate_with_XMLNS_prefixes(niv_1, 'xsi')
            # self.add_XMLNS_attributes(niv_1, xmlns_uris)
            tree = etree.ElementTree(niv_1)
            file = open(os.path.join(directory, 'SimplIGR.xml'), 'wb')
            # file.write(etree.tostring(niv_1, encoding='UTF-8', xml_declaration=True))
            file.write(etree.tostring(niv_1))
            file.close()
            zf = zipfile.ZipFile(os.path.join(directory, 'SimplIGR.zip'), mode='w')
            try:
                zf.write(os.path.join(directory, 'SimplIGR.xml'), arcname='SimplIGR.xml')
            finally:
                zf.close()
            xml_file = base64.encodestring(open(os.path.join(directory, 'SimplIGR.zip'), 'rb').read())

            filename = rec.env.user.company_id.name
            extension = 'zip'
            name = "%s.%s" % (filename, extension)
            rec.write({'file_id': xml_file, 'name_file': name})

    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
        return next_month - datetime.timedelta(days=next_month.day)

    def annotate_with_XMLNS_prefixes(ztree, xmlns_prefix, skip_root_node=True):
        if not etree.iselement(ztree):
            ztree = ztree.getroot()
        iterator = ztree.iter()
        if skip_root_node:  # Add XMLNS prefix also to the root node?
            iterator.next()
        for e in iterator:
            if not ':' in e.tag:
                e.tag = xmlns_prefix + ":" + e.tag

    def add_XMLNS_attributes(ztree, xmlns_uris_dict):
        if not etree.iselement(ztree):
            ztree = ztree.getroot()
        for prefix, uri in xmlns_uris_dict.items():
            ztree.attrib['xmlns:' + prefix] = uri

    @api.multi
    def generer_etat_9421(self):
        p = self.env['date.range']
        bul = self.env['hr.payroll_ma.bulletin']
        line_etat = self.env['etat.9421.line']

        for res in self:
            if not res.annee:
                raise ValidationError(u"Merci de specifier l'Année fiscale")
            res.name = "Etat 9421 - Année : " + str(res.annee)
            # extraction des period_ids incluses dans l'année sélectionnée
            periodes = []
            for i in range(1, 13, 1):
                v_period = str(i).rjust(2, '0') + '/' + str(res.annee)
                r_period = p.search([('name', '=', v_period)])
                if r_period:
                    periodes.append(r_period.id)

            # Suppression des lignes déjà existantes
            query = " DELETE FROM etat_9421_line WHERE id_etat =" + str(res.id) + ". "
            res.env.cr.execute(query)
            # res.env.invalidate_all()

            # Identification de tous les employés qui ont été déclarés durant l'année sélectionnée
            r_employe = bul.search([('period_id', 'in', tuple(periodes))])

            requete = "select distinct(a.employee_id), (select max(period_id) " \
                      "from hr_payroll_ma_bulletin where employee_id = a.employee_id and company_id = %s and " \
                      " period_id in " + str(tuple(periodes)) + " ) " \
                                                                "from hr_payroll_ma_bulletin a " \
                                                                "where period_id in " + str(tuple(periodes)) + "" \
                                                                                                               " group by employee_id, period_id  order by employee_id"
            self._cr.execute(requete, (res.company_id.id,))
            resultat = self._cr.fetchall()
            for j in resultat:
                if j[0] and j[1]:
                    bulletin = bul.search([('employee_id', '=', int(j[0])), ('period_id', '=', int(j[1]))])
                    line_etat.create({
                        'id_etat': res.id,
                        'employee_id': j[0],
                        'period_id': j[1],
                        's_salaire_base': bulletin.cumul_base,
                        's_salaire_brut': bulletin.cumul_sb,
                        's_avantage_nature': bulletin.cumul_avantages,
                        's_ind_fp': bulletin.cumul_indemnites_fp,
                        's_indemnites': bulletin.cumul_exo,
                        'taux_fp': 20,
                        's_sbi': bulletin.cumul_sbi,
                        's_frais_pro': bulletin.cumul_fp,
                        's_cot_ass': 0.0,
                        's_autres_ret': bulletin.cumul_ee_cotis,
                        's_sni': bulletin.cumul_sni,
                        's_jrs': bulletin.cumul_work_days,
                        's_igr': bulletin.cumul_igr,
                        'nbr_reductions': bulletin.personnes,
                    })


class Etat9421Line(models.Model):
    _name = 'etat.9421.line'
    _description = 'etat 9421 line'
    _order = 'matricule'

    id_etat = fields.Many2one('etat.9421')

    # détail ligne
    employee_id = fields.Many2one('hr.employee', string=u"Employé")
    matricule = fields.Char(related='employee_id.matricule', string="Matricule", store=True)
    cin = fields.Char(related='employee_id.cin', string="CIN")
    cnss = fields.Char(related='employee_id.ssnid', string=u"N°CNSS")
    adresse = fields.Char(related='employee_id.address_home', string="Adresse personnelle")
    situation = fields.Char(compute='get_marital_status', string="Situation")
    period_id = fields.Many2one('date.range', domain="[('type_id.fiscal_period','=',True)]", string=u"Période")
    # les cumuls
    s_salaire_base = fields.Float(string="Salaire base")
    s_salaire_brut = fields.Float(string="Salaire brut")
    s_avantage_nature = fields.Float(string="avantages en nature")
    s_ind_fp = fields.Float(string=u"Montant ind. frais pro")
    s_indemnites = fields.Float(string=u"Montant exonérations")
    taux_fp = fields.Integer(string="Taux frais professionnels")
    s_sbi = fields.Float(string="Revenue brut imposable")
    s_frais_pro = fields.Float(string="Montant Frais professionnels")
    s_cot_ass = fields.Float(string="Cotisations assurance")
    s_autres_ret = fields.Float(string="Autres retenues")
    s_total_deductions = fields.Float(string="Total des déductions", compute='get_total_deductions')
    s_ech = fields.Float(string=u"Montant échéances")
    s_date_ac = fields.Date(string=u"Date de l'AC")
    s_date_ph = fields.Date(string="Date du PH")
    s_sni = fields.Float(string="Net imposable")
    nbr_reductions = fields.Integer(string=u"Nbr déductions charges de famille")
    s_jrs = fields.Float(string=u"Période en jours")
    s_igr = fields.Float(string=u"I.R prélevé")

    @api.multi
    @api.depends('s_frais_pro', 's_cot_ass', 's_autres_ret')
    def get_total_deductions(self):
        for rec in self:
            rec.s_total_deductions = rec.s_frais_pro + rec.s_cot_ass + rec.s_autres_ret

    @api.multi
    def get_marital_status(self):
        for res in self:
            if res.employee_id.marital == 'single':
                res.situation = 'C'
            if res.employee_id.marital == 'married':
                res.situation = 'M'
            if res.employee_id.marital == 'divorced':
                res.situation = 'D'
            if res.employee_id.marital == 'widower':
                res.situation = 'V'
