# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class hr_contract_base(models.Model):
    _name = 'hr.contract.base'
    _description = 'Contrats de base'

    name = fields.Char(string=u'Nom', size=64, required=True,)
    code = fields.Char(string=u'Code', size=64, required=True,)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)',
         'Le code du contrat doit être unique !'),
    ]
