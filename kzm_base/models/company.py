# encoding: utf-8
##############################################################################
#
#    Localisation marocaine module for OpenERP, Localisation marocaine, Les bases
#    Copyright (C) 2014 (<http://www.example.org>) Anonym
#
#    This file is a part of Localisation marocaine
#
#    Localisation marocaine is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Localisation marocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, api, fields, _
from ..controllers import tools as T
from odoo.exceptions import Warning

import odoo.addons.decimal_precision as dp


# The two variable are related to kzm_ma_tax/models/tax_engine.py
# Think to update all
ENCAISSEMENT = 'payments'
DEBIT = 'invoices'


class res_company(models.Model):
    _inherit = 'res.company'
    _description = 'Company'

#     @api.multi
#     def fix_accounts_reconciliation(self):
#         accounts = self.env['account.account'].search([('reconcile', '=', False), ('type', '!=', 'view')]).filtered(
#             lambda r: r.code.startswith('34') or r.code.startswith('44'))
#         for account in accounts:
#             account.reconcile = True

#     @api.multi
#     def fix_fr_lang(self):
#         langs = self.env['res.lang'].search([('code', '=', 'fr_FR')])
#         for lang in langs:
#             lang.write({
#                 'date_format' : '%d/%m/%Y',
#                 'grouping' : '[3,3,3,-1]',
#                 'thousands_sep' : u'\u00A0',
#             })

#     @api.multi
#     def fix_config_general(self):
#         configs = self.env['base.config.settings'].search([])
#         for config in configs:
#             config.execute()

#     @api.multi
#     def get_company_root(self):
#         company = self.env.user.company_id
#         while company.parent_id:
#             company = company.parent_id
#         return company

#     @api.one
#     @api.depends("parent_id")
#     def _compute_main_company(self):
#         main_company_id = self.sudo()
#         while main_company_id.parent_id:
#             main_company_id = main_company_id.parent_id
#         self.main_company_id = main_company_id
# 
#     main_company_id = fields.Many2one(
#         'res.company', string=u'Main company', compute='_compute_main_company',)

#     @api.one
#     @api.depends('fp_id')
#     def _compute_fp_taux(self):
#         if self.fp_id:
#             self.fp_taux = self.fp_id.rate
#         else:
#             self.fp_taux = 0

#     @api.one
#     @api.depends('fp_taux')
#     def _compute_fp_taux_str(self):
#         self.fp_taux_str = str(self.fp_taux) + ' %'

    patente = fields.Char(string=u'Patente', size=64, help='Patente')
    forme_juridique_id = fields.Many2one(
        'res.company.forme.juridique', string=u'Forme juridique',)
    activity = fields.Char(string=u'Activity', size=64, help='Activity')
    cnss = fields.Char(string=u'CNSS', size=64, help='CNSS')
    cimr = fields.Char(string=u'CIMR', size=64, help='CIMR')
    vat = fields.Char(string=u'Identifiant fiscal', size=64,)
#     company_registry = fields.Char(string=u'Registre de commerce', size=64,)
    identifiant_tp = fields.Char(string=u'Identifiant TP', size=64,)
    commune_id = fields.Many2one('l10n.ma.commune', string=u'Commune',)
    declaration_type = fields.Selection(
        [('m', 'Mensuelle'), ('t', 'Trimestrielle')], 'Type de la declaration', required=True, default='m')
    based_on = fields.Selection(
        [(DEBIT, 'Debit'), (ENCAISSEMENT, 'Encaissement'), ], 'Regime', required=True, default=ENCAISSEMENT)
    
#     cf_plafond = fields.Float('Plafond des charges familiales', digits_compute=dp.get_precision(
#         'Local 2'), required=True, default=180,)
#     af_plafond = fields.Float('Plafond des charges familiales', digits_compute=dp.get_precision(
#         'Local 2'), required=True, default=180,)
#     cf_amount = fields.Float('Montant pour une charge familiale', digits_compute=dp.get_precision(
#         'Local 2'), required=True, default=30,)
#     fp_plafond = fields.Float('Plafond des frais professionels', digits_compute=dp.get_precision(
#         'Local 2'), required=True, default=2500,)
#     fp_taux = fields.Float('Taux des frais professionels', digits_compute=dp.get_precision(
#         'Local 4'),  compute='_compute_fp_taux', store=True,)
#     fp_id = fields.Many2one(
#         'l10n.ma.fp', string=u'Taux des frais professionels', required=False,
#         default=lambda self: self.env['l10n.ma.fp'].search([('rate', '=', 20)], limit=1),)
#     fp_taux_str = fields.Char('Taux des frais professionels', size=64,
#                               compute='_compute_fp_taux_str', store=True, readonly=True,)
#     nbr_af1_plafond = fields.Integer(
#         string=u'Plafond de nombre des allocations familiales (1ere tranche)', default=3, required=True)
#     nbr_af2_plafond = fields.Integer(
#         string=u'Plafond de nombre des allocations familiales (2eme tranche)', default=6, required=True)
#     af1_amount = fields.Float('Montant des allocations familiales (1ere tranche)', digits_compute=dp.get_precision(
#         'Local 2'), required=True, default=200,)
#     af2_amount = fields.Float('Montant des allocations familiales (2eme tranche)', digits_compute=dp.get_precision(
#         'Local 2'), required=True, default=36,)
    
#     code_digits = fields.Integer('# digits', required=True, default=0)
#     code_digits_min = fields.Integer('# digits min', readonly=True,)

#     initial = fields.Char(string=u'Initial', size=64,)
# 
#     cnss_day_limit = fields.Integer(string=u'Dernier jour de la regularisation', default=10,  required=True,  )
# 
# 
#     _sql_constraints = [
#         ('initial_unique', 'UNIQUE (initial)',
#          'The initial of the company must be unique !'),
#     ]

#     @api.one
#     def process_code_digits(self):
#         # FIXME: Trim should be auto and check 5141 problem
#         accounts = self.env['account.account'].search(
#             [('company_id', '=', self.id)])
# #         for account in accounts :
# #             if account.type <> 'view' :
# #                 code = int(account.code[::-1])
# #                 code = str(code)[::-1]
# #                 if len(code) > self.code_digits :
# #                     raise Warning(_('The code [%s] block the operation.\nTry to trim it firstly to %s digits.') % (code, self.code_digits,))
#         for account in accounts:
#             if account.type <> 'view':
#                 part1 = account.code[:self.code_digits_min - 1]
#                 part2 = account.code[self.code_digits_min - 1:]
#                 part2 = part2.strip('0')
#                 code = part1 + '0' * \
#                     (self.code_digits - len(str(part1)) - len(part2)) + part2
#                 account.code = code

#     @api.one
#     @api.constrains('fp_taux', 'code_digits')
#     def _check_taux(self):
#         if self.fp_taux < 0 or self.fp_taux > 100:
#             raise Warning(_('Le taux doit etre compris entre 0 et 100'))
#         if self.code_digits < self.code_digits_min:
#             raise Warning(
#                 _('Le nombre de chiffre doitre superieur a %s') % self.code_digits_min)


class res_company_forme_juridique(models.Model):
    _name = 'res.company.forme.juridique'
    _description = 'Formes juridiques'

    name = fields.Char(string=u'Nom', size=64, required=True,)
    code = fields.Char(string=u'Code', size=64, required=True,)
