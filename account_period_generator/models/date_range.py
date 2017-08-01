# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _, exceptions


class DateRange(models.Model):
    _inherit = "date.range"

    fiscal_year = fields.Boolean(related='type_id.fiscal_year')
    
    def create_period(self, interval=1):
        
        if self.type_id.fiscal_year:
            ds = datetime.strptime(self.date_start, '%Y-%m-%d')
            period = self.env.ref('account_period_generator.period').id
            while ds.strftime('%Y-%m-%d') < self.date_end:
                de = ds + relativedelta(months=1, days=-1)

                if de.strftime('%Y-%m-%d') > self.date_end:
                    de = datetime.strptime(self.date_end, '%Y-%m-%d')

                self.create({
                    'name': ds.strftime('%m/%Y'),
                    'type_id': period,
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_end': de.strftime('%Y-%m-%d'),
                    'company_id': self.env['res.company']._company_default_get().id,
                })
                ds = ds + relativedelta(months=1)
        