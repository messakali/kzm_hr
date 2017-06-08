# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class hr_salary_rule_category(models.Model):
    _inherit = 'hr.salary.rule.category'

    category = fields.Selection([
        ('none', 'Autre'),
        ('gs', 'Gain salariale'),
        ('rs', 'Retenu salariale'),
        ('gp', 'Gain patronale'),
        ('rp', 'Retenu patronale'),
    ], string=u'Catégorie', required=False, )
