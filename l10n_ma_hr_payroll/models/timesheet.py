# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class hr_timesheet(models.Model):
    _inherit = 'hr_timesheet_sheet.sheet'

    saisie_line_id = fields.Many2one('hr.saisie.line', string=u'Ligne de saisie',)

    @api.one
    def should_be_canceled(self):
        if self.state == 'done':
            self.action_set_to_draft()
        if self.state == 'confirm':
            self.signal_workflow('cancel')
