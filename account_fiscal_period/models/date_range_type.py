# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions


class DateRangeType(models.Model):
    _inherit = "date.range.type"

    fiscal_period = fields.Boolean(string='Is fiscal period ?', default=False)

    def unlink(self):
        """
        Cannot delete a date_range_type with 'fiscal_period' flag = True
        """
        for rec in self:
            if rec.fiscal_period:
                raise exceptions.ValidationError(
                    ('Vous ne pouvez pas supprimer un type de flag fiscal_year"')
                )
            else:
                super(DateRangeType, rec).unlink()