# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class hr_employee_task(models.Model):
    _name = 'hr.employee.task'
    _description = 'Task'


    name = fields.Char(string=u'Nom', size =  64 ,  required=True, )
