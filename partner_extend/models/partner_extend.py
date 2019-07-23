# -*- encoding: utf-8 -*-

from odoo import models,fields, api


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    id_fisc = fields.Char(string=u'Identifiant Fiscal')
    rc = fields.Char(string=u'RC')
    cnss = fields.Char(string=u'Numéro de la sécurité sociale')
    capital_social = fields.Char(string=u'Capital social')
    ice = fields.Char(string=u'ICE')
    itp = fields.Char(string=u'Identifiant Taxe Professionnelle')
    activites = fields.Char(string=u"Profession ou activités exercées")
    nationalite = fields.Char(string=u"Nationalité")
    fax = fields.Char(string=u"Fax")