# encoding: utf-8

from odoo import models, fields, api, _
from odoo.exceptions import Warning

from datetime import datetime

import odoo.addons.decimal_precision as dp

class hr_employee_km(models.Model):
    _name = 'hr.employee.km'
    _description = u'kilométrage'
    _order = 'date desc'

    name = fields.Char(string=u'Nom', size=64, required=False,states={'draft' : [('readonly', False)]}, readonly=True, )
    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé', required=True,states={'draft' : [('readonly', False)]}, readonly=True, )
    value = fields.Float(string=u'Kilométrage', digits=dp.get_precision('Account'),  states={'draft' : [('readonly', False)]}, readonly=True, )
    cv = fields.Integer(string=u'Puissance fiscale',  required=True, states={'draft' : [('readonly', False)]}, readonly=True, )
    date = fields.Date(string=u'Date', required=True, default= lambda self: fields.Date.today() , states={'draft' : [('readonly', False)]}, readonly=True,)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Terminé'),
    ], string=u'État', readonly=True, copy=False, default='draft',)

    saisie_line_id = fields.Many2one('hr.saisie.line', string=u'Ligne de saisie',)


    @api.model
    def get_km_cv(self, employee_id, date_from, date_to, cv=False):
        if not isinstance(employee_id, (int, long)):
            employee_id = employee_id.id
        if isinstance(date_from, datetime):
            date_from = fields.Datetime.to_string(date_from)
        if isinstance(date_to, datetime):
            date_to = fields.Datetime.to_string(date_to)
        domain = [
            ('employee_id', '=', employee_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'done'),
        ]
        if cv:
            domain.append(('cv','=', cv))
        lines = self.search(domain)
        km, cv = 0.0, 0
        for line in lines:
            cv = line.cv
            km += line.value
        return km, cv

    @api.model
    def get_cvs(self, employee_id, date_from, date_to):
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
        return list(set(lines.mapped('cv')))

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
        return super(hr_employee_km, self).unlink()
