# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class KzmResCompany(models.Model):
    _inherit = "res.company"



    arrondi = fields.Boolean("Arrondi", default=True)
    charge = fields.Float(string="Charges familiales", default=30, help="Les charges de famille déduites de IR")
    hour_day = fields.Float(string="Nbr heures par jour", default=8, help="Nbr des heures de travaille par jour")
    hour_month = fields.Float(string="Nbr heures par mois", default=191, help="Nbr des heures de travaille par mois")
    fraispro = fields.Float(string="Frais Professionnels", default=20)
    plafond = fields.Float(string="Plafond",default=2500)
    credit_account_id = fields.Many2one('account.account', string=u'Compte de crédit IR')
    journal_id = fields.Many2one('account.journal', string=u'Journal')
    salary_credit_account_id = fields.Many2one('account.account', string=u'Compte de crédit')
    salary_debit_account_id = fields.Many2one('account.account', string=u'Compte de débit')
    #   analytic_account_id = fields.Many2one('account.analytic.account', string='Compte analytique')
    salaire_max_logement_social = fields.Float("Salaire max", default=3000)
    superficie_max_logement_social = fields.Float(u"Superficie max (m²)", default=80)
    prix_achat_max_logement_social = fields.Float("Prix d'achat max", default=300000)
