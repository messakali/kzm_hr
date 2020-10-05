# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo import api
from odoo.tools.translate import _
from datetime import datetime
from odoo import exceptions

class kzm_hr_pointeuse_load_attendance(models.Model):

    _name = 'kzm.hr.pointeuse.load.attendance'
    _description = 'Une description'

    pointeuse_ids = fields.Many2one(comodel_name="kzm.hr.pointeuse", string=_("Pointeuse"), required=True,)
    company_id = fields.Many2one(comodel_name="res.company", ondelete='cascade', string=_("Society"),
                                 required=True,
                                 default=lambda self: self.env.company)


    
    def load_attendance(self):
        self.sudo().pointeuse_ids.load_attendance()


    def check_pointeuse_periodic(self):
        pointeuse_ids = self.env['kzm.hr.pointeuse'].search([('active', '=', True)])
        for p in pointeuse_ids:
            p.load_attendance_from_cron()

