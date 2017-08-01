# encoding: utf-8

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.addons.kzm_base.controllers.tools import date_range

import time

import logging
_logger = logging.getLogger(__name__)
from openerp.exceptions import Warning

def transform_domain_to_where_tab(domain, tuples={}, preferred_prefix=''):
    tab = []
    for (field, operator, value) in domain:
        prefix = False
        if field and '.' in field:
            prefix = '.'.join(field.split('.')[:-1])
            field = field.split('.')[-1]
            if not prefix in tuples.keys():
                _logger.error('the dictionnary can not manage the transformation of %s', tuples)
                raise Warning(_('Please contact the administrator'))
            else:
                prefix = tuples.get(prefix)
        if prefix:
            field = "%s.%s" % (prefix, field)
        if '.' not in field:
            field = "%s.%s" % (preferred_prefix, field)
        if isinstance(value, basestring):
            value = "'%s'" % value
        if hasattr(value, '__iter__'):
            if not value:
                field, operator, value = '1', '<>', '1'
            else:
                value = "%s" % str(tuple(value))
        if isinstance(value, basestring):
            value = value.replace(',)', ')')
        if isinstance(value, bool):
            value = str(value).upper()
        tab.append("%s %s %s" % (field, operator, value))
    return tab

class hr_dictionnary(models.Model):
    _name = 'hr.dictionnary'
    _order = 'name asc'

    name = fields.Char(string=u'Code', size=64,  required=True)
    is_fixed = fields.Boolean(string=u'FIxe',  default=False)
    add_rule_ids = fields.Many2many(
        'hr.salary.rule', 'hr_dict_add_rule_rel', 'dict_id', 'rule_id', string=u'Ajouter les valeurs depuis',)
    remove_rule_ids = fields.Many2many(
        'hr.salary.rule', 'hr_dict_remove_rule_rel', 'dict_id', 'rule_id', string=u'Soustraire les valeurs depuis',)
    add_category_ids = fields.Many2many(
        'hr.salary.rule.category', 'hr_dict_add_category_rel', 'dict_id', 'category_id', string=u'Ajouter les valeurs depuis',)
    remove_category_ids = fields.Many2many(
        'hr.salary.rule.category', 'hr_dict_remove_category_rel', 'dict_id', 'category_id', string=u'Soustraire les valeurs depuis',)

    based_on = fields.Selection([
        ('rule', 'Règle'),
        ('category', 'Catégorie'),
    ], string=u'Basé sur', default='rule', required=True)
    type = fields.Selection([
        ('total', 'Total'),
        ('amount', 'Base'),
        ('rate', 'Taux'),
        ('quantity', 'Quantité'),
    ], string=u'Type',)

    force_not_null = fields.Boolean(string=u'Forcer le total nul', default=False,)
    description = fields.Text(string=u'Utilisation',)

    operator = fields.Selection([
        ('sum', 'SUM'),
        ('avg', 'AVG'),
        ('one', 'Une ligne'),
        ('count', 'Nombre de lignes'),
    ], string=u'Opérateur', default='sum', required=True, )

    _sql_constraints = [
        ('code_unique', 'UNIQUE (name)',
         'Le code doit être unique !'),
    ]

    @api.model
    def compute_value(
        self,
        code=None,
        year_of_date=None,
        month_of_date=None,
        date_start=None,
        date_stop=None,
        employee_id=None,
        contract_id=None,
        payslip_ids=False,
        department_ids=[],
        state='done',
        avance_id=None,
        avantage_id=None,
        cotisation_id=None,
        cotisation_group_id=None,
        cotisation_ledger_id=None,
        rubrique_id=None,
        holiday_status_id=None,
        force_type=None,
        category_type=None,
        category_code=None,
        just_category_code=None,
        rule_code=None,
        just_rule_code=None,
        company_id=None,
        contract_type=None,
        based_on=None,
        fixed_salary=None,
        payslip_domain=[],
        line_domain=[],
    ):
        """
        state can be : draft, verify, cancel or done
        contract_type can be : o (occasionnel), t/s (trainne), p (permanent)
        """
        DAYS = 'days'
        HOURS = 'hours'
        WHERE_TAB = transform_domain_to_where_tab(line_domain, preferred_prefix='line')
        FROM="""
            hr_payslip_line as line
            LEFT JOIN hr_payslip as slip ON line.slip_id = slip.id
            LEFT JOIN hr_salary_rule_category as category ON line.category_id = category.id
            LEFT JOIN hr_salary_rule as rule ON line.salary_rule_id = rule.id
            LEFT JOIN hr_employee as employee ON line.employee_id = employee.id
            LEFT JOIN hr_contract as contract ON line.contract_id = contract.id
            LEFT JOIN hr_contract_type as contract_type ON contract.type_id = contract_type.id
        """

        assert based_on in [None, DAYS, HOURS], _('Based on sould be in %s' % [None, DAYS, HOURS])
        assert code or avance_id or avantage_id or cotisation_id  or cotisation_group_id or cotisation_ledger_id or rubrique_id or holiday_status_id or category_code or rule_code, _(
            "The code/avance/avantage/cotisation/cotisation_group/cotisation_ledger/rubrique/holiday_status_id/category_code/rule_code is required for the function")
        dictionnary = False
        if code:
            dictionnary = self.search([('name', '=', code)])
#             print "dictionnary    : ",dictionnary
            assert dictionnary, _(
                "A dictionnary should be created for [%s]") % code
        assert force_type or dictionnary, _(
            "You should force a type (force_type in ['amount','rate','quantity','total'])")
        add_ids = []
        remove_ids = []
        domain = []
        log_msg = False
        if dictionnary:
            log_msg = "Code_%s" % code
            if dictionnary.based_on == 'category':
                add_categ_ids = [x.id for x in dictionnary.add_category_ids]
                add_categ_ids = [x.id for x in dictionnary.add_category_ids.search(
                    [('id', 'child_of', add_categ_ids)])]
                add_ids = [x.id for x in dictionnary.add_rule_ids.search(
                    []) if x.category_id.id in add_categ_ids]
                remove_categ_ids = [
                    x.id for x in dictionnary.remove_category_ids]
                remove_categ_ids = [x.id for x in dictionnary.add_category_ids.search(
                    [('id', 'child_of', remove_categ_ids)])]
                remove_ids = [x.id for x in dictionnary.add_rule_ids.search(
                    []) if x.category_id.id in remove_categ_ids]
            else:
                add_ids = [x.id for x in dictionnary.add_rule_ids]
                remove_ids = [x.id for x in dictionnary.remove_rule_ids]
        if category_code:
            log_msg = "Category_Code_%s" % category_code
            if isinstance(category_code, basestring):
                category_code = [category_code]
            category_id = self.env['hr.salary.rule.category'].search(
                [('code', 'in', category_code)])
            if not category_id:
                raise Warning(
                    _("No category found for the code %s") % category_code)
            add_ids = [x.id for x in self.env['hr.salary.rule'].search(
                [('category_id.code', 'in', category_code)])]
        if avance_id:
            log_msg = "Avance_%s" % avance_id
            if isinstance(avance_id, (long, int)):
                avance_id = [avance_id]
            add_ids = [x.id for x in self.env['hr.salary.rule'].search(
                [('avance_id', 'in', avance_id)])]
        if avantage_id:
            log_msg = "Avantage_%s" % avantage_id
            if isinstance(avantage_id, (long, int)):
                avantage_id = [avantage_id]
            add_ids = [x.id for x in self.env['hr.salary.rule'].search(
                [('avantage_id', 'in', avantage_id)])]
        if rubrique_id:
            log_msg = "Rubrique_%s" % rubrique_id
            if isinstance(rubrique_id, (long, int)):
                rubrique_id = [rubrique_id]
            add_ids = [x.id for x in self.env['hr.salary.rule'].search(
                [('rubrique_id', 'in', rubrique_id)])]
        if cotisation_id:
            log_msg = "Cotisation_%s" % cotisation_id
            if isinstance(cotisation_id, (long, int)):
                cotisation_id = [cotisation_id]
            add_ids = [x.id for x in self.env['hr.salary.rule'].search(
                [('cotisation_id', 'in', cotisation_id)])]
        if cotisation_group_id:
            log_msg = "Cotisation_group_%s" % cotisation_group_id
            if isinstance(cotisation_group_id, (long, int)):
                cotisation_group_id = [cotisation_group_id]
            add_ids = [x.id for x in self.env['hr.salary.rule'].search(
                [('cotisation_id.group_id', 'in', cotisation_group_id)])]
        if cotisation_ledger_id:
            log_msg = "Cotisation_ledger_%s" % cotisation_ledger_id
            if isinstance(cotisation_ledger_id, (long, int)):
                cotisation_ledger_id = [cotisation_ledger_id]
            add_ids = [x.id for x in self.env['hr.salary.rule'].search(
                [('cotisation_id.ledger_id', 'in', cotisation_ledger_id)])]
        if holiday_status_id:
            log_msg = "Holiday_Status_%s" % holiday_status_id
            if isinstance(holiday_status_id, (long, int)):
                holiday_status_id = [holiday_status_id]
            add_ids = [x.id for x in self.env['hr.salary.rule'].search(
                [('holiday_status_id', 'in', holiday_status_id)])]
        if rule_code:
            log_msg = "Rule_Code_%s" % rule_code
            if isinstance(rule_code, (long, int)):
                rule_code = self.env['hr.salary.rule'].browse(rule_code).code
            if isinstance(rule_code, basestring):
                rule_code = [rule_code]
            add_ids = [x.id for x in self.env['hr.salary.rule'].search(
                [('code', 'in', rule_code)])]
            if not add_ids:
                raise Warning(_('No rule code/id [%s] found') % rule_code)
        #END MANDATORY
        if just_category_code:
            log_msg = "Just_Category_Code_%s" % just_category_code
            if isinstance(just_category_code, basestring):
                just_category_code = [just_category_code]
            category_id = self.env['hr.salary.rule.category'].search(
                [('code', 'in', just_category_code)])
            if not category_id:
                raise Warning(
                    _("No category found for the code %s") % just_category_code)
            add_ids = list(set(add_ids) & set([x.id for x in self.env['hr.salary.rule'].search(
                [('category_id.code', 'in', just_category_code)])]))
        if just_rule_code:
            log_msg = "Just_Rule_Code_%s" % just_rule_code
            if isinstance(just_rule_code, (long, int)):
                just_rule_code = self.env['hr.salary.rule'].browse(just_rule_code).code
            if isinstance(just_rule_code, basestring):
                just_rule_code = [just_rule_code]
            add_ids = list(set(add_ids) & set([x.id for x in self.env['hr.salary.rule'].search(
                [('code', 'in', just_rule_code)])]))
        if state:
            if state != 'all':
                domain = [('state', '=', state)]
        if year_of_date:
            year = year_of_date[:4]
            domain.append(('date_to', '>=', year + '-01-01'))
            domain.append(('date_to', '<=', year + '-12-31'))
        if month_of_date:
            dt_from, dt_to = date_range(month_of_date)
            domain.append(('date_to', '>=', dt_from))
            domain.append(('date_to', '<=', dt_to))
        if date_start:
            domain.append(('date_to', '>=', date_start))
        if date_stop:
            domain.append(('date_to', '<=', date_stop))
        if employee_id:
            if not isinstance(employee_id, (int, long)):
                employee_id = employee_id.id
            domain.append(('employee_id', '=', employee_id))
        if contract_id:
            if not isinstance(contract_id, (int, long)):
                contract_id = contract_id.id
            domain.append(('contract_id', '=', contract_id))
        if isinstance(payslip_ids,(list, tuple, self.env['hr.payslip'].__class__)):
            if isinstance(payslip_ids, self.env['hr.payslip'].__class__):
                payslip_ids = [x.id for x in payslip_ids]
            domain.append(('id', 'in', payslip_ids))
        if department_ids:
            if not isinstance(department_ids, (list, tuple)):
                department_ids = [x.id for x in department_ids]
            domain.append(('department_id', 'in', department_ids))
        if company_id:
            if isinstance(company_id, (int, long)):
                company_id = [company_id]
            if not isinstance(company_id, (list, tuple)):
                company_id = [x.id for x in company_id]
            domain.append(('company_id', 'in', company_id))
        if contract_type:
            assert contract_type.lower().strip()[0] in ['o', 's', 't', 'p'], _(
                'Contract type shoul be start with [o/t/p/s]')
            contract_type = contract_type.lower().strip()[0]
            if contract_type == 'p':
                domain.append(('contract_id.type_id.type', '=', 'permanent'))
            if contract_type == 'o':
                domain.append(('contract_id.type_id.type', '=', 'occasionnel'))
            if contract_type in ['t', 's']:
                domain.append(('contract_id.type_id.type', '=', 'trainee'))
        if based_on:
            if based_on == HOURS:
                domain.append(('contract_id.based_on_days', '=', False))
            if based_on == DAYS:
                domain.append(('contract_id.based_on_days', '=', True))
        if fixed_salary is not None:
            if fixed_salary == True:
                domain.append(('contract_id.fixed_salary', '=', True))
            if fixed_salary == False:
                domain.append(('contract_id.fixed_salary', '=', False))
        domain+=payslip_domain
        WHERE_TAB += transform_domain_to_where_tab(domain, preferred_prefix='slip', tuples={
            'contract_id': 'contract',
            'contract_id.type_id': 'contract_type',
        })
        if not dictionnary or not dictionnary.force_not_null:
            WHERE_TAB.append('line.amount > 0')
        if category_type:
            WHERE_TAB.append("category.category = '%s'" % category_type)
        SELECT = " SUM(line.%s)  as res " % (force_type or dictionnary.type)
        if dictionnary and dictionnary.operator == 'avg':
            SELECT = " AVG(line.%s)  as res " % (force_type or dictionnary.type)
        if dictionnary and dictionnary.operator == 'count':
            SELECT = " COUNT(*) as res "
        domain_add = [('id', 'in', add_ids)]
        domain_remove = [('id', 'in', remove_ids)]
        #ADD
        WHERE_TAB_ADD = WHERE_TAB[:]
        WHERE_TAB_ADD += transform_domain_to_where_tab(domain_add, preferred_prefix='rule')
        WHERE_ADD = WHERE_TAB_ADD and " AND ".join(WHERE_TAB_ADD) or " 1=1 "
        sql_add = "SELECT %s FROM %s WHERE %s" % (SELECT, FROM, WHERE_ADD)
        #REMOVE
        WHERE_TAB_REMOVE = WHERE_TAB[:]
        WHERE_TAB_REMOVE += transform_domain_to_where_tab(domain_remove, preferred_prefix='rule')
        WHERE_REMOVE = WHERE_TAB_REMOVE and " AND ".join(WHERE_TAB_REMOVE) or " 1=1 "
        sql_remove = "SELECT (-1)*%s FROM %s WHERE %s" % (SELECT, FROM, WHERE_REMOVE)
        #Main SQL
        limit = dictionnary and dictionnary.operator == 'one' and " LIMIT 1 " or ''
        main_sql = "SELECT SUM(res) FROM ( %s UNION %s %s ) as tbl" % (sql_add, sql_remove, limit)
        self.env.cr.execute(main_sql)
        res = self.env.cr.fetchone()
        return res and res[0] or 0.0
