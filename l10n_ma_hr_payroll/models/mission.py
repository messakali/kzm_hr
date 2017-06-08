# encoding: utf-8

from odoo import models, fields, api, _
from odoo.exceptions import Warning

from datetime import datetime

import odoo.addons.decimal_precision as dp

class hr_employee_mission(models.Model):
    _name = 'hr.employee.mission'
    _description = 'Missions'
    _order = 'date desc'

    name = fields.Char(string=u'Nom', size=64, required=True, states={'draft' : [('readonly', False)]}, readonly=True,)
    employee_id = fields.Many2one('hr.employee', string=u'Employé', required=True,states={'draft' : [('readonly', False)]}, readonly=True,)

    @api.one
    @api.depends("date","employee_id")
    def _get_contract(self):
        if self.employee_id and self.date:
            self.contract_id = self.env['hr.contract'].search([('is_contract_valid_by_context','=',self.date)], order='date_start desc', limit=1)
        else:
            self.contract_id = False

    days = fields.Float(
        string=u'Nombre de jours', digits=dp.get_precision('Account'), default=0,states={'draft' : [('readonly', False)]}, readonly=True,)
    hours = fields.Float(
        string=u'Nombre d\'heures', digits=dp.get_precision('Account'), default=0,states={'draft' : [('readonly', False)]}, readonly=True,)
    date = fields.Date(string=u'Date', required=True, states={'draft' : [('readonly', False)]}, readonly=True,)
    contract_id = fields.Many2one('hr.contract', string=u'Contrat', compute='_get_contract', store=False   )
    based_on = fields.Selection(
        string=u'Basé sur', related='contract_id.based_on', store=False, readonly=True, )
    based_on_days = fields.Boolean(
        string=u'Basé sur les jours', related='contract_id.based_on_days', store=False, readonly=True, )
    notes = fields.Text(string=u'Notes', states={'draft' : [('readonly', False)]}, readonly=True, )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Terminé'),
    ], string=u'État', readonly=True, copy=False, default='draft',)


    @api.model
    def get_days_hours(self, employee_id, date_from, date_to):
        if not isinstance(employee_id, (int, long)):
            employee_id = employee_id.id
        if isinstance(date_from, datetime):
            date_from = fields.Datetime.to_string(date_from)
        if isinstance(date_to, datetime):
            date_to = fields.Datetime.to_string(date_to)
        lines = self.search([
            ('employee_id', '=', employee_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'done'),
        ])
        days, hours = 0.0, 0.0
        for line in lines:
            days += line.days
            hours += line.hours
        return days, hours

    @api.one
    def set_done(self):
        self.state = 'done'

    @api.one
    def set_draft(self):
        self.state = 'draft'

    @api.multi
    def unlink(self):
        for obj in self:
            if obj.state != 'draft':
                raise Warning(
                    _('Vous ne pouvez pas supprimer un document qui n\'est pas en état brouillon'))
        return super(hr_employee_mission, self).unlink()
