# encoding: utf-8

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from .variables import *


class hr_contract(models.Model):
    _inherit = 'hr.contract'

    @api.model
    def create(self, vals):
        if not vals.get('situation'):
            vals.update({'situation': 'NON_RENSEIGNE'})
        contract_id = super(hr_contract, self).create(vals)
        return contract_id


    @api.one
    @api.depends('employee_id')
    def _get_situation(self):
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('date', '<=', fields.Date.today()),
            ('contract_id', '=', self.id),
        ]
        line = self.env['hr.employee.situation'].search(
            domain, order='date desc', limit=1)
        self.situation = line and line.name or False

    @api.one
    def _set_situation(self):
        situation_obj = self.env['hr.employee.situation']
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('contract_id', '=', self.id),
        ]
        first_element = situation_obj.search(domain, order='date asc', limit=1)
        if not first_element:
            first_element = situation_obj.create({
                'name': 'NON_RENSEIGNE',
                'employee_id': self.employee_id.id,
                'contract_id': self.id,
                'date': self.date_start,
            })
        # TODAY
        today = fields.Date.from_string(fields.Date.today())
        ctx = {'date': fields.Date.to_string(today + relativedelta(days=-1))}
        situation = self.employee_id.with_context(ctx).get_situation()
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('date', '=', fields.Date.today()),
            ('contract_id', '=', self.id),
        ]
        line = self.env['hr.employee.situation'].search(domain)
        if situation == self.situation :
            if line != first_element:
                line.unlink()
            return True
        if line:
            line.name = self.situation
        else:
            line.create({
                'name': self.situation,
                'employee_id': self.employee_id.id,
                'contract_id': self.id,
            })

    situation = fields.Selection(
        SITUATION, string=u'Situation', compute='_get_situation', inverse='_set_situation',
        track_visibility='onchange', )
