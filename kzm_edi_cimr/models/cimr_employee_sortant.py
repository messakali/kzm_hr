# -*- coding: utf-8 -*-

from odoo import fields, models,api


class CimrEmployeeSortant(models.Model):
    _name = 'cimr.employee.sortant'
    _inherit = ['mail.thread']

    name = fields.Selection(string="Trimestre", selection='get_quarters', required=True)
    cimr_sortant_line_ids = fields.One2many('cimr.employee.sortant.line', 'cimr_sortant_id',
                                             string=u'e_bds_sortant_line')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id,
                                 string='Société', readonly=True, copy=False)

    def get_quarters(self):
        return (
            ('1', u'1er Trimestre'),
            ('2', u'2ème Trimestre'),
            ('3', u'3ème Trimestre'),
            ('4', u'4ème Trimestre')
        )


class CimrEmployeeSortantLine(models.Model):
    _name = 'cimr.employee.sortant.line'
    _description = 'Cimr Employee Sortant Line'

    cimr_sortant_id = fields.Many2one('cimr.employee.sortant', u'Cimr employee sortant')
    employee_id = fields.Many2one('hr.employee', string=u'Employé', required=True)
