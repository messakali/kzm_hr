# -*- coding: utf-8 -*-

from odoo import fields, models,api


class RapportCimr(models.Model):
        _name = 'rapport.cimr'
        _description = 'Rapport Cimr'

        name = fields.Char(string=u'Intitulé rapport', default="Etat CIMR")
        company_id = fields.Many2one('res.company', u'Societé', default=lambda self: self.env.user.company_id,
                                     required=True)
        annee = fields.Integer(string=u'Année', required=True)
        trimestre = fields.Selection(string="Trimestre", selection='get_quarters', required=True)
        rep_cimr_line_ids = fields.One2many('rapport.cimr.line','id_rep_cimr')

        all_bs = fields.Float(compute='get_tot_rapport',string="total base soumise")
        all_bc = fields.Float(compute='get_tot_rapport',string="total base calcul")
        all_ps = fields.Float(compute='get_tot_rapport',string="total part salariale")
        all_pp = fields.Float(compute='get_tot_rapport',string="total part patronale")
        all_tot_part = fields.Float(compute='get_tot_rapport',string="total part sal + pat")
        all_cum_bs = fields.Float(compute='get_tot_rapport',string="total cumul base soumise")
        all_cum_bc = fields.Float(compute='get_tot_rapport',string="total cumul base calcul")
        all_cum_ps = fields.Float(compute='get_tot_rapport',string="total cumul part salariale")
        all_cum_pp = fields.Float(compute='get_tot_rapport',string="total cumul part patronale")
        all_cum_tot_part = fields.Float(compute='get_tot_rapport',string="total cumul part sal + pat")


        @api.depends('rep_cimr_line_ids')
        def get_tot_rapport(self):
            somme1 = 0
            somme2 = 0
            somme3 = 0
            somme4 = 0
            somme5 = 0
            somme6 = 0
            somme7 = 0
            somme8 = 0
            somme9 = 0
            somme10 = 0
            for res in self:
                for line in res.rep_cimr_line_ids:
                    somme2 += line.base_calcul
                    somme3 += line.part_salariale
                    somme4 += line.part_patronale
                    somme5 += line.total_part
                    somme7 += line.cum_base_calcul
                    somme8 += line.cum_part_salariale
                    somme9 += line.cum_part_patronale
                    somme10 += line.cum_total_part

                res.all_bs = somme1
                res.all_bc = somme2
                res.all_ps = somme3
                res.all_pp = somme4
                res.all_tot_part = somme5
                res.all_cum_bs = somme6
                res.all_cum_bc = somme7
                res.all_cum_ps = somme8
                res.all_cum_pp = somme9
                res.all_cum_tot_part = somme10

        def get_quarters(self):
            return (
                ('1', u'1er Trimestre'),
                ('2', u'2ème Trimestre'),
                ('3', u'3ème Trimestre'),
                ('4', u'4ème Trimestre')
            )

        # Fonction qui génère les résultats du rapport

        def generer_rapport_cimr(self):
            employe = self.env['hr.employee']
            contract_obj = self.env['hr.contract']
            l_rapport_cimr = self.env['rapport.cimr.line']
            employee_sortant_obj = self.env['cimr.employee.sortant']

            ligne_bul_paie = self.env['hr.payroll_ma.bulletin.line']
            acct_period = self.env['date.range']
            bul = self.env['hr.payroll_ma.bulletin']

            for rec in self:
                query = "DELETE FROM rapport_cimr_line WHERE id_rep_cimr ="+str(rec.id)+". "
                self._cr.execute(query)
                period = str(rec.trimestre).rjust(2, '0') + "/" + str(rec.annee)
                # Je parcours la liste des employés
                for emp in employe.search([('active', '=', True)]).sorted(key=lambda r: int(r.matricule)):
                    contract = contract_obj.search([('employee_id', '=', emp.id), ('state', 'in', ('pending', 'open'))], order='date_start', limit=1)
                    bulletin = bul.search([('period_id.name', '=', period), ('employee_id', '=', emp.id)])

                    taux_emp = ligne_bul_paie.search([('id_bulletin', '=', bulletin.id), ('name', 'like', '%CIMR%')]).rate_employee or 0
                    if contract:
                        l_rapport_cimr.create({
                            'id_rep_cimr': rec.id,
                            'employee_id': emp.id,
                            'taux_emp': taux_emp,
                        })
                employee_sortant_id = employee_sortant_obj.search([('name', '=', rec.trimestre),
                                                                   ('company_id', '=', rec.company_id.id)], limit=1)
                for empl_sort in employee_sortant_id.cimr_sortant_line_ids:
                    contract = contract_obj.search([('employee_id', '=', empl_sort.employee_id.id),
                                                    ('state', 'not in', ('pending', 'open'))], order='date_start', limit=1)
                    bulletin = bul.search([('period_id.name', '=', period), ('employee_id', '=', empl_sort.employee_id.id)])
                    taux_emp = ligne_bul_paie.search(
                        [('id_bulletin', '=', bulletin.id), ('name', 'like', '%CIMR%')]).rate_employee or 0
                    if contract:
                        l_rapport_cimr.create({
                            'id_rep_cimr': rec.id,
                            'employee_id': empl_sort.employee_id.id,
                            'taux_emp': taux_emp,
                        })


class RapportCimrLine(models.Model):
        _name = 'rapport.cimr.line'
        _description = 'Rapport Cimr Line'

        # détail ligne
        employee_id = fields.Many2one('hr.employee', string=u'Employé')
        matricule = fields.Char(related='employee_id.matricule', string="Matricule")
        num_cimr = fields.Char(related='employee_id.cimr', string=u'N° CIMR')
        nom_complet = fields.Char(compute='get_trimestre_val', string="Nom complet")

        # Calculs relatif au trimestre choisi
        taux_emp = fields.Float(u'Taux de cotisation employé')
        base_calcul = fields.Float(compute='get_trimestre_val', string="Base calcul")
        part_salariale = fields.Float(compute='get_trimestre_val', string="Part salariale")
        part_patronale = fields.Float(compute='get_trimestre_val', string="Part patronale")
        total_part = fields.Float(compute='get_trimestre_val', string=u'Total part Sal + Pat')

        # Cumul depuis le début d'année
        cum_base_calcul = fields.Float(compute='get_trimestre_val', string="Base calcul")
        cum_part_salariale = fields.Float(compute='get_trimestre_val', string="Part salariale")
        cum_part_patronale = fields.Float(compute='get_trimestre_val', string="Part patronale")
        cum_total_part = fields.Float(compute='get_trimestre_val', string=u'Total part Sal + Pat')

        id_rep_cimr = fields.Many2one('rapport.cimr')


        def get_trimestre_val(self):
            for res in self:
                # On détermine le dernier mois du trimestre
                v_trim = int(res.id_rep_cimr.trimestre) * 3
                somme_employe = 0
                somme_employeur = 0
                somme_base_calcul = 0
                res.nom_complet = res.employee_id.name + ' '+ res.employee_id.prenom

                # On parcours tous les mois en commençant par le dernier mois et en terminant par le premier mois
                for mois in range(v_trim, 0, -1):

                    # On extrait les valeurs du mois et on incrémente les compteurs
                    cimr = res.get_cimr_vals(mois, res.id_rep_cimr.annee,res.employee_id.id)
                    somme_employe += cimr['somme_employe']
                    somme_employeur += cimr['somme_employeur']
                    somme_base_calcul += cimr['somme_base_calcul']

                    # à ce niveau, on met à jour les valeurs du trimestre
                    if mois == v_trim - 2 :
                        res.base_calcul = somme_base_calcul
                        res.part_salariale = somme_employe
                        res.part_patronale = somme_employeur
                        res.total_part = (somme_employeur + somme_employe)

                    # à ce niveau, on met à jour les valeurs cumulatives depuis le début d'année jusqu'au mois en cours
                    if mois == 1:
                        res.cum_base_calcul = somme_base_calcul
                        res.cum_part_salariale = somme_employe
                        res.cum_part_patronale = somme_employeur
                        res.cum_total_part = (somme_employeur + somme_employe)

        # Fonction qui retourne les valeurs de la rubrique "CIMR", pour un mois donné et une année donnée
        def get_cimr_vals(self, mois, annee, employe):
            ligne_bul_paie = self.env['hr.payroll_ma.bulletin.line']
            acct_period = self.env['date.range']
            bul = self.env['hr.payroll_ma.bulletin']
            cimr_vals = {}

            v_period = str(mois).rjust(2,'0') + "/" + str(annee)
            period = acct_period.search([('name', '=', v_period)])
            bulletin = bul.search([('period_id', '=', period.id), ('employee_id', '=', employe)])

            cimr_vals['somme_employe'] = ligne_bul_paie.search([('id_bulletin', '=', bulletin.id),
                                                                ('name', 'like', '%CIMR%')]).subtotal_employee or 0
            cimr_vals['somme_employeur'] = ligne_bul_paie.search([('id_bulletin', '=', bulletin.id),
                                                                  ('name', 'like', '%CIMR%')]).subtotal_employer or 0
            cimr_vals['somme_base_calcul'] = ligne_bul_paie.search([('id_bulletin', '=', bulletin.id),
                                                                    ('name', 'like', '%CIMR%')]).base or 0

            return cimr_vals
