# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class hr_employee_rotation(models.Model):
    _name = 'hr.employee.rotation'
    _description = u'Rotation des employés'

    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé',  required=True, ondelete='cascade',)
    company_id = fields.Many2one(
        'res.company', string=u'Société',  required=True, )
    date = fields.Date(string=u'Date', required=True, )
    action = fields.Selection([
        ('trial_start', 'Date début de la période de test'),
        ('trial_end', 'Date fin de la période de test'),
        ('start', 'Entrée'),
        ('end', 'Sortie'),
    ], string=u'Action', required=True,)
