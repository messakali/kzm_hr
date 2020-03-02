# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    zip = fields.Char('Zip', change_default=True)
    city = fields.Char('City')
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')

    street_secondary = fields.Char('Street')
    street2_secondary = fields.Char('Street2')
    zip_secondary = fields.Char('Zip', change_default=True)
    city_secondary = fields.Char('City')
    state_secondary_id = fields.Many2one("res.country.state", string='State')
    country_secondary_id = fields.Many2one('res.country', string='Country')
