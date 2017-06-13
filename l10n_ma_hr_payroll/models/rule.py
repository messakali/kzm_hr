# encoding: utf-8

from odoo import models, fields, api, _
from odoo.exceptions import Warning
import odoo.addons.decimal_precision as dp
import math
from dateutil.relativedelta import relativedelta

from odoo.tools.safe_eval import safe_eval as eval

from datetime import datetime
from datetime import timedelta

import logging
_logger = logging.getLogger(__name__)

PARENT = '_PARENT'


class hr_salary_rule(models.Model):
    _inherit = 'hr.salary.rule'

    code = fields.Char()
    rubrique_id = fields.Many2one('hr.rubrique', string=u'Rubrique',)
    avance_id = fields.Many2one('hr.avance', string=u'Avance',)
    avantage_id = fields.Many2one('hr.avantage', string=u'Avantage',)
    cotisation_id = fields.Many2one('hr.cotisation', string=u'Cotisation',)
    holiday_status_id = fields.Many2one(
        'hr.holidays.status', string=u'Type de congé',)
    is_salary_item = fields.Boolean(string=u'Élément de salaire', default=False,)

    @api.one
    @api.depends("show_on_payslip")
    def _compute_appears_on_payslip(self):
        if not self.show_on_payslip:
            self.appears_on_payslip = False
        elif self.show_on_payslip == 'never':
            self.appears_on_payslip = False
        else:
            self.appears_on_payslip = True

    appears_on_payslip = fields.Boolean(
        string=u'Affichage sur les bulletins',  compute='_compute_appears_on_payslip', store=True,)

    @api.one
    @api.constrains('code', 'avance_id', 'avantage_id', 'rubrique_id', 'cotisation_id')
    def _check_code(self):
#         print self
#         print self.code
        if self.search_count([('code', '=', self.code)]) > 1:
            raise Warning(
                _('The code [%s] is already exist') % self.code.replace(PARENT, ''))
        tab = [x for x in [self.rubrique_id, self.avance_id,
                           self.avantage_id, self.cotisation_id, self.holiday_status_id] if x]
        if len(tab) > 1:
            raise Warning(
                _('The rule can be attached to one element (Avance, Avantage, Cotisation ou Rubrique)'))

    base_val = fields.Char(
        string=u'Valeur de base',
        size=1024,
        help='Base en expression python')
    rate_val = fields.Char(
        string=u'Valeur de pourcentage',
        size=1024,
        default='100',
        help='Poucentage en expression python\nUtiliser 100 for 100%')

    amount_select = fields.Selection(
        selection_add=[('flexible_percentage', 'Pourcentage flexible')])

    show_on_payslip = fields.Selection([
        ('never', 'Jamais'),
        ('ifnotnull', 'Si différent du zéro'),
        ('always', 'Toujours'),
    ], string=u'Affichage sur les bulletins', required=True, default='ifnotnull')

    auto = fields.Boolean(string=u'Créé automatiquement', default=False)

    def compute_rule(self, localdict):

        def get_majoration_net(p):
            if p.simulation_ok:
                if not p.simulate_elements_ok:
                    return 0.0
            somme = 0.0
            # Notes de frais
            line_obj = self.env['hr.expense']
            domain = [
                ('state', '=', 'paid'),
                ('payroll_type', '=', 'majoration_net'),
                ('employee_id', '=', p.employee_id),
                ('payroll_date', '<=', p.date_to),
                ('payroll_date', '>=', p.date_from),
            ]
            line_ids = line_obj.search(domain)
            lines = line_ids
            somme += sum([x.total_amount for x in lines])
            return somme

        def get_retenu_net(p):
            if p.simulation_ok:
                if not p.simulate_elements_ok:
                    return 0.0
            somme = 0.0
            # Notes de frais
            line_obj = self.env['hr.expense']
            domain = [
                ('state', '=', 'paid'),
                ('payroll_type', '=', 'retenu_net'),
                ('employee_id', '=', p.employee_id),
                ('payroll_date', '<=', p.date_to),
                ('payroll_date', '>=', p.date_from),
            ]
            line_ids = line_obj.search(domain)
            lines = line_ids
            somme += sum([x.total_amount for x in lines])
            return somme

        def get_rubrique(p, code):
            if p.simulation_ok:
                if not p.simulate_elements_ok:
                    return 0.0
            somme = 0.0
            # Rubrique
            line_obj = self.env['hr.rubrique.line']
            # Domain linked to saisie.py
            domain = line_obj.get_domain(employee_id=p.employee_id, state='done', code=code, date_start=p.date_from, date_end=p.date_to)
            lines = line_obj.search(domain)
            for line in lines:
                somme += line.amount
                # FIXME RELATE ME TO SAISIE.PY AND TRANSLATE ALL TO DOMAIN
            # Notes de frais
            line_obj = self.env['hr.expense']
            domain = [
                ('state', '=', 'paid'),
                ('rubrique_id.code', '=', code),
                ('employee_id', '=', p.employee_id),
                ('payroll_date', '<=', p.date_to),
                ('payroll_date', '>=', p.date_from),
            ]
            line_ids = line_obj.search(domain)
            lines = line_ids
            somme += sum([x.total_amount for x in lines])
            return somme

        def get_avance(p, code, is_interest, categories, inputs):
            if p.simulation_ok:
                if not p.simulate_elements_ok:
                    return 0.0
            plafond = False
            rate = False
            if is_interest:
                localdict = {
                    'categories': categories,
                    'inputs': inputs,
                    'self': self,
                }
                expression_id = self.search(
                    [('code', '=', 'NET_IMPOSABLE')], limit=1)
                expression = expression_id
                expression = expression and expression.amount_python_compute or False
                eval(expression, localdict, mode='exec', nocopy=True)
                result = 'result' in localdict and localdict['result'] or 0.0
                plafond = result
            somme = 0.0
            # Avances
            line_obj = self.env['hr.avance.line.line']
            # Domain linked to saisie.py
            domain = [
                ('state', '=', 'done'),
                ('avance_line_id.code', '=', code),
                ('avance_line_id.employee_id', '=', p.employee_id),
                ('date', '>=', p.date_from),
                ('date', '<=', p.date_to),
            ]
            line_ids = line_obj.search(domain)
            lines = line_ids
            somme += sum([x.amount for x in lines])
            # Rates
            for line in lines:
                rate = line.avance_line_id.avance_id.interest_rate
                break
            # Notes de frais
            line_obj = self.env['hr.expense']
            domain = [
                ('state', '=', 'paid'),
                ('avance_id.code', '=', code),
                ('employee_id', '=', p.employee_id),
                ('payroll_date', '<=', p.date_to),
                ('payroll_date', '>=', p.date_from),
            ]
            line_ids = line_obj.search(domain)
            lines = line_ids
            somme += sum([x.total_amount for x in lines])
            if rate and plafond:
                if somme > plafond * rate / 100.:
                    return plafond * rate / 100.
            return somme

        def get_avantage(p, code):
            if p.simulation_ok:
                if not p.simulate_elements_ok:
                    return 0.0
            somme = 0.0
            line_obj = self.env['hr.avantage.line']
            # Domain linked to Saisie.py
            domain = [
                ('state', '=', 'done'),
                ('code', '=', code),
                ('employee_id', '=', p.employee_id),
                '|',
                '|',
                '&',
                ('date_start', '>=', p.date_from),
                ('date_start', '<=', p.date_to),
                '&',
                ('date_end', '>=', p.date_from),
                ('date_end', '<=', p.date_to),
                '&',
                ('date_start', '<=', p.date_from),
                ('date_end', '>=', p.date_to),
            ]
            line_ids = line_obj.search(domain)
            lines = line_ids
            somme += sum([x.amount for x in lines])
            # Notes de frais
            line_obj = self.env['hr.expense']
            domain = [
                ('state', '=', 'paid'),
                ('avantage_id.code', '=', code),
                ('employee_id', '=', p.employee_id),
                ('payroll_date', '<=', p.date_to),
                ('payroll_date', '>=', p.date_from),
            ]
            line_ids = line_obj.search(domain)
            lines = line_ids
            somme += sum([x.total_amount for x in lines])
            return somme

        def get_fp(inputs, base):
            res = base * (inputs.FP_TAUX.amount / 100.)
            if res > inputs.FP_PLAFOND.amount:
                return inputs.FP_PLAFOND.amount
            else:
                return res

        def get_cf(inputs, employee):
            if inputs.CF_PLAFOND.amount > (inputs.NBR_PERSONNE_CHARGE.amount * inputs.CF_MONTANT.amount) or inputs.CF_PLAFOND.amount <= 0:
                return inputs.NBR_PERSONNE_CHARGE.amount * inputs.CF_MONTANT.amount
            else:
                return inputs.CF_PLAFOND.amount

        def get_af(employee):
            nbr = employee.nbr_children_af
            company = employee.company_id
            first_part = nbr >= company.nbr_af1_plafond and company.nbr_af1_plafond or nbr
            tmp_part = nbr >= company.nbr_af2_plafond and (
                company.nbr_af2_plafond - first_part) or (nbr - first_part)
            second_part = nbr >= first_part and tmp_part or 0
            total = first_part * company.af1_amount + \
                second_part * company.af2_amount
            nbr2 = nbr >= company.nbr_af2_plafond and company.nbr_af2_plafond or nbr
            return nbr2, nbr2 > 0 and float(total) / nbr2 or 0

        def get_ir_report(p):
            if p.simulation_ok:
                return 0.0
            m1days = timedelta(days=-1)
            m1months = relativedelta(months=-1)
            last_slip_date_to = datetime.strptime(
                p.date_from, "%Y-%m-%d") + m1days
            last_slip_date_from = datetime.strptime(
                p.date_from, "%Y-%m-%d") + m1months
            last_slip_date_to = last_slip_date_to.strftime("%Y-%m-%d")
            last_slip_date_from = last_slip_date_from.strftime("%Y-%m-%d")
            return self.env['hr.dictionnary'].compute_value(
                    code="IR_NET_REPORT",
                    year_of_date=last_slip_date_to,
                    date_start=last_slip_date_from,
                    date_stop=last_slip_date_to,
                    employee_id=p.employee_id,
                    company_id=p.company_id.id
            )


        def get_ir(p, categories, base, base_code):
            if p.contract_id.type_id.type == 'occasional':
                occasionel_ir = self.env['ir.config_parameter'].get_param(
                    'ir_occasionel', '0')
                occasionel_ir_taux = float(occasionel_ir)/100
                if occasionel_ir_taux:
                    return occasionel_ir_taux * categories.BRUT_IMPOSABLE
            reg_ok = self.env['ir.config_parameter'].get_param(
                'ir_reg', '0') == '1' and True or False
            if not reg_ok or p.simulation_ok:
                return self.env['hr.scale.ir'].get_ir(base, 1)
            based_on_days = p.contract_id.based_on_days
            nbr = self.env['hr.payslip'].search_count([
                ('state', '=', 'done'),
                ('employee_id', '=', p.employee_id),
                ('date_from', '>=', p.date_from[:4] + '-01-01'),
                ('date_to', '<', p.date_from),
                ('company_id', '=', p.company_id.id)
            ]) * 1.0 + 1
            if nbr == 1:
                return self.env['hr.scale.ir'].get_ir(base, 1)
            m1days = timedelta(days=-1)
            last_slip_date_to = datetime.strptime(
                p.date_from, "%Y-%m-%d") + m1days
            last_slip_date_to = last_slip_date_to.strftime("%Y-%m-%d")
            cumul_ir_value = self.env['hr.dictionnary'].compute_value(
                code="IR_BRUT",
                year_of_date=last_slip_date_to,
                date_stop=last_slip_date_to,
                employee_id=p.employee_id,
                company_id=p.company_id.id
            )
            cumul_net_imposable_value = self.env['hr.dictionnary'].compute_value(
                code=base_code,
                year_of_date=last_slip_date_to,
                date_stop=last_slip_date_to,
                employee_id=p.employee_id,
                company_id=p.company_id.id
            )
            if based_on_days:
                cumul_worked_days = self.env['hr.dictionnary'].compute_value(
                    code="NBR_JOURS",
                    year_of_date=last_slip_date_to,
                    date_stop=last_slip_date_to,
                    employee_id=p.employee_id,
                    company_id=p.company_id.id
                ) + categories.PERIODE_JOURS
                nbr_days_declared = p.company_id.main_company_id.nbr_days_declared
                cumul_fullfill = cumul_worked_days > 0 and (base + cumul_net_imposable_value) * \
                    (nbr_days_declared * 12) / cumul_worked_days or 0.0
                required_ir_value = self.env[
                    'hr.scale.ir'].get_ir(cumul_fullfill, nbr=12)
                required_ir_value *= cumul_worked_days / \
                    (nbr_days_declared * 12)
            else:
                cumul_worked_hours = self.env['hr.dictionnary'].compute_value(
                    code="NBR_HEURES",
                    year_of_date=last_slip_date_to,
                    date_stop=last_slip_date_to,
                    employee_id=p.employee_id,
                    company_id=p.company_id.id
                ) + categories.PERIODE_HEURES
                nbr_hours_declared = p.company_id.main_company_id.nbr_hours_declared
                cumul_fullfill = cumul_worked_hours > 0 and (base + cumul_net_imposable_value) * \
                    (nbr_hours_declared * 12) / cumul_worked_hours or 0.0
                required_ir_value = self.env[
                    'hr.scale.ir'].get_ir(cumul_fullfill, nbr=12)
                required_ir_value *= cumul_worked_hours / \
                    (nbr_hours_declared * 12)
            computed_ir_value = required_ir_value - cumul_ir_value
            return computed_ir_value

        def get_cs(p, categories, base, base_code):
            reg_ok = self.env['ir.config_parameter'].get_param(
                'css_reg', '0') == '1' and True or False
            if not reg_ok:
                return self.env['hr.scale.solidarity'].get_solidarity(base, 1)
            based_on_days = p.contract_id.based_on_days
            nbr = self.env['hr.payslip'].search_count([
                ('state', '=', 'done'),
                ('employee_id', '=', p.employee_id),
                ('date_from', '>=', p.date_from[:4] + '-01-01'),
                ('date_to', '<', p.date_from),
                ('company_id', '=', p.company_id.id)
            ]) * 1.0 + 1
            if nbr == 1:
                return self.env['hr.scale.solidarity'].get_solidarity(base, nbr)
            m1days = timedelta(days=-1)
            last_slip_date_to = datetime.strptime(
                p.date_from, "%Y-%m-%d") + m1days
            last_slip_date_to = last_slip_date_to.strftime("%Y-%m-%d")
            cumul_solidarity_value = self.env['hr.dictionnary'].compute_value(
                code="CONTRIBUTION_SOLIDARITE",
                year_of_date=p.date_from,
                date_start=p.date_from[:4] + '-01-01',
                date_stop=last_slip_date_to,
                employee_id=p.employee_id,
                company_id=p.company_id.id
            )
            cumul_net_contractuel = self.env['hr.dictionnary'].compute_value(
                code=base_code,
                year_of_date=p.date_from,
                date_start=p.date_from[:4] + '-01-01',
                date_stop=last_slip_date_to,
                employee_id=p.employee_id,
                company_id=p.company_id.id
            )
            if based_on_days:
                cumul_worked_days = self.env['hr.dictionnary'].compute_value(
                    code="NBR_JOURS",
                    year_of_date=last_slip_date_to,
                    date_stop=last_slip_date_to,
                    employee_id=p.employee_id,
                    company_id=p.company_id.id
                ) + categories.PERIODE_JOURS
                nbr_days_declared = p.company_id.main_company_id.nbr_days_declared
                cumul_fullfill = cumul_worked_days > 0 and (base + cumul_net_contractuel) * \
                    (nbr_days_declared * 12) / cumul_worked_days or 0.0
                required_cs_value = self.env[
                    'hr.scale.solidarity'].get_solidarity(cumul_fullfill, nbr=12)
                required_cs_value *= cumul_worked_days / \
                    (nbr_days_declared * 12)
            else:
                cumul_worked_hours = self.env['hr.dictionnary'].compute_value(
                    code="NBR_HEURES",
                    year_of_date=last_slip_date_to,
                    date_stop=last_slip_date_to,
                    employee_id=p.employee_id,
                    company_id=p.company_id.id
                ) + categories.PERIODE_HEURES
                nbr_hours_declared = p.company_id.main_company_id.nbr_hours_declared
                cumul_fullfill = cumul_worked_hours > 0 and (base + cumul_net_contractuel) * \
                    (nbr_hours_declared * 12) / cumul_worked_hours or 0
                required_cs_value = self.env[
                    'hr.scale.solidarity'].get_solidarity(cumul_fullfill, nbr=12)
                required_cs_value *= cumul_worked_hours / \
                    (nbr_hours_declared * 12)
            computed_cs_value = required_cs_value - cumul_solidarity_value
            return computed_cs_value

        def compute_arrondi(base, standard=2, n=1):
            base = round(base, standard)
            """ if given 4355.89 and n=0.1
            basee * n = 435.589 => ceil : 436
            So res/n => 4360
            left = 4360 - 4355.89 = 4.11
            if given 4355.89 and n=1, left = 0.11
            """
            left = math.ceil(base * n) / n - base
            return left

        def get_plafond_ind_kilometrique(payslip):
            plafond = 0
            cvs = self.env['hr.employee.km'].get_cvs(payslip.employee_id, payslip.date_from, payslip.date_to)
            for cv in cvs:
                rate = self.env['hr.scale.km'].get_km_rate(cv)
                km, tmp = self.env['hr.employee.km'].get_km_cv(payslip.employee_id, payslip.date_from, payslip.date_to, cv=cv)
                plafond += km * rate
            return plafond

        localdict.update({
            'majoration_net': get_majoration_net,
            'retenu_net': get_retenu_net,
            'rubrique': get_rubrique,
            'avance': get_avance,
            'avantage': get_avantage,
            'fp': get_fp,
            'ir': get_ir,
            'ir_report': get_ir_report,
            'cs': get_cs,
            'cf': get_cf,
            'af': get_af,
            'plafond_ind_kilometrique': get_plafond_ind_kilometrique,
            'arrondi': compute_arrondi,
        })
        rule = self
        use_try = True
        if not use_try:
            _logger.info('Compute code [%s] defined for salary rule [%s] with compute method [%s]', rule.name, rule.code, rule.amount_select)
            if rule.amount_select == 'flexible_percentage':
                return eval(rule.base_val, localdict), eval(rule.quantity, localdict), eval(rule.rate_val, localdict)
            elif rule.amount_select == 'fix':
                return rule.amount_fix, float(eval(rule.quantity, localdict)), 100.0
            elif rule.amount_select == 'percentage':
                return (float(eval(rule.amount_percentage_base, localdict)),
                            float(eval(rule.quantity, localdict)),
                            rule.amount_percentage)
            else:
                eval(rule.amount_python_compute, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), 'result_qty' in localdict and localdict['result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
        
        if rule.amount_select == 'flexible_percentage':
            try:
#                 print "koko",localdict['inputs'].SALAIRE_PAR_JOUR
#                 print "flexible_percentage",rule.base_val
#                 print "flexible_percentage",rule.quantity,localdict['worked_days'].DECLARED
#                 print "flexible_percentage",rule.rate_val,eval(rule.rate_val, localdict)
                return eval(rule.base_val, localdict), eval(rule.quantity, localdict), eval(rule.rate_val, localdict)
            except:
                raise Warning(
                    _('Erreur dans l\'expression python défini pour la règle de salaire %s (%s).') % (rule.name, rule.code))
        elif rule.amount_select == 'fix':
            try:
#                 print "fix"
                return rule.amount_fix, float(eval(rule.quantity, localdict)), 100.0
            except:
                raise Warning(
                _('Erreur dans la quantité défini pour la règle de salaire %s (%s).')% (rule.name, rule.code))
        elif rule.amount_select == 'percentage':
            try:
#                 print "percentage"
                return (float(eval(rule.amount_percentage_base, localdict)),
                        float(eval(rule.quantity, localdict)),
                        rule.amount_percentage)
            except:
                raise Warning(
                _('Erreur de pourcentage de base ou la quantité défini pour la règle de salaire %s (%s).')% (rule.name, rule.code))
        else:
            try:
#                 print "kokokok",rule.amount_python_compute
                eval(rule.amount_python_compute, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), 'result_qty' in localdict and localdict['result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
            except:
                raise Warning(
                _('Erreur dans l\'expression python défini pour la règle de salaire %s (%s).')% (rule.name, rule.code))
