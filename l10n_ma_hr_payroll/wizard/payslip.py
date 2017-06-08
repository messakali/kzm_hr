# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning

import odoo.addons.decimal_precision as dp


class hr_payslip_edit_wizard(models.TransientModel):
    _name = 'hr.payslip.edit.wizard'
    _description = 'Edition en lot'

    work_ids = fields.One2many(
        'hr.payslip.worked_days.wizard', 'run_id', string=u'Jours travaillés',)
    input_ids = fields.One2many(
        'hr.payslip.input.wizard', 'run_id', string=u'Entrées',)
    payslip_ids = fields.Many2many('hr.payslip', string=u'Bulletins de paie',)

    @api.model
    def default_get(self, fields):
        res = super(hr_payslip_edit_wizard, self).default_get(fields)
        ids = self.env.context.get('active_ids', [])
        payslips = self.env['hr.payslip'].browse(
            ids).filtered(lambda r: r.state == 'draft')
        res['payslip_ids'] = payslips.mapped('id')
        if payslips:
            slip = payslips[0]
            res['work_ids'] = [{
                'name': x.name,
                'code': x.code,
                'number_of_days': x.number_of_days,
                'number_of_hours': x.number_of_hours,
            } for x in slip.worked_days_line_ids]
            res['input_ids'] = [{
                'name': x.name,
                'code': x.code,
                'amount': x.amount,
            } for x in slip.input_line_ids]
        return res

    @api.one
    def erase(self):
        payslip_ids = self.payslip_ids.mapped('id')
        for wizard_work in self.work_ids.filtered(lambda r: r.erase_ok):
            lines = self.env['hr.payslip.worked_days'].search([
                ('code', '=', wizard_work.code),
                ('payslip_id', 'in', payslip_ids),
            ])
            lines.write({
                'number_of_days': wizard_work.number_of_days,
                'number_of_hours': wizard_work.number_of_hours,
            })
        for wizard_input in self.input_ids.filtered(lambda r: r.erase_ok):
            lines = self.env['hr.payslip.input'].search([
                ('code', '=', wizard_input.code),
                ('payslip_id', 'in', payslip_ids),
            ])
            lines.write({
                'amount': wizard_input.amount,
            })

    @api.one
    def apply(self):
        self.erase()

    @api.one
    def apply_compute(self):
        self.apply()
        self.payslip_ids.compute_sheet()

    @api.one
    def apply_compute_confirm(self):
        self.apply_compute()
        self.payslip_ids.process_sheet()


class hr_payslip_worked_days(models.TransientModel):

    '''
    Payslip Worked Days
    '''

    _name = 'hr.payslip.worked_days.wizard'
    _description = 'Payslip Worked Days'

    run_id = fields.Many2one('hr.payslip.edit.wizard', string=u'Assistant',)
    erase_ok = fields.Boolean(string=u'Remplacer', default=False,)
    name = fields.Char(string=u'Description', size=64, readonly=True, )
    code = fields.Char(string=u'Code', size=64, readonly=True, )
    number_of_days = fields.Float(
        string=u'Nombre de jours', digits=dp.get_precision('Account'),)
    number_of_hours = fields.Float(
        string=u'Nombre d\'heures', digits=dp.get_precision('Account'),)


class hr_payslip_input(models.TransientModel):

    '''
    Payslip Input
    '''

    _name = 'hr.payslip.input.wizard'
    _description = 'Payslip Input'

    run_id = fields.Many2one('hr.payslip.edit.wizard', string=u'Assistant',)
    erase_ok = fields.Boolean(string=u'Remplacer', default=False,)
    name = fields.Char(string=u'Description', size=64, readonly=True, )
    code = fields.Char(string=u'Code', size=64, readonly=True, )
    amount = fields.Float(string=u'Valeur', digits=dp.get_precision('Account'),)
