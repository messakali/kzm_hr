# -*- coding: utf-8 -*-

from odoo import models, fields
import datetime
from odoo.tools.translate import _
from odoo import api
from odoo.exceptions import ValidationError

class kzm_hr_pointeuse_connection(models.Model):
    _name = 'kzm.hr.pointeuse.connection'
    _rec_name = 'date'
    _description = 'Une Description'
    date = fields.Datetime(string=_("Date vérification"), readonly=True, default=datetime.datetime.now())
    company_id = fields.Many2one(comodel_name="res.company", ondelete='cascade', string=_("Society"),
                                 required=True,
                                 default=lambda self: self.env.company)



    def check_connection(self):
        pointeuse_ids = self.env['kzm.hr.pointeuse'].search([('active', '=', True)])
        messages = pointeuse_ids.check_connection()
        raise ValidationError(messages)
