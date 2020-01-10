# -*- coding: utf-8 -*-
from odoo import fields, models, api, osv
from . import convertion


class ResCompany(models.Model):
    _inherit = 'res.company'

    banque_virement_paie = fields.Char(string='Banque')
    agence_virement_paie = fields.Char(string='Agence')
    ville_agence_virement_paie = fields.Char(string='Ville agence')
    rib_virement_paie = fields.Char(string=u'RIB')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    banque_virement_paie = fields.Char(string='Banque', related="company_id.banque_virement_paie", readonly=False)
    agence_virement_paie = fields.Char(string='Agence', related="company_id.agence_virement_paie", readonly=False)
    ville_agence_virement_paie = fields.Char(string='Ville agence', related="company_id.ville_agence_virement_paie",
                                             readonly=False)
    rib_virement_paie = fields.Char(string='RIB', related="company_id.rib_virement_paie", readonly=False)
