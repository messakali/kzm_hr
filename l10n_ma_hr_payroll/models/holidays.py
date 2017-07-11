# encoding: utf-8

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning
import datetime
from odoo.addons.kzm_base.controllers.tools import remove_accent


class hr_holidays(models.Model):
    _inherit = 'hr.holidays'

    date = fields.Date(string='Date', default=lambda self: fields.Date.today() ,   )  
    number_of_hours_temp = fields.Float(
        string=u'Nombre d\'heures', digits=dp.get_precision('Holiday'),)

    line_ids = fields.One2many(
        'hr.holidays.line', 'holiday_id', string=u'Lignes',)

    @api.one
    @api.depends("number_of_hours_temp")
    def _compute_number_of_hours(self):
        nbr = self.number_of_hours_temp
        if self.type == 'remove':
            nbr = -nbr
        self.number_of_hours = nbr

    number_of_hours = fields.Float(string=u'Number d\'heures', digits=dp.get_precision(
        'Account'), compute='_compute_number_of_hours',  store=True)

    @api.one
    def should_be_refused(self):
        if self.state == 'refuse':
            pass
        elif self.state == 'draft':
            self.signal_workflow('confirm')
            self.signal_workflow('refuse')
        elif self.state == 'confirm':
            self.signal_workflow('refuse')
        elif self.state == 'first_validate':
            self.signal_workflow('refuse')
        elif self.state == 'validate':
            self.signal_workflow('refuse')

    @api.one
    def should_be_validated(self):
        if self.state == 'refuse':
            self.signal_workflow('reset')
            self.signal_workflow('confirm')
            self.signal_workflow('validate')
            self.signal_workflow('second_validate')
        elif self.state == 'draft':
            self.signal_workflow('confirm')
            self.signal_workflow('validate')
            self.signal_workflow('second_validate')
        elif self.state == 'confirm':
            self.signal_workflow('validate')
            self.signal_workflow('second_validate')
        elif self.state == 'first_validate':
            self.signal_workflow('second_validate')
        elif self.state == 'validate':
            pass

    @api.one
    def flush(self):
        days = sum([x.days for x in self.line_ids])
        hours = sum([x.hours for x in self.line_ids])
        self.write({
            'number_of_hours_temp': hours,
            'number_of_days_temp': days,
        })

    @api.one
    @api.depends('number_of_days_temp', 'number_of_hours_temp')
    def _compute_summary(self):
        self.summary = str(self.number_of_days_temp) + ' ' + _('days') + \
            '.\n' + str(self.number_of_hours_temp) + ' ' + _('hours') + '.'

    summary = fields.Text(
        string=u'Résumé', readonly=True, compute='_compute_summary', store=True)

    holiday_status_code = fields.Char(
        string=u'Code de type de congé', size=64,)

    saisie_line_id = fields.Many2one('hr.saisie.line', string=u'Ligne de saisie',)

    @api.onchange('holiday_status_code')
    def _onchange_holiday_status_code(self):
#         print self.holiday_status_code
        if self.holiday_status_code:
            return {
                'domain': {
                    'holiday_status_id': [('code', 'ilike', self.holiday_status_code)]
                }
            }

    def _update_numbers(self, res, holiday_status_id,
                        employee_id, dd, ds):
        emp_obj = self.env['hr.employee']
        contract_obj = self.env['hr.contract']
        resource_obj = self.env['resource.calendar']
        status_obj = self.env['hr.holidays.status']
        holidays_public = self.env['hr.holidays.public']
        status = status_obj.browse(holiday_status_id)
        employee = emp_obj.browse(employee_id)
        resource = employee and employee.company_id.working_hours or False
        contract_id = contract_obj.search([
            ('employee_id', '=', employee_id),
            ('is_contract_valid_by_context', '=', dd),
        ], limit=1)
        contract = contract_id and contract_obj.browse(contract_id[0]) or False
        if not contract:
            res['value'].update(
                {'holiday_status_id': False})
            res['warning'] = {
                'title': _('Aucun contrat trouvé'),
                'message': _('Veuillez définir un contrat valide pour l\'employé [%s]') % employee.name
            }
            return res
        default_hours_on_holiday = contract.default_hours_on_holiday or employee.company_id.default_hours_on_holiday
        number_of_hours_temp = 0
        number_of_days_temp = 0
        tab = []
        if not status:
            return res
        if not employee:
            res['value'].update(
                {'holiday_status_id': False})
            res['warning'] = {
                'title': _('Aucun employé trouvé'),
                'message': _('Veuillez spécifier un employé')
            }
            return res
        if not resource:
            res['value'].update({'holiday_status_id': False})
            res['warning'] = {
                'title': _('Aucun temps de travaille paramétré'),
                'message': _('Veuillez spécifier un temps de travail valide pour la société [%s]') % employee.company_id.name
            }
            return res
        if status.is_hs or status.is_rappel:
            if (ds - dd).days == 0 and ds.day == dd.day:
                number_of_days_temp = 1
                number_of_hours_temp = (
                    ds - dd).seconds / 3600. + (ds - dd).days * 24
                tab.append((0, 0, {
                    'date': fields.Datetime.to_string(dd),
                    'hours': number_of_hours_temp,
                    'days': 1,
                }))
            elif (ds - dd).days == 0 and ds.day != dd.day:
                number_of_days_temp = 2
                number_of_hours_temp = (
                    ds - dd).seconds / 3600. + (ds - dd).days * 24
                tab.append((0, 0, {
                    'date': fields.Datetime.to_string(dd),
                    'hours': (
                        dd.replace(hour=23, minute=59, second=59) - dd).seconds / 3600.,
                    'days': 1,
                }))
                tab.append((0, 0, {
                    'date': fields.Datetime.to_string(ds),
                    'hours': (
                        ds - ds.replace(hour=0, minute=0, second=0)).seconds / 3600.,
                    'days': 1,
                }))
            else:
                res['value'].update({'holiday_status_id': False})
                res['warning'] = {
                    'title': _('Erreur intervalle de temps'),
                    'message': _('Cette declaration ne doit pas depasser deux jours')
                }
                return res
        else:
            for day in range((ds - dd).days + 1):
                new_date = dd + datetime.timedelta(days=day)
                new_date_start = new_date.replace(hour=0, minute=0, second=0)
                new_date_stop = new_date.replace(hour=23, minute=59, second=59)
                new_date_str = fields.Datetime.to_string(new_date)
                if not holidays_public.is_free(new_date_str) or status.include_free:
                    value = resource_obj.get_working_hours_of_date(
                        resource.id,
                        start_dt=new_date_start, end_dt=new_date_stop)
                    if status.include_free:
                        if status.is_work: #JFT
                            value = default_hours_on_holiday
                    if value:
                        number_of_days_temp += 1
                        number_of_hours_temp += value
                        tab.append((0, 0, {
                            'date': new_date_str,
                            'hours': value,
                            'days': 1,
                        }))
        res['value'].update({
            'number_of_days_temp': number_of_days_temp,
            'number_of_hours_temp': number_of_hours_temp,
            'line_ids':  tab,
        })
        return res

#     def _onchange_date_from(self, type_holiday, holiday_status_id, employee_id, date_to, date_from):
#         res = super(hr_holidays, self)._onchange_date_from(
#             date_to, date_from)
#         if not date_to or not date_from or type_holiday != 'remove':
#             return res
#         dd = datetime.datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S")
#         ds = datetime.datetime.strptime(date_to, "%Y-%m-%d %H:%M:%S")
#         return self._update_numbers(res, holiday_status_id, employee_id, dd, ds)
# 
#     def _onchange_date_to(self, type_holiday, holiday_status_id, employee_id, date_to, date_from):
#         res = super(hr_holidays, self)._onchange_date_to(
#             date_to, date_from)
#         if not date_to or not date_from or type_holiday != 'remove':
#             return res
#         dd = datetime.datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S")
#         ds = datetime.datetime.strptime(date_to, "%Y-%m-%d %H:%M:%S")
#         return self._update_numbers(res, holiday_status_id, employee_id, dd, ds)

    @api.one
    @api.constrains('date_from')
    def _check_date_from(self):
        self = self.sudo()
        # TODO you can get contract by context
        if self.employee_id and self.employee_id.current_contract_id and \
                self.employee_id.current_contract_id.date_begin_holiday > \
                self.date_from and not self.holiday_status_id.limit and \
                self.type == 'remove':
            raise Warning(_('Vous ne pouvez pas demander un congé légal avant [%s]' %
                            self.employee_id.current_contract_id.date_begin_holiday))


    def _check_holidays(self):
        for record in self:
            if record.holiday_type != 'employee' or record.type != 'remove' or not record.employee_id or record.holiday_status_id.limit:
                continue
            if record.employee_id.holiday_force_remove:
                continue
            leave_days = record.holiday_status_id.get_days(record.employee_id.id)[record.holiday_status_id.id]
            if leave_days['remaining_leaves'] < 0 or leave_days['virtual_remaining_leaves'] < 0:
                # Raising a warning gives a more user-friendly feedback than the default constraint error
                raise Warning(_('The number of remaining leaves is not sufficient for this leave type.\n'
                                'Please verify also the leaves waiting for validation.'))
        return True


class hr_holidays_line(models.Model):
    _name = 'hr.holidays.line'

    date = fields.Date(string=u'Date',)
    holiday_id = fields.Many2one('hr.holidays', string=u'Congé',)
    holiday_status_id = fields.Many2one(
        'hr.holidays.status', string=u'Type de congé',
        related='holiday_id.holiday_status_id', store=True)
    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé',
        related='holiday_id.employee_id', store=True)
    hours = fields.Float(
        string=u'Heures', digits=dp.get_precision('Hour'),)
    days = fields.Float(string=u'Jour', digits=dp.get_precision('Day'),)
    state = fields.Selection(
        string=u'État', related='holiday_id.state', store=True)


class hr_holidays_status(models.Model):
    _inherit = 'hr.holidays.status'

    code = fields.Char(string=u'Code', size=64,)
    sequence = fields.Integer(string=u'Séquence',)
    majoration = fields.Float(string=u'Majoration', required=True, default=0,
                              help="""Entrer 100 pour faire une majoration à  200% de salaire\n
                                Règle : salaire journalier * (1 + majoration/100)""",
                              digits=dp.get_precision('Account'))

    @api.one
    @api.depends("majoration")
    def _compute_majoration_taux(self):
        self.majoration_rate = self.majoration and (
            1 + self.majoration / 100) or 1

    majoration_rate = fields.Float(string=u'Taux de majoration', digits=dp.get_precision(
        'Account'), compute='_compute_majoration_taux', store=True,)
    is_hs = fields.Boolean(
        string=u'Est heures supplémentaires', default=False)

    include_free = fields.Boolean(string=u'Inclu les jours fériés', default=False,)
    is_work = fields.Boolean(string=u'Travaille en congés', default=False,)
    is_rappel = fields.Boolean(string=u'Est un rappel', default=False,)

    is_retained = fields.Boolean(string=u'Est un retenu',  default=False)
    show_on_payslip = fields.Selection([
        ('never', 'Jamais'),
        ('ifnotnull', 'Si différent du zéro'),
        ('always', 'Toujours'),
    ], string=u'Affichage sur les bulletins', required=True, default='ifnotnull')


    show_on_ledger = fields.Selection([
        ('never', 'Jamais'),
        ('ifnotnull', 'Si différent du zéro'),
        ('always', 'Toujours'),
    ], string=u'Affichage dans le livre de paie', required=True, default='ifnotnull')

    analytic_account_id = fields.Many2one(
        'account.analytic.account', string=u'Compte analytique',)
    account_tax_id = fields.Many2one('account.tax', string=u'Code TVA',)
    account_debit = fields.Many2one(
        'account.account', string=u'Compte du débit')
    account_credit = fields.Many2one(
        'account.account', string=u'Compte du crédit')

    export_ok = fields.Boolean(string=u'Export/Import CSV', default=True,)


    @api.onchange('name')
    def _onchange_name(self) :
        if self.name and not self.code:
            self.code = remove_accent(self.name.strip().replace(' ','_')).upper()

    # @api.multi
    # def _get_type(self):
    #     tt = 'leave'
    #     if self.is_hs:
    #         tt = 'hs'
    #     if self.is_work:
    #         tt = 'work'
    #     if self.is_retained:
    #         tt = 'unpaid'
    #     if self.is_rappel:
    #         tt = 'rappel'
    #     self.type = tt
    #
    # @api.one
    # def _inverse_type(self):
    #     if self.type == 'leave':
    #         self.write({
    #             'is_retained': False,
    #             'is_work': False,
    #             'is_hs': False,
    #             'is_rappel': False,
    #         })
    #     if self.type == 'unpaid':
    #         self.write({
    #             'is_retained': True,
    #             'is_work': False,
    #             'is_hs': False,
    #             'is_rappel': False,
    #         })
    #
    # type = fields.Selection([
    #     ('leave', 'Leave'),
    #     ('unpaid', 'Unpaid'),
    #     ('hs', 'Overtime'),
    #     ('work', 'Working holiday'),
    #     ('rappel', 'Rappel'),
    # ], string=u'Type', compute='_get_type', inverse='_inverse_type',)

    @api.model
    def create(self, vals):
        holiday_status_id = super(hr_holidays_status, self).create(vals)
        self.env['hr.axe'].create({'holiday_status_id': holiday_status_id.id})
        return holiday_status_id

    @api.multi
    def write(self, vals):
        res = super(hr_holidays_status, self).write(vals)
        for holiday_status in self:
            axes = self.env['hr.axe'].search(
                [('holiday_status_id', '=', holiday_status.id)])
            if axes:
                for axe in axes:
                    axe.write({'holiday_status_id': holiday_status.id})
            else:
                axes.create({'holiday_status_id': holiday_status.id})
        return res

    @api.multi
    def unlink(self):
        for holiday_status in self:
            axes = self.env['hr.axe'].search(
                [('holiday_status_id', '=', holiday_status.id)])
            if axes:
                for axe in axes:
                    axe.unlink()
        return super(hr_holidays_status, self).unlink()
