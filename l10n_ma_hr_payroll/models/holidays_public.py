# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta


class hr_holidays_public(models.Model):
    _name = 'hr.holidays.public'
    _description = u'Jours fériés'
    _order = 'date_start asc'

    @api.model
    def is_free(self, date_string):
        if isinstance(date_string, datetime):
            date_string = fields.Date.to_string(date_string)
        holiday = self.search([
                ('ignore', '=', False),
                ('date_start', '<=', date_string),
                ('date_end', '>=', date_string)
             ], limit=1)
        if holiday:
            return True
        else:
            return False

    @api.model
    def count_days(self, date_start, date_end):
        if isinstance(date_start, basestring):
            date_start = fields.Datetime.from_string(date_start)
        if isinstance(date_end, basestring):
            date_end = fields.Datetime.from_string(date_end)
        days = 0
        for day in range((date_end - date_start).days + 1):
            new_date = date_start + timedelta(days=day)
            if self.is_free(new_date):
                days += 1
        return days

    @api.one
    @api.depends("date_start")
    def _compute_year(self):
        if self.date_start:
            self.year = self.date_start[:4]
        else:
            self.year = False

    name = fields.Text(string=u"Description", size=64, required=True)
    date_start = fields.Date(string=u'Date début', required=True)
    date_end = fields.Date(string=u'Date fin', required=True)
    ignore = fields.Boolean(string='Ignorer dans la paie',  )
    year = fields.Char(
        string=u'Year', size=64, compute='_compute_year', store=True)

    _sql_constraints = [
        ('date_check', 'CHECK (date_start <= date_end)',
         'Vérifier les erreurs des dates !'),
    ]
