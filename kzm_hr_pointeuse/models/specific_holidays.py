# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime


class Holidays(models.Model):
    _name = "specific.holidays"
    _description = "specific.holidays"

    name = fields.Char(u"Description", required=True)
    start_date = fields.Date(u"Date début", required=True)
    end_date = fields.Date(u"Date fin", required=True)
    company_id = fields.Many2one(comodel_name="res.company", ondelete='cascade', string=_("Society"),
                                 required=True,
                                 default=lambda self: self.env.company)
    sous_ferme_id = fields.Many2one(comodel_name="sub.farm",
                                    default=False, string=_("Sub farm"), required=False)


    def is_free_date(self, odoo_date):
        if odoo_date:
            dt = fields.Datetime.from_string(odoo_date)
            dt = fields.Date.to_string(dt.date())
            free_days = self.env['specific.holidays'].search([('start_date','>=', dt),('start_date','<=', dt)])
            if len(free_days)>0:
                return True
        return False

class Pause(models.Model):
    _name = "specific.pause"
    _description = "specific.pause"

    def _compute_decs(self):
        for o in self:
            db, df = "NN:NN", "NN:NN"
            if o.start_hour:
                db = ("%s" % (int(o.start_hour))).zfill(2) + ":" + (
                "%s" % (int((o.start_hour - int(o.start_hour)) * 60))).zfill(2)
            if o.end_hour:
                df = ("%s" % (int(o.end_hour))).zfill(2) + ":" + (
                "%s" % (int((o.end_hour - int(o.end_hour)) * 60))).zfill(2)
            o.desc = db + " - " + df

    name = fields.Char(u"Description", required=True)
    start_hour = fields.Float(u"Heure début", required=True)
    end_hour = fields.Float(u"Heure fin", required=True)
    desc = fields.Char("Des", compute=_compute_decs)
    company_id = fields.Many2one(comodel_name="res.company", ondelete='cascade', string=_("Society"),
                                 required=True,
                                 default=lambda self: self.env.company)
    sous_ferme_id = fields.Many2one(comodel_name="sub.farm",
                                    default=False, string=_("Sub farm"), required=False)


    def get_pause_text(self):
        return "; ".join([l.desc for l in self.env['specific.pause'].search([])])
