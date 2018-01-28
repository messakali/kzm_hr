# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrContractBase(models.Model):
    _name = 'hr.contract.base'
    _description = 'Contrats de base'

    name = fields.Char(string=u'Nom', size=64, required=True,)
    code = fields.Char(string=u'Code', size=64, required=True,)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)',
         'Le code du contrat doit être unique !'),
    ]

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        context = self._context or {}
        if context.get('default_values'):
            args += [('id', 'in', self.env.user.company_id.based_on_ids.ids)]
        return super(HrContractBase, self)._search(args, offset=offset, limit=limit, order=order,
                                    count=count, access_rights_uid=access_rights_uid)
