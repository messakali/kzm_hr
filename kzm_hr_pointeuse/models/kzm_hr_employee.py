# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    # matricule = fields.Char(string=_("Matricule"), required=False, )
    badge_ids = fields.One2many(comodel_name="kzm.hr.pointeuse.badge",
                                inverse_name="employee_id", string=_("Badges"),
                                required=False, readonly=False)



    def _attendance_access(self):
        # this function field use to hide attendance button to singin/singout from menu
        #group = self.env['ir.model.data'].search([('module', '=', 'base'), ('name', '=', 'group_hr_manager')])
        visible = False
        if self.env.user.has_group('hr.group_hr_manager'):
            visible = True
        return dict([(x, visible) for x in self.ids])

    # @api.model
    # def create(self, vals):
    #     new_record = super(HrEmployee, self).create(vals)
    #     if not new_record.matricule:
    #         #new_record.matricule=self.env['ir.sequence'].next_by_code('hr.employee.matricule')
    #         new_record.write({})
    #     return new_record



    def write(self, vals):
        for r in self:
            # if len(r) == 1 and (not r.matricule or r.matricule == 'False' or len(r.matricule) < 5):
            #     vals['matricule'] = self.env['ir.sequence'].next_by_code('hr.employee.matricule')
            super(HrEmployee, self).write(vals)
            return True


class HrContract(models.Model):
    _inherit = 'hr.contract'

    badge_ids = fields.One2many(comodel_name="kzm.hr.pointeuse.badge",
                                string=_("Badges"), related='employee_id.badge_ids')

    sous_ferme_id = fields.Many2one(comodel_name="sub.farm",
                                    default=False, string=_("Sub farm"), required=False)
