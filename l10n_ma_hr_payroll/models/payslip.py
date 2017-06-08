# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning
from odoo.addons.kzm_base.controllers.tools import fiscal_year_for as fyf
from variables import *

import time
import logging
_logger = logging.getLogger(__name__)

SPECIAL_CODE = ['NET']
SALARIALE = 'SALARIALE'
PATRONALE = 'PATRONALE'


class hr_payslip(models.Model):
    _inherit = ['hr.payslip', 'mail.thread', 'ir.needaction_mixin']
    _name = 'hr.payslip'

    department_id = fields.Many2one(
        'hr.department', string=u'Département', readonly=True, states={'draft': [('readonly', False)]})

    job_id = fields.Many2one(
        'hr.job', string=u'Poste', readonly=True, states={'draft': [('readonly', False)]})

    voucher_mode = fields.Selection([
        ('ES', 'Espèces'),
        ('CH', 'Chèque'),
        ('VIR', 'Virement'),
    ], string=u'Mode de règlement', required=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    voucher_date = fields.Date(string=u'Date de règlement', track_visibility='onchange')

    cimr_ok = fields.Boolean(
        string=u'CIMR', states={'draft': [('readonly', False)]}, readonly=True, )
    cnss_ok = fields.Boolean(
        string=u'CNSS', states={'draft': [('readonly', False)]}, readonly=True, )

    simulation_ok = fields.Boolean(string=u'Simulation',  default=False,  )
    simulate_elements_ok = fields.Boolean(string=u'Simulation des éléments de salair',  default=False )
    without_arrondi = fields.Boolean(string=u'Sans arrondi',  default=False )

    payslip_run_id = fields.Many2one(ondelete='cascade',   )

    @api.multi
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: browse record of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        contract_obj = self.env['hr.contract']
        clause = []
        #a contract is valid if it ends between the given dates
        clause_1 = ['&',('date_end', '<=', date_to),('date_end','>=', date_from)]
        #OR if it starts between the given dates
        clause_2 = ['&',('date_start', '<=', date_to),('date_start','>=', date_from)]
        #OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&',('date_start','<=', date_from),'|',('date_end', '=', False),('date_end','>=', date_to)]
        clause_final =  [('employee_id', '=', employee.id),'|','|'] + clause_1 + clause_2 + clause_3
        contract_ids = contract_obj.search(clause_final, order='date_start desc', limit=1)
        return [r.id for r in contract_ids]

    @api.multi
    def cancel_sheet(self):
        payslips = self.browse()
        for slip in payslips:
            if slip.solde_tout_compte_id:
                slip.solde_tout_compte_id.should_be_refused()
        self.write({'voucher_ok' : False})
        super(hr_payslip, self).cancel_sheet()

    @api.multi
    def compute_sheet(self):
        res = super(hr_payslip, self).compute_sheet()
        for payslip in self:
            payslip.compute_leave_params()
        return res

    @api.multi
    def process_sheet(self):
        for slip in self:
            days = hours =0.0
            for wd in slip.worked_days_line_ids:
                if wd.code == RESTE_CONGES_PAYES:
                    days = wd.number_of_days
                    hours = wd.number_of_hours
            if days or hours:
                holiday_obj = self.env['hr.holidays']
                holiday_status_obj = self.env['hr.holidays.status']
                holiday_line_obj = self.env['hr.holidays.line']
                legal_status_id = holiday_status_obj.search([('limit','=',False)], limit=1)
                if not legal_status_id:
                    raise Warning(_('Veuillez définir un type : congé légal'))
                holiday_id = slip.solde_tout_compte_id and slip.solde_tout_compte_id.id or False
                holiday_id = holiday_id or holiday_obj.create({
                    'name' : _('Solde de tout compte'),
                    'employee_id' : slip.employee_id.id,
                    'date_from': slip.date_to,
                    'date_to': slip.date_to,
                    'holiday_status_id' : legal_status_id[0],
                })
                #GET LINES
                holiday_line_ids = holiday_line_obj.search([('holiday_id','=', holiday_id)])
                #CLEAN LINES
                holiday_line_ids.unlink()
                #CREATE LINES
                holiday_line_obj.create({
                    'date' : slip.date_to,
                    'holiday_id' : holiday_id,
                    'hours':  hours,
                    'days': days,
                    'type': 'remove',
                })
                holiday_id.flush()
                holiday_id.should_be_validated()
                self.write([slip.id], {'solde_tout_compte_id' : holiday_id})
        standard = self.env['ir.config_parameter'].get_param(
            'paie_acc', '0') == '1'
        if not standard:
            return self.write({'paid': True, 'state': 'done'})
        else:
            return super(hr_payslip, self).process_sheet()

    voucher_ok = fields.Boolean(string=u'Règlement effectué', default=False, track_visibility='onchange')

    @api.one
    @api.depends("state", "voucher_ok")
    def _compute_state2(self):
        if self.state == 'done' and self.voucher_ok:
            self.state2 = 'paid'
        else:
            self.state2 = self.state

    state = fields.Selection(track_visibility='onchange')
    state2 = fields.Selection([
        ('draft', 'Brouillon'),
        ('verify', 'En attente de vérification'),
        ('done', 'Terminé'),
        ('paid', 'Terminé et payé'),
        ('cancel', 'Annulé'),
    ], 'État', readonly=True, copy=False, compute='_compute_state2', store=True, track_visibility='onchange')

    @api.multi
    def action_paid(self):
        self.ensure_one()
        if not self.voucher_date:
            raise Warning(_('Veuillez définir la date de règlement'))
        self.voucher_ok = True

    @api.multi
    def action_unpaid(self):
        self.ensure_one()
        #self.voucher_date = False
        self.voucher_ok = False

    @api.multi
    def reset_params(self):
        self.ensure_one()
        contract_id = self.contract_id and self.contract_id.id or False
        employee_id = self.employee_id and self.employee_id.id or False
        res = self.env['hr.payslip'].onchange_employee_id(
            self.date_from, self.date_to, employee_id, contract_id).get('value')
        worked_days_line_ids = res['worked_days_line_ids']
        input_line_ids = res['input_line_ids']
        self.worked_days_line_ids.unlink()
        self.input_line_ids.unlink()
        for worked_days_line in worked_days_line_ids:
            self.write({
                'worked_days_line_ids': [(0, 0, worked_days_line)]
            })
        for input_line in input_line_ids:
            self.write({
                'input_line_ids': [(0, 0, input_line)]
            })
    
    @api.multi
    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        start_time = time.time()
        res = super(hr_payslip, self).onchange_employee_id(date_from, date_to, employee_id=employee_id, contract_id=contract_id)
        employee = self.env['hr.employee'].browse(employee_id)
        contract = contract_id
        if employee:
            res['value'][
                'department_id'] = employee.department_id and employee.department_id.id or False
            res['value']['marital'] = employee.marital or False
            res['value']['wife_situation'] = employee.wife_situation or False
            res['value']['children'] = employee.children or 0
            res['value']['hire_date'] = employee.hire_date or False
            res['value']['otherid'] = employee.otherid or ''
            res['value'][
                'address_home'] = employee.address_home_id and employee.address_home_id.contact_address.strip() or ''
        if contract:
            res['value'][
                'voucher_mode'] = contract.voucher_mode or False
            res['value'][
                'job_id'] = contract.job_id and contract.job_id.id or False
            res['value'][
                'journal_id'] = contract.journal_id.id or False
            res['value'][
                'cimr_ok'] = contract.cimr_ok or False
            res['value'][
                'cnss_ok'] = contract.cnss_ok or False
        _logger.info('Meter payslip onchange_employee_id '.upper(
        ) + "%s" % (time.time() - start_time))
        return res

    @api.one
    @api.depends("date_from", "date_to")
    def _get_slip_period_fiscalyear(self):
        if self.date_to:
            self.slip_period_id = self.env[
            'date.range'].search([('date_start', '<=' ,self.date_to), ('date_end', '>=', self.date_to)])
        if not self.slip_period_id:
            raise Warning('There is no period defined for this date: '+ str(self.date_to) +'.\nPlease go to Configuration/Periods and configure a fiscal year.')
        self.slip_fiscalyear_id = self.slip_period_id.type_id

    slip_period_id = fields.Many2one(
        'date.range', string=u'Période', compute='_get_slip_period_fiscalyear', store=True)
    slip_fiscalyear_id = fields.Many2one(
        'date.range.type', string=u'Année', compute='_get_slip_period_fiscalyear', store=True)
    employee_user_id = fields.Many2one(
        'res.users', string=u'Utilisateur',  related='employee_id.user_id', store=True)

    solde_tout_compte_id = fields.Many2one(
        'hr.holidays', string=u'Solde de tout compte', readonly=True,)

    @api.one
    @api.depends("input_line_ids")
    def _get_nbr_person_to_charge(self):
        nbr = 0
        for line in self.input_line_ids:
            if line.code == 'NBR_PERSONNE_CHARGE':
                nbr = line.amount
        self.nbr_person_charged = nbr

    nbr_person_charged = fields.Integer(
        string=u'Nombre de personne à charge',
        compute='_get_nbr_person_to_charge',)

    marital = fields.Selection([
        ('C', 'Célibataire'),
        ('M', 'Marié(e)'),
        ('V', 'Veuf(ve)'),
        ('D', 'Divorcé(e)')
    ], string=u'Situation familiale', readonly=True, states={'draft': [('readonly', False)]})

    wife_situation = fields.Selection([
        ('A', 'Affilié(e)'),
        ('W', 'Travaille'),
        ('N', 'Aucun'),
    ], string=u'Situation du partenaire', default='N', readonly=True, states={'draft': [('readonly', False)]})

    children = fields.Integer(
        string=u'Enfants', readonly=True,  states={'draft': [('readonly', False)]})

    hire_date = fields.Date(string=u'Date d\'embauche',)
    otherid = fields.Char(string=u'Matricule', size=64,)
    address_home = fields.Text(string=u'Adresse personnelle',)

    @api.one
    @api.depends("line_ids")
    def _compute_salary(self):
        net = net_imposable = net_contractuel = brut = brut_imposable = 0.0
        for line in self.details_by_salary_rule_category:
            if line.code == 'NET':
                net = line.total
            if line.code == 'BRUT':
                brut = line.total
            if line.code == 'BRUT_IMPOSABLE':
                brut_imposable = line.total
            if line.code == 'NET_CONTRACTUEL':
                net_contractuel = line.total
            if line.code == 'NET_IMPOSABLE':
                net_imposable = line.total
        self.salary_net = net
        self.salary_brut = brut
        self.salary_brut_imposable = brut_imposable
        self.salary_net_contractuel = net_contractuel
        self.salary_net_imposable = net_imposable

    salary_brut = fields.Float(string=u'Salaire brut', digits=dp.get_precision(
        'Salary'), compute='_compute_salary',  store=True,)
    salary_brut_imposable = fields.Float(string=u'Salaire brut imposable', digits=dp.get_precision(
        'Salary'), compute='_compute_salary',  store=True,)
    salary_net = fields.Float(string=u'Salaire net', digits=dp.get_precision(
        'Salary'), compute='_compute_salary',  store=True,)
    salary_net_contractuel = fields.Float(string=u'Salaire net contractuel', digits=dp.get_precision(
        'Salary'), compute='_compute_salary',  store=True,)
    salary_net_imposable = fields.Float(string=u'Salaire net imposable', digits=dp.get_precision(
        'Salary'), compute='_compute_salary',  store=True,)


    @api.multi
    def compute_leave_params(self):
        """
        Cette fonction doit faire sortir les variables suivants :
        - (1) Nombre de congés restant pour N-1
        - (2) Nombre de congés consommé pour N
        - (3) Nombre de congés alloué pour N
        - Solde = (3) + (1) - (2)
        """
        for obj in self:
            based_on_days = obj.contract_id.based_on_days
            leave_status_legal = self.env['hr.holidays.status'].search([('limit','=',False)])
            if based_on_days:
                obj.leave_current_legal = obj.worked_days_line_ids.filtered(lambda r: r.code == leave_status_legal.code).number_of_days
            else:
                obj.leave_current_legal = obj.worked_days_line_ids.filtered(lambda r: r.code == leave_status_legal.code).number_of_hours / obj.contract_id.default_hours_on_leave
            if based_on_days:
                obj.leave_left_legal = obj.worked_days_line_ids.filtered(lambda r: r.code == CONGES_A_CONSOMMER).number_of_days
            else:
                obj.leave_left_legal = obj.worked_days_line_ids.filtered(lambda r: r.code == CONGES_A_CONSOMMER).number_of_hours / obj.contract_id.default_hours_on_leave
            first_contract = self.env['hr.contract'].search([
                ('employee_id','=',obj.employee_id.id),
                ('company_id','=',obj.company_id.id),
            ], limit=1, order='date_start asc')
            dt_start_n, dt_stop_n = fyf(first_contract.date_start, obj.date_to, n=0)
            dt_start_n1, dt_stop_n1 = fyf(first_contract.date_start, obj.date_to, n=-1)
            legal_holidays_n = self.env['hr.holidays.line'].search([
                    ('employee_id', '=', obj.employee_id.id),
                    ('date', '>=', dt_start_n),
                    ('date', '<=', dt_stop_n),
                    ('holiday_status_id.limit', '=', False),
                    ('state', '=', 'validate'),
            ])
            legal_holidays_n1 = self.env['hr.holidays.line'].search([
                    ('employee_id', '=', obj.employee_id.id),
                    ('date', '>=', dt_start_n1),
                    ('date', '<=', dt_stop_n1),
                    ('holiday_status_id.limit', '=', False),
                    ('state', '=', 'validate'),
            ])
            legal_holidays_allocation_n = self.env['hr.holidays'].search([
                    ('employee_id', '=', obj.employee_id.id),
                    ('date', '>=', dt_start_n),
                    ('date', '<=', dt_stop_n),
                    ('holiday_status_id.limit', '=', False),
                    ('state', '=', 'validate'),
                    ('type', '=', 'add'),
            ])
            legal_holidays_allocation_n1 = self.env['hr.holidays'].search([
                    ('employee_id', '=', obj.employee_id.id),
                    ('date', '>=', dt_start_n1),
                    ('date', '<=', dt_stop_n1),
                    ('holiday_status_id.limit', '=', False),
                    ('state', '=', 'validate'),
                    ('type', '=', 'add'),
            ])
            if based_on_days:
                obj.leave_pris_n_legal = sum(legal_holidays_n.mapped('days'))
                obj.leave_pris_n1_legal = sum(legal_holidays_n1.mapped('days'))
            else:
                obj.leave_pris_n_legal = sum(legal_holidays_n.mapped('hours'))
                obj.leave_pris_n1_legal = sum(legal_holidays_n1.mapped('hours'))
            obj.leave_holidays_allocation_n_legal = sum(legal_holidays_allocation_n.mapped('number_of_days_temp'))
            obj.leave_holidays_allocation_n1_legal = sum(legal_holidays_allocation_n1.mapped('number_of_days_temp'))

    leave_current_legal = fields.Float(string='Congé courant', digits=dp.get_precision('Account'),  )
    leave_left_legal = fields.Float(string='Solde des congés', digits=dp.get_precision('Account'),  )
    leave_pris_n_legal = fields.Float(string='Congés pris cette année', digits=dp.get_precision('Account'),  )
    leave_pris_n1_legal = fields.Float(string='Congés pris (N-1)', digits=dp.get_precision('Account'),  )
    leave_holidays_allocation_n_legal = fields.Float(string='Congés alloués pour cette année', digits=dp.get_precision('Account'),  )
    leave_holidays_allocation_n1_legal = fields.Float(string='Congés alloués pour (N-1)', digits=dp.get_precision('Account'),  )
    @api.multi
    @api.depends('leave_holidays_allocation_n_legal',
                 'leave_holidays_allocation_n1_legal',
                 'leave_pris_n_legal',
                 'leave_pris_n1_legal',
                 )
    def _compute_leave_restants(self):
        for obj in self:
            obj.leave_restant_n_legal = obj.leave_holidays_allocation_n_legal - obj.leave_pris_n_legal
            obj.leave_restant_n1_legal = obj.leave_holidays_allocation_n1_legal - obj.leave_pris_n1_legal
    leave_restant_n_legal = fields.Float(string='Congés restant pour cette année', digits=dp.get_precision('Account'),  compute='_compute_leave_restants', store=True)
    leave_restant_n1_legal = fields.Float(string='Congés restant pour (N-1)', digits=dp.get_precision('Account'), compute  ='_compute_leave_restants', store=True)

    @api.multi
    def get_slip_report_items(self, group, patronal, group_rubrique, rename={}, includes=[], excludes=[]):
        self.ensure_one()
        tab = []
        cumul = []
        special = {}
        start_time = time.time()
        for line in self.details_by_salary_rule_category:
            if line.code in SPECIAL_CODE:
                special.update(
                    {line.code: (line.quantity, line.rate, line.amount, line.total)})
            else:
                if line.code not in includes and (line.salary_rule_id.show_on_payslip == 'never' or line.code in excludes):
                    continue
                elif line.code in includes or line.salary_rule_id.show_on_payslip == 'ifnotnull':
                    if line.total == 0:
                        continue
                category = line.category_id.category
                if category == 'none':
                    continue
                if not patronal:
                    if category in ['rp', 'gp']:
                        continue
                name = line.name
                code = line.code
                s_base = 0
                s_taux = 0
                s_gain = 0
                s_retenu = 0
                p_base = 0
                p_taux = 0
                p_retenu = 0
                group_name = False
                group_code = False
                group_rubrique_name = False
                group_rubrique_code = False
                #Rubrique vs Avantage
                avantage = line.salary_rule_id.avantage_id
                rubrique = line.salary_rule_id.rubrique_id
                if avantage:
                    group_rubrique_name = avantage.name
                    group_rubrique_code = avantage.code
                if rubrique:
                    group_rubrique_name = rubrique.name
                    group_rubrique_code = rubrique.code
                if category in ['gs', 'rs']:
                    s_base = line.amount
                    s_taux = line.rate * line.quantity
                    if line.salary_rule_id.holiday_status_id or line.salary_rule_id.is_salary_item:
                        s_taux = line.rate / 100 * line.quantity
                    if s_taux == 100.0:
                        s_taux = 1
                    if category == 'gs':
                        s_gain = line.total
                    else:
                        s_retenu = line.total
                    if SALARIALE in line.code:
                        cotisation = line.salary_rule_id.cotisation_id
                        if cotisation:
                            group_name = cotisation.group_id.name
                            group_code = cotisation.group_id.code
                        new_code = line.code.replace(SALARIALE, PATRONALE)
                        for tmp in self.line_ids:
                            if tmp.code == new_code:
                                p_base = tmp.amount
                                p_taux = tmp.rate * tmp.quantity
                                p_retenu = tmp.total
                                break
                if category in ['gp', 'rp']:
                    found = False
                    if PATRONALE in line.code:
                        cotisation = line.salary_rule_id.cotisation_id
                        if cotisation:
                            group_name = cotisation.group_id.name
                            group_code = cotisation.group_id.code
                        new_code = line.code.replace(PATRONALE, SALARIALE)
                        for tmp in self.line_ids:
                            if tmp.code == new_code and tmp.total != 0:
                                found = True
                                break
                    if not found:
                        s_base = line.amount
                        p_base = line.amount
                        p_taux = line.rate * line.quantity
                        p_retenu = line.total
                    else:
                        continue
                if line.code in rename:
                    name = rename[line.code]
                tab.append([
                    name, code, s_base, s_taux, s_gain, s_retenu, p_base, p_taux, p_retenu, group_name, group_code, group_rubrique_name, group_rubrique_code],)
        cumul = [0, 0, 0, 0, 0, 0, 0]
        if group:
            xx_tab = []
            GROUP_CODES = []
            for item in tab:
                xx_name, xx_code = item[9], item[10]
                if not xx_code or xx_code not in GROUP_CODES:
                    if xx_code:
                        item[0] = xx_name
                        item[1] = xx_code
                        GROUP_CODES.append(xx_code)
                    xx_tab.append(item)
                else:
                    for i, val in enumerate(xx_tab):
                        if xx_code == val[10]:
                            # 2 est la base
                            xx_tab[i][3] += item[3]
                            xx_tab[i][4] += item[4]
                            xx_tab[i][5] += item[5]
                            xx_tab[i][6] += item[6]
                            xx_tab[i][7] += item[7]
                            xx_tab[i][8] += item[8]
                            # 9 et 10 sont group code et name
                            # 11 et 12 sont group rubrique code et name
            tab = xx_tab[:]
        if group_rubrique:
            xx_tab = []
            GROUP_CODES = []
            for item in tab:
                xx_name, xx_code = item[11], item[12]
                if not xx_code or xx_code not in GROUP_CODES:
                    if xx_code:
                        item[0] = xx_name
                        item[1] = xx_code
                        GROUP_CODES.append(xx_code)
                    xx_tab.append(item)
                else:
                    for i, val in enumerate(xx_tab):
                        if xx_code == val[12]:
                            # 2 est la base
                            xx_tab[i][2] += item[2]
                            xx_tab[i][3] = item[3]
                            xx_tab[i][4] += item[4]
                            xx_tab[i][5] += item[5]
                            xx_tab[i][6] += item[6]
                            xx_tab[i][7] += item[7]
                            xx_tab[i][8] += item[8]
                            # 9 et 10 sont group code et name
                            # 11 et 12 sont group rubrique code et name
            tab = xx_tab[:]
        for item in tab:
            for i, val in enumerate(item):
                if i < 2 or i > 8:
                    continue
                cumul[i - 2] += val
        _logger.info('Meter payslip get_slip_report_items '.upper(
        ) + "%s" % (time.time() - start_time))
        return tab, cumul, special

    def get_worked_day_lines(self, contract_ids, date_from, date_to):
        """
        @param contract_ids: list of contract id
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        simulate_elements_ok = self._context.get('simulation', False) and self._context.get('simulate_elements_ok', False) or False
        simulation_ok = self._context.get('simulation', False) or False
        start_time = time.time()
        if not self._context:
            self._context = {}
        status_helper_obj = self.env['hr.holidays.status']
        status_helper_context = self._context.copy()
        status_helper_context.update({'active_test': False})
        status_helper_ids = status_helper_obj.with_context(status_helper_context).search([])
        status_helper = status_helper_ids

        def was_on_leave(employee_id, datetime_day):
            res, code, status = False, False, False
            days, hours = 0.0, 0.0
            if simulation_ok and not simulate_elements_ok:
                return res, code, days, hours, status
            day = datetime_day.strftime("%Y-%m-%d")
            holiday_ids = self.env['hr.holidays.line'].search([
                ('holiday_status_id.is_hs', '=', False),
                ('holiday_status_id.is_rappel', '=', False),
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id),
                ('date', '=', day), ])
            if holiday_ids:
                lines = holiday_ids
                for line in lines:
                    days += line.days
                    hours += line.hours
                status = lines[0].holiday_status_id
                res, code = status.name, status.code
            return res, code, days, hours, status

        def get_all_rappel(employee_id, datetime_day):
            if simulation_ok and not simulate_elements_ok:
                return []
            day = datetime_day.strftime("%Y-%m-%d")
            holiday_ids = self.env['hr.holidays.line'].search([
                ('holiday_id.holiday_status_id.is_rappel', '=', True),
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id),
                ('date', '=', day)
            ])
            holiday_lines = holiday_ids
            return holiday_lines

        def get_all_hs(employee_id, datetime_day):
            if simulation_ok and not simulate_elements_ok:
                return []
            day = datetime_day.strftime("%Y-%m-%d")
            holiday_ids = self.env['hr.holidays.line'].search([
                ('holiday_id.holiday_status_id.is_hs', '=', True),
                ('holiday_id.holiday_status_id.is_rappel', '=', False),
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id),
                ('date', '=', day)
            ])
            holiday_lines = holiday_ids
            return holiday_lines

        def get_holiday_work_lines(employee_id, datetime_day):
            if simulation_ok and not simulate_elements_ok:
                return []
            day = datetime_day.strftime("%Y-%m-%d")
            holiday_ids = self.env['hr.holidays.line'].search([
                ('holiday_id.holiday_status_id.is_work', '=', True),
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id),
                ('date', '=', day)
            ])
            holiday_lines = holiday_ids
            return holiday_lines

#         def get_timesheet_lines(employee_id, datetime_day):
#             if simulation_ok and not simulate_elements_ok:
#                 return []
#             timesheet_obj = self.env['hr.analytic.timesheet']
#             day = datetime_day.strftime("%Y-%m-%d")
#             line_ids = timesheet_obj.search([
#                 ('sheet_id.state', '=', 'done'),
#                 ('sheet_id.employee_id', '=', employee_id),
#                 ('date', '=', day)
#             ])
#             return line_ids

        res = []
        for contract in self.env['hr.contract'].browse(contract_ids):
            first_month = contract.date_start >= date_from and contract.date_start <= date_to
            stc_ok = contract.solde_tout_compte and contract.solde_tout_compte >= date_from and contract.solde_tout_compte <= date_to and True or False
            date_start = date_from < contract.date_start and contract.date_start or date_from
            date_end = contract.date_end and date_to > contract.date_end and contract.date_end or date_to
            if not contract.working_hours:
                # fill only if the contract has a working schedule linked
                continue
            remaining_leaves = {
                'name': _("Reste des congés payés"),
                'sequence': 9,
                'code': RESTE_CONGES_PAYES,
                'number_of_days': stc_ok and contract.remaining_leaves or 0.0,
                'number_of_hours': stc_ok and (contract.remaining_leaves*contract.default_hours_on_holiday) or 0.0,
                'contract_id': contract.id,
            }
            conges_a_consommer = {
                'name': _("Congés payés à consommer"),
                'sequence': 10,
                'code': CONGES_A_CONSOMMER,
                'number_of_days': contract.employee_id.remaining_leaves,
                'number_of_hours': contract.employee_id.remaining_leaves*contract.default_hours_on_holiday,
                'contract_id': contract.id,
            }
            times = {
                'name': _("Pointage"),
                'sequence': 8,
                'code': 'ATTENDANCE',
                'number_of_days': 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            }
            attendance_with_holidays = {
                'name': _("Pointage avec congés"),
                'sequence': 8,
                'code': ATTENDANCE_WITH_HOLIDAYS,
                'number_of_days': 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            }
            timesheet = {
                'name': _("Feuille de temps"),
                'sequence': 9,
                'code': 'TIMESHEET',
                'number_of_days': 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            }
            declaration = {
                'name': _("Nombre de jours déclaré et payé à 100%"),
                'sequence': 1,
                'code': 'DECLARED',
                'number_of_days': (stc_ok and contract.stc_worked_days) or (first_month and contract.nbr_days_declared_first_month) or contract.nbr_days_declared,
                'number_of_hours': (stc_ok and contract.stc_worked_hours) or (first_month and contract.nbr_hours_declared_first_month) or contract.nbr_hours_declared,
                'contract_id': contract.id,
            }
            feries = {
                'name': _("Jours Chomés payés"),
                'sequence': 3,
                'code': 'FERIES',
                'number_of_days': 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            }
            retenues = {
                'name': _("Nombre de retenu"),
                'sequence': 10,
                'code': 'RETENU',
                'number_of_days': 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            }
            contract_dict = {
                'name': _("Contrat"),
                'sequence': 10,
                'code': 'CONTRACT',
                'number_of_days': first_month and contract.nbr_days_declared_first_month or contract.nbr_days_declared,
                'number_of_hours': first_month and contract.nbr_hours_declared_first_month or contract.nbr_hours_declared,
                'contract_id': contract.id,
            }
            leaves = {}
            # for sh in status_helper:
            #     leaves[sh.name] = {
            #         'name': sh.name,
            #         'sequence': 10,
            #         'code': @sh.code,
            #         'number_of_days': 0.0,
            #         'number_of_hours': 0.0,
            #         'contract_id': contract.id,
            #     }
            hss = {}
            day_from = datetime.strptime(date_start, "%Y-%m-%d")
            day_to = datetime.strptime(date_end, "%Y-%m-%d")
            mass_days, mass_hours = self.env['hr.employee.mass.attendance'].get_days_hours(contract.employee_id.id, day_from, day_to)
            mission_days, mission_hours = self.env['hr.employee.mission'].get_days_hours(contract.employee_id.id, day_from, day_to)
            times['number_of_days'] += mass_days + mission_days
            times['number_of_hours'] += mass_hours + mission_hours
            attendance_with_holidays['number_of_days'] += mass_days + mission_days
            attendance_with_holidays['number_of_hours'] += mass_hours + mission_hours
            nb_of_days = (day_to - day_from).days + 1
            for day in range(0, nb_of_days):
                times_days, times_hours = self.env['hr.attendance'].get_days_hours(
                    contract.employee_id.id, day_from + timedelta(days=day))
                times['number_of_days'] += times_days
                times['number_of_hours'] += times_hours
                attendance_with_holidays['number_of_days'] += times_days
                attendance_with_holidays['number_of_hours'] += times_hours
                working_hours_on_holiday = contract.default_hours_on_holiday
                lines = get_all_hs(
                    contract.employee_id.id, day_from + timedelta(days=day))
                work_lines = get_holiday_work_lines(
                    contract.employee_id.id, day_from + timedelta(days=day))
                rappels = get_all_rappel(
                    contract.employee_id.id, day_from + timedelta(days=day))

                for rappel in rappels:
                    declaration.update({
                        'number_of_days': declaration.get('number_of_days', 0) + rappel.days,
                        'number_of_hours': declaration.get('number_of_hours', 0) + rappel.hours,
                    })
                    timesheet.update({
                        'number_of_days': timesheet.get('number_of_days', 0) + rappel.days,
                        'number_of_hours': timesheet.get('number_of_hours', 0) + rappel.hours,
                    })
                    times.update({
                        'number_of_days': times.get('number_of_days', 0) + rappel.days,
                        'number_of_hours': times.get('number_of_hours', 0) + rappel.hours,
                    })
                    attendance_with_holidays.update({
                        'number_of_days': attendance_with_holidays.get('number_of_days', 0) + rappel.days,
                        'number_of_hours': attendance_with_holidays.get('number_of_hours', 0) + rappel.hours,
                    })
                for line in lines:
                    if hss.get(line.holiday_id.holiday_status_id.code, False):
                        tmp = hss.get(line.holiday_id.holiday_status_id.code)
                        hss[line.holiday_id.holiday_status_id.code].update({
                            'number_of_days': tmp.get('number_of_days', 0) + line.days,
                            'number_of_hours': tmp.get('number_of_hours', 0) + line.hours,
                        })
                    else:
                        hss[line.holiday_id.holiday_status_id.code] = {
                            'name': line.holiday_id.holiday_status_id.name,
                            'sequence': 20,
                            'code': line.holiday_id.holiday_status_id.code,
                            'number_of_days': line.days,
                            'number_of_hours': line.hours,
                            'contract_id': contract.id,
                        }
#                 timesheet_lines = get_timesheet_lines(
#                     contract.employee_id.id, day_from + timedelta(days=day))
                timesheet_lines = False
                if timesheet_lines:
                    timesheet['number_of_days'] += 1.0
#                 for timesheet_line in timesheet_lines:
#                     timesheet['number_of_hours'] += timesheet_line.unit_amount
                for work_line in work_lines:
                    feries['number_of_days'] -= work_line.days
                    feries['number_of_hours'] -= work_line.hours
                    attendance_with_holidays['number_of_days'] -= work_line.days
                    attendance_with_holidays['number_of_hours'] -= work_line.hours
                if self.env['hr.holidays.public'].is_free(
                        fields.Datetime.to_string(day_from + timedelta(days=day))):
                    attendance_with_holidays['number_of_days'] += 1.0
                    attendance_with_holidays['number_of_hours'] += working_hours_on_holiday
                    feries['number_of_days'] += 1.0
                    feries['number_of_hours'] += working_hours_on_holiday
                    declaration['number_of_days'] -= 1.0
                    declaration['number_of_hours'] -= working_hours_on_holiday
                # the employee had to work
                leave_type, code, leave_days, leave_hours, leave_status = was_on_leave(
                    contract.employee_id.id, day_from + timedelta(days=day))
                if leave_status:
                    if leave_status.is_retained:
                        retenues['number_of_days'] += leave_days
                        retenues['number_of_hours'] += leave_hours
                    if not leave_status.is_retained and not leave_status.is_hs and not leave_status.is_rappel:
                        attendance_with_holidays['number_of_days'] += leave_days
                        attendance_with_holidays['number_of_hours'] += leave_hours
                    declaration['number_of_days'] -= leave_days
                    declaration['number_of_hours'] -= leave_hours
                    # if he was on leave, fill the leaves dict
                    if leave_type in leaves:
                        leaves[leave_type]['number_of_days'] += leave_days
                        leaves[leave_type][
                            'number_of_hours'] += leave_hours
                    else:
                        leaves[leave_type] = {
                            'name': leave_type,
                            'sequence': 10,
                            'code': code,
                            'number_of_days': leave_days,
                            'number_of_hours': leave_hours,
                            'contract_id': contract.id,
                        }
            leaves = [value for key, value in leaves.items()]
            hss = [value for key, value in hss.items()]
            codes = [x.get('code')
                     for x in leaves] + [x.get('code') for x in hss]
            leaves_skipped = []
            for leave_tmp in status_helper:
                if leave_tmp.code not in codes:
                    leaves_skipped.append({
                        'name': leave_tmp.name,
                        'sequence': 10,
                        'code': leave_tmp.code,
                        'number_of_days': 0.0,
                        'number_of_hours': 0,
                        'contract_id': contract.id,
                    })
            res += [declaration] + [contract_dict]  + [timesheet] + \
                [times] + [attendance_with_holidays] + [feries] + hss + leaves + \
                leaves_skipped + [remaining_leaves] + [conges_a_consommer] + [retenues]
        _logger.info('Meter payslip get_worked_day_lines '.upper(
        ) + "%s" % (time.time() - start_time))
        return res

    def get_inputs(self, contract_ids, date_from, date_to):
        start_time = time.time()

        def get_seniority(age):
            return self.env['hr.scale.seniority'].get_seniority_rate(age)

        res = []
        contract_obj = self.env['hr.contract']
        rule_obj = self.env['hr.salary.rule']

        structure_ids = contract_obj.browse(contract_ids).get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        sorted_rule_ids = [
            id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        ctx = dict(self._context, seniority_end=date_to)
        for contract in contract_obj.with_context(ctx).browse(contract_ids):
            stc_ok = contract.solde_tout_compte and contract.solde_tout_compte >= date_from and contract.solde_tout_compte <= date_to and True or False
            company = contract.employee_id.company_id
            salary_by_day = {
                'name': _(u"Salaire par jour"),
                'amount': contract.salary_by_day,
                'code': "SALAIRE_PAR_JOUR",
                'contract_id': contract.id,
            }
            salary_by_hour = {
                'name': _(u"Salaire par heure"),
                'amount': contract.salary_by_hour,
                'code': "SALAIRE_PAR_HEURE",
                'contract_id': contract.id,
            }
            m52week = timedelta(weeks=-52)  # TODO translate it to years = -1
            m1days = timedelta(days=-1)
            sbm_date_to = datetime.strptime(date_from, "%Y-%m-%d") + m1days
            sbm_date_from = (sbm_date_to + m52week).strftime("%Y-%m-%d")
            sbm_date_to = sbm_date_to.strftime("%Y-%m-%d")
            sbm_nbr_payslip = self.env['hr.payslip'].search_count([
                ('employee_id', '=', contract.employee_id.id),
                ('date_to', '>=', sbm_date_from),
                ('date_to', '<=', sbm_date_to),
                ('state', '=', 'done'),
            ])
            sbm_amount_avg = self.env['hr.dictionnary'].compute_value(
                code="BRUT",
                date_start=sbm_date_from,
                date_stop=sbm_date_to,
                employee_id=contract.employee_id.id,
                state='done',
                company_id=company.id
            )
            salary_brut_moyen = {
                'name': _(u"Salaire brut moyen (52 semaines)"),
                'amount': sbm_nbr_payslip > 0 and sbm_amount_avg / float(sbm_nbr_payslip) or 0,
                'code': "SALAIRE_BRUT_MOYEN",
                'contract_id': contract.id,
            }
            seniority_rate = {
                'name': _(u"Taux d'ancienneté"),
                'amount': get_seniority(int(contract.employee_id.seniority or 0)),
                'code': "ANCIENNETE_TAUX",
                'contract_id': contract.id,
            }
            seniority = {
                'name': _(u"Ancienneté"),
                'amount': contract.employee_id.seniority or 0,
                'code': "ANCIENNETE",
                'contract_id': contract.id,
            }
            x_age = 0
            if contract.employee_id.birthday:
                x_age = relativedelta(fields.Datetime.from_string(date_to), fields.Datetime.from_string(contract.employee_id.birthday)).years + relativedelta(
                    fields.Datetime.from_string(date_to), fields.Datetime.from_string(contract.employee_id.birthday)).months * 1 / 12.
            age = {
                'name': _("Age"),
                'amount': x_age,
                'code': "AGE",
                'contract_id': contract.id,
            }
            fp_rate = {
                'name': _("Taux des frais professionels"),
                'amount': company.fp_taux,
                'code': "FP_TAUX",
                'contract_id': contract.id,
            }
            fp_plafond = {
                'name': _("Plafond des frais professionels"),
                'amount': company.fp_plafond,
                'code': "FP_PLAFOND",
                'contract_id': contract.id,
            }
            cf_plafond = {
                'name': _("Plafond des charges familiales"),
                'amount': company.cf_plafond,
                'code': "CF_PLAFOND",
                'contract_id': contract.id,
            }
            cf_taux = {
                'name': _("Montant pour une charge familiale"),
                'amount': company.cf_amount,
                'code': "CF_MONTANT",
                'contract_id': contract.id,
            }
            nbr_person_charged = {
                'name': _("Nombre de personne à charger"),
                'amount': contract.employee_id.nbr_person_charged or 0,
                'code': "NBR_PERSONNE_CHARGE",
                'contract_id': contract.id,
            }
            prime_preavis = {
                'name': _("Prime de préavis"),
                'amount': stc_ok and contract.prime_preavis or 0,
                'code': "PRIME_PREAVIS",
                'contract_id': contract.id,
            }
            prime_licenciement = {
                'name': _(u"Prime de licenciement"),
                'amount': stc_ok and contract.prime_licenciement or 0,
                'code': "PRIME_LICENCIEMENT",
                'contract_id': contract.id,
            }
            res += [salary_by_day, salary_by_hour, salary_brut_moyen, fp_rate,
                    fp_plafond, cf_plafond, cf_taux, nbr_person_charged, age,
                    seniority_rate, seniority, prime_preavis, prime_licenciement]
            for rule in rule_obj.browse(sorted_rule_ids):
                if rule.input_ids:
                    for input in rule.input_ids:
                        inputs = {
                            'name': input.name,
                            'code': input.code,
                            'contract_id': contract.id,
                        }
                        res += [inputs]
        _logger.info(
            'Meter payslip get_inputs '.upper() + "%s" % (time.time() - start_time))
        return res


class hr_payslip_line(models.Model):
    _inherit = 'hr.payslip.line'

    amount_select = fields.Selection(
        selection_add=[('flexible_percentage', 'Pourcentage flexible')])
    amount = fields.Float(digits=dp.get_precision('Salary Rate'))


class hr_payslip_input(models.Model):
    _inherit = 'hr.payslip.input'

    amount = fields.Float(digits=dp.get_precision('Salary Rate'))
