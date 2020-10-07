# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    matricule = fields.Char(string=_("Matricule"), required=False, )
    badge_ids = fields.One2many(comodel_name="kzm.hr.pointeuse.badge",
                                inverse_name="employee_id", string=_("Badges"),
                                required=False, readonly=False)



    def _attendance_access(self):
        # this function field use to hide attendance button to singin/singout from menu
        group = self.env['ir.model.data'].search([('module', '=', 'base'), ('name', '=', 'group_hr_manager')])
        visible = False
        if self.env.user.id in [user.id for user in group.users]:
            visible = True
        return dict([(x, visible) for x in self.ids])


    def create(slef, vals):
        res = super(HrEmployee, self).create(vals)
        for r in res:
            if r.matricule:
                r.matricule = r.matricule.zfill(5)
        return res
        
    def write(self, vals):
        if vals.get("matricule", False):
            vals['matricule'] = vals['matricule'].zfill(5)
        # for r in self:
        #     if len(r) == 1 and (not r.matricule or r.matricule == 'False'):
        #         vals['matricule'] = self.env['ir.sequence'].next_by_code('hr.employee.matricule')
        return super(HrEmployee, self).write(vals)


class HrContract(models.Model):
    _inherit = 'hr.contract'

    badge_ids = fields.One2many(comodel_name="kzm.hr.pointeuse.badge",
                                string=_("Badges"), related='employee_id.badge_ids')



