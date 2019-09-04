# -*- coding: utf-8 -*-

from odoo import api, fields, models


class DateRangeType(models.Model):
    _name = "date.range.type"
    _description = "Date Range Type"

    @api.model
    def _default_company(self):
        return self.env['res.company']._company_default_get('date.range')

    name = fields.Char(required=True, translate=True)
    allow_overlap = fields.Boolean(
        help="If sets date range of same type must not overlap.",
        default=False)
    active = fields.Boolean(
        help="The active field allows you to hide the date range without "
        "removing it.", default=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', index=True,
        default=_default_company)

    _sql_constraints = [
        ('date_range_type_uniq', 'unique (name,company_id)',
         'A date range type must be unique per company !')]
