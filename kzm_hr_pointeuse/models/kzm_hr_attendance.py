# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class attendance(models.Model):
    # _inherit = 'hr.attendance'
    _name = "zk_attendance.attendance"
    _order = "date desc"
    active = fields.Boolean(string=_("Active"), default=True)
    company_id = fields.Many2one(comodel_name="res.company",
                                 string=_("Company"), related='machine_id.company_id', store=True)





    employee_id = fields.Many2one('hr.employee', string="Employee", store=True)
    machine_id = fields.Many2one('kzm.hr.pointeuse', string=_('Machine Name'),
                                 ondelete='cascade',
                                 required=False)
    matricule = fields.Char(string=_("Matricule"), store=True, related='employee_id.matricule')
    matricule_pointeuse = fields.Char(string=_("Matricule (P)"), required=False)
    note = fields.Char(string=_("Note"))
    # badge_id = fields.Many2one('kzm.hr.pointeuse.badge', string="Badge")
    date = fields.Datetime()
    # action = fields.Char(string=_("Action"))
    active = fields.Boolean(string=_("Active"), default=True)

    action = fields.Selection(string=_("Action"),
                              selection=[('sign_in', _('Sign In')), ('sign_out', _('Sign Out')), ],
                              )


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    # company_id = fields.Many2one(comodel_name="res.company",
    #                              string=_("Company"), )
    check_in_machine = fields.Char(string=_('Check in machine'), )
    check_out_machine = fields.Char(string=_('Check out machine'), )

    #== domaineDB
    active = fields.Boolean(string=_("Archivé"), default=True)
    company_id = fields.Many2one(comodel_name="res.company",
                                 string=_("Ferme"), related='pointeuse_id.company_id', store=True)



    # type_employe = fields.Selection(string='Type employe', related='employee_id.type_employe',
    #                                 # compute='compute_type_employe',
    #                                 store=True)
    pointeuse_id = fields.Many2one(comodel_name="kzm.hr.pointeuse", string=_("Pointeuse"),
                                   required=False, )
    matricule = fields.Char(string=_("Matricule"), store=True, related='employee_id.matricule')

    @api.constrains('employee_id')
    def check_contract(self):
        for r in self :
            if not r.employee_id.contract_id:
                raise UserError(_("Vous n'avez pas de contract en cours!"))



