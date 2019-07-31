# -*- coding: utf-8 -*-
from odoo import fields, models,api, osv
from . import convertion


class payroll_parametres(models.Model):
    _inherit = 'hr.payroll_ma.parametres'

    banque_virement_paie = fields.Char(string='Banque')
    agence_virement_paie = fields.Char(string='Agence')
    ville_agence_virement_paie = fields.Char(string='Ville agence')
    rib_virement_paie = fields.Char(string=u'RIB')
