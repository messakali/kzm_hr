# encoding: utf-8

from odoo import models, fields, api, _



class hr_employee(models.Model):
    _inherit = 'hr.employee'

    @api.one
    def _compute_document_count(self):
        self.document_count = self.sudo().env['hr.document'].search_count(
            [('employee_id', '=', self.id)])
        
    @api.one
    def _compute_warning_count(self):
        self.warning_count = self.sudo().env['hr.employee.warning'].search_count(
            [('employee_id', '=', self.id)])
