# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions

from datetime import datetime
from dateutil.relativedelta import relativedelta

class DateRange(models.Model):
    _inherit = "date.range"

    period_ids = fields.One2many(comodel_name="date.range", inverse_name="fiscal_year_id", string=u"Périodes", required=False, )
    fiscal_year_id = fields.Many2one(comodel_name="date.range", string=u"Exercice fiscal", required=False, )
    is_fiscal_year = fields.Boolean('Is fiscal year?',compute="is_fiscal_year",store=True)
    previous_fiscal_year = fields.Many2one(comodel_name="date.range", string=u"Exercice fiscal précedant", required=False, )
    next_fiscal_year = fields.Many2one(comodel_name="date.range", string="Exercice fiscal suivant", required=False, )

    @api.multi
    @api.depends('type_id')
    def is_fiscal_year(self):
        for record in self:
            is_fiscal_year = False
            if record.type_id.is_fisacal_year:
                is_fiscal_year = True
            record.is_fiscal_year = is_fiscal_year

    @api.multi
    def create_period3(self,context):
        return self.create_period(context,3)

    @api.multi
    def create_period(self,context, interval=1):

        period_obj = self.env['date.range']
        for fy in self:
            #fy.period_ids.unlink()
            ds = fy.date_start
            date_stop = fy.date_end

            while ds < date_stop:
                de = ds + relativedelta(months=interval, days=-1)
                if date_stop < de:
                    de = fy.date_stop
                period_obj.create({
                    'name': ds.strftime('%m/%Y'),
                    # 'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_end': de.strftime('%Y-%m-%d'),
                    'type_id':self.env.ref('account_fiscal_period.fiscalperiod').id,
                    'fiscal_year_id': fy.id,
                })
                ds = ds + relativedelta(months=interval)
        return True
