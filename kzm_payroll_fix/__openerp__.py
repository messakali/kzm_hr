# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 HESATEC (<http://www.hesatecnica.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name"        : "KZM Payroll FIXME",
    "version"     : "1.0",
    "category"    : "Paie marocaine",
    'complexity'  : "normal",
    "author"      : "Karizma Conseil",
    "website"     : "http://www.karizma.ma",
    "depends"     : ["l10n_ma_hr_payroll"],
    "summary"     : "Karizma Conseil Odoo Localisation",
    "description" : """

Adapting some payroll features
==============================

With this module, it will possible to manually enter all charged person parameters
 - For the new entries (hr.employee), the onchange method will recompute charged parameters
 - Empoyee identification not based on initial company

""",
    "data" : [
        ],

    "application": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
