# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api, _

import odoo.addons.decimal_precision as dp

from odoo.addons.l10n_ma_hr_payroll.models.variables import *

class payroll_statistics_report(models.Model):
    _name = "hr.payroll.statistics.report"
    _description = "Statistique de paie"
    _auto = False
    _rec_name = 'slip_period_id'
    _order = 'slip_period_id desc'

    slip_period_id = fields.Many2one('date.range', string=u'Période',)
    slip_fiscalyear_id = fields.Many2one(
        'date.range.type', string=u'Année',)
    nbr = fields.Integer(string=u'Nombre de lignes',)
    code = fields.Char(string=u'Code', size=64,)

    employee_id = fields.Many2one('hr.employee', string=u'Employé',)
    contract_id = fields.Many2one('hr.contract', string=u'Contrat',)
    based_on = fields.Selection(BASED_ON_SELECTION, string=u'Basé sur', )

    contract_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('occasional', 'Occasionnel'),
        ('trainee', 'Stagiaire'),
    ], string=u'Type',)

    total = fields.Float(string=u'Total', digits=dp.get_precision('Account'),)
    quantity = fields.Float(string=u'Quantité', digits=dp.get_precision('Account'),)
    rate = fields.Float(string=u'Taux', digits=dp.get_precision('Account'),)
    base = fields.Float(string=u'Base', digits=dp.get_precision('Account'),)

    name = fields.Char(string=u'Nom', size=64,)

    category_id = fields.Many2one(
        'hr.salary.rule.category', string=u'Catégorie',)
    category_code = fields.Char(string=u'Code de la catégorie', size=64,)

    category = fields.Selection([
        ('none', 'Autre'),
        ('gs', 'Gain salariale'),
        ('rs', 'Retenu salariale'),
        ('gp', 'Gain patronale'),
        ('rp', 'Retenu patronale'),
    ], string=u'Type de la catégorie', required=False, )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('verify', 'À vérifier'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string=u'État',)

    rubrique_id = fields.Many2one('hr.rubrique', string=u'Rubrique',)
    avance_id = fields.Many2one('hr.avance', string=u'Avance',)
    avantage_id = fields.Many2one('hr.avantage', string=u'Avantage',)
    cotisation_id = fields.Many2one('hr.cotisation', string=u'Cotisation',)
    holiday_status_id = fields.Many2one(
        'hr.holidays.status', string=u'Type de congé',)

    register_id = fields.Many2one(
        'hr.contribution.register', string=u'Registre de contribution',)

    voucher_mode = fields.Selection([
        ('ES', u'Espèces'),
        ('CH', u'Chèque'),
        ('VIR', u'Virement'),
    ], string=u'Mode de règlement',)
    job_id = fields.Many2one('hr.job', string=u'Poste',)
    department_id = fields.Many2one('hr.department', string=u'Département',)
    voucher_date = fields.Date(string=u'Date de versement',)
    company_id = fields.Many2one('res.company', string=u'Société',  )

    def _select(self):
        select_str = """
             SELECT min(l.id) as id,
                    l.code as code,
                    s.rubrique_id as rubrique_id,
                    s.avance_id as avance_id,
                    s.avantage_id as avantage_id,
                    s.cotisation_id as cotisation_id,
                    s.holiday_status_id as holiday_status_id,
                    categ.code as category_code,
                    sum(l.total) as total,
                    l.name as name,
                    e.department_id as department_id,
                    c.job_id as job_id,
                    p.state as state,
                    p.voucher_mode as voucher_mode,
                    p.voucher_date as voucher_date,
                    p.company_id as company_id,
                    sum(l.quantity) as quantity,
                    avg(l.rate) as rate,
                    sum(l.amount) as base,
                    p.slip_period_id as slip_period_id,
                    p.slip_fiscalyear_id as slip_fiscalyear_id,
                    p.employee_id as employee_id,
                    p.contract_id as contract_id,
                    c.based_on as based_on,
                    t.type as contract_type,
                    l.category_id as category_id,
                    categ.category as category,
                    l.register_id as register_id,
                    count(*) as nbr
        """
        return select_str

    def _from(self):
        from_str = """
                hr_payslip_line l
                      join hr_payslip p on (l.slip_id=p.id)
                        left join hr_employee e on (p.employee_id=e.id)
                            left join hr_contract c on (p.contract_id=c.id)
                    left join hr_salary_rule s on (l.salary_rule_id=s.id)
                    left join hr_contract_type t on (c.type_id=t.id)
                    left join hr_salary_rule_category categ on (l.category_id=categ.id)
                    left join hr_contribution_register register on (l.register_id=register.id)
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY l.code,
                    s.rubrique_id,
                    s.avantage_id,
                    s.avance_id,
                    s.cotisation_id,
                    s.holiday_status_id,
                    categ.code,
                    l.total,
                    p.state,
                    l.name,
                    p.voucher_mode,
                    p.voucher_date,
                    p.company_id,
                    e.department_id,
                    c.job_id,
                    l.register_id,
                    p.slip_period_id,
                    p.slip_fiscalyear_id,
                    p.employee_id,
                    p.contract_id,
                    l.category_id,
                    categ.category,
                    c.based_on,
                    t.type
        """
        return group_by_str
    
    @api.model_cr
    def init(self):
        cr = self._cr
        # self._table = sale_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))
