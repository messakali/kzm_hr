# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class hr_employee_qualification(models.Model):
    _name = 'hr.employee.qualification'
    _description = 'Qualification'

    name = fields.Char(string=u'Nom', size =  64 , required=True,  )