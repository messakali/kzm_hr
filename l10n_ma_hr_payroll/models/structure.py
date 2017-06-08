# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class hr_payroll_structure(models.Model):
    _inherit = 'hr.payroll.structure'

    advantages = fields.Text(string=u'Description de la structure',)
    cimr_ok = fields.Boolean(string=u'CIMR',)
    cnss_ok = fields.Boolean(string=u'CNSS', )
    assurance_ok = fields.Boolean(string=u'Assurance retraite',)

    @api.multi
    def update_struct_fields(self):
        for obj in self:
            if obj.parent_id:
                obj.cimr_ok =  obj.parent_id.cimr_ok
                obj.cnss_ok = obj.parent_id.cnss_ok
                obj.assurance_ok = obj.parent_id.assurance_ok
            else:
                obj.cimr_ok =  False
                obj.cnss_ok =  False
                obj.assurance_ok =  False

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        self.update_struct_fields()
