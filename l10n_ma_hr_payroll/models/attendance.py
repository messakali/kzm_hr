# encoding: utf-8

from odoo import models, fields, api, _
from datetime import datetime
import odoo.addons.decimal_precision as dp


class hr_attendance(models.Model):
    _inherit = 'hr.attendance'

    @api.one
    @api.depends("name")
    def _compute_jour(self):
        self.jour = self.name and self.name[:10] or False

    name = fields.Datetime()
    jour = fields.Date(string=u'Jour', store=True, compute='_compute_jour')

    gap = fields.Float(
        string=u'GAP', digits=dp.get_precision('Account'), default=0)
    action_state = fields.Selection([
        ('in_late', 'In Late'),
        ('out_late', 'Out Late'),
        ('in_early', 'In Early'),
        ('out_early', 'Out Early'),
        ('normal', 'Normal'),
    ], string=u'Action type', default='normal',)

    @api.model
    def get_days_hours(self, employee_id, day):
        if isinstance(day, datetime):
            day = fields.Date.to_string(day)
        lines = self.search([
            ('employee_id', '=', employee_id),
            ('jour', '=', day),
        ], order='name asc')
        hours = 0.0
        tmp = False
        line = False
        for line in lines:
            if line.action == 'sign_in':
                tmp = fields.Datetime.from_string(line.name)
            elif line.action == 'sign_out':
                if not tmp:
                    tmp = fields.Datetime.from_string(
                        line.name[:10] + ' 00:00:00')
                tmp2 = fields.Datetime.from_string(line.name)
                hours += (tmp2 - tmp).seconds / 3600.
        if line and line.action == 'sign_in':
            tmp = fields.Datetime.from_string(line.name)
            tmp2 = fields.Datetime.from_string(
                line.name[:10] + ' 23:59:59')
            hours += (tmp2 - tmp).seconds / 3600.
        return hours > 0 and 1 or 0,  hours

    @api.model
    def create(self, vals):
        attendance = super(hr_attendance, self).create(vals)
        working_hours = attendance.employee_id.working_hours
        if working_hours:
            date = fields.Datetime.from_string(attendance.name)
            dayofweek = date.weekday()
            lines = self.env['resource.calendar.attendance'].search([
                ('calendar_id', '=', working_hours.id),
                ('dayofweek', '=', str(dayofweek)),
            ], order='hour_from asc')
            if lines:
                atts = self.search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('jour', '=', attendance.jour)
                ], order="name asc")
                self._recompute_gaps_helper(atts, lines)
        return attendance

    @api.model
    def _recompute_gaps_helper(self, atts, lines):
        times = [(x.hour_from, x.hour_to) for x in lines]
        first, time_first = False, times[0][0]
        last, time_last = False, times[-1][1]
        last_one = False
        for att in atts:
            att.gap = 0
            last_one = att
            att.action_state = 'normal'
            if not first and att.action == 'sign_in':
                first = att
            if att.action == 'sign_out':
                last = att
        if first and last:
            date_first = fields.Datetime.from_string(first.name)
            date_last = fields.Datetime.from_string(last.name)
            datetime_first = datetime(
                year=date_first.year,
                month=date_first.month,
                day=date_first.day,
                hour=int(time_first),
                minute=int((time_first - int(time_first)) * 60),
                second=0)
            datetime_last = datetime(
                year=date_last.year,
                month=date_last.month,
                day=date_last.day,
                hour=int(time_last),
                minute=int((time_last - int(time_last)) * 60),
                second=0)
            first_sign = datetime_first > date_first and 1 or -1
            last_sign = date_last > datetime_last and 1 or -1
            diff_first = datetime_first > date_first and \
                (datetime_first - date_first).seconds / 60 or \
                (date_first - datetime_first).seconds / 60
            diff_last = datetime_last > date_last and \
                (datetime_last - date_last).seconds / 60 or \
                (date_last - datetime_last).seconds / 60
            diff_first = diff_first * first_sign
            diff_last = diff_last * last_sign
            if last_one and last_one.action == 'sign_in':
                last_one.gap = 0
                last_one.action_state = 'normal'
            else:
                last.gap = diff_last
                last.action_state = diff_last > 0 and 'out_late' or diff_last < 0 and 'out_early' or 'normal'
            first.gap = diff_first
            first.action_state = diff_first > 0 and 'in_early' or diff_first < 0 and 'in_late' or 'normal'
