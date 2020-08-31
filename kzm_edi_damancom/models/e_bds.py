# -*- coding: utf-8 -*-

from odoo import api, fields, models


class EBdsSortant(models.Model):
    _name = "e_bds.sortant"
    _inherit = ['mail.thread']

    name = fields.Many2one('date.range', string=u'Période',
                           domain="[('type_id.fiscal_period', '=', True)]", required=True)
    e_bds_sortant_line_ids = fields.One2many('e_bds.sortant.line', 'e_bds_sortant_id',
                                             string=u'e_bds_sortant_line')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company,
                                 string='Société', readonly=True, copy=False)


class EBdsSortantLine(models.Model):
    _name = "e_bds.sortant.line"
    _description = "e_bds Sortant Line"

    employee_id = fields.Many2one('hr.employee', string=u'Employé', required=True)
    situation = fields.Selection(selection=[('SO', 'Sortant'),
                                               ('DE', 'Decédé'),
                                               ('IT', 'Maternité'),
                                               ('IL', 'Maladie'),
                                               ('AT', 'Accident de Travail'),
                                               ('CS', 'Congé Sans salaire'),
                                               ('MS', 'Maintenu Sans Salaire'),
                                               ('MP', 'Maladie Professionnelle')], string=u'Situation')
    e_bds_sortant_id = fields.Many2one('e_bds.sortant', u'e_bds_sortant')


class HrPayrollMaBulletin(models.Model):
    _inherit = "hr.payroll_ma.bulletin" 

    normal = fields.Boolean(string=u'Normal')
