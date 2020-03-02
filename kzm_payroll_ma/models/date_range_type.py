# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DateRangeType(models.Model):
    _inherit = "date.range.type"

    @api.constrains("company_id")
    def _check_company_id(self):
        pass
