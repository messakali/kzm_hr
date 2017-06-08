# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

from odoo.exceptions import Warning


class hr_expense_expense(models.Model):
    _inherit = 'hr.expense'

    payroll_ok = fields.Boolean(
        string=u'Report à la paie', default=False, copy=False)
    payroll_date = fields.Date(string=u'Date de paie', readonly=True,  states={
                               'draft': [('readonly', False)], 'confirm': [('readonly', False)], 'accepted': [('readonly', False)]})
#     line_ids = fields.One2many(
#         states={'draft': [('readonly', False)], 'confirm': [('readonly', False)], })

    saisie_line_id = fields.Many2one('hr.saisie.line', string=u'Ligne de saisie',)
# 
#     @api.model
#     def force_paid(self):
#         for exp in self:
#             exp.message_post(_("Note de paie est marquée payée."))
#             exp.state = 'paid'
#         return True
# 
#     @api.model
#     def reserve_payroll(self):
#         for exp in self:
#             for line in exp.line_ids:
#                 if not line.product_id:
#                     raise Warning(
#                         _("La note de frais ne peut pas être reportée à la paie parce que le produit associé est obligatoire"))
#                 product = line.product_id
#                 if not product.payroll_type or (product.payroll_type == 'rubrique' and not product.payroll_rubrique_id) or (product.payroll_type == 'avance' and not product.payroll_avance_id):
#                     raise Warning(
#                         _("Veuillez spécifier un élément de salaire pour l'article [%s]" % product.name))
#                 if product.payroll_type == 'rubrique':
#                     line.rubrique_id = product.payroll_rubrique_id.id
#                 elif product.payroll_type == 'avance':
#                     line.avance_id = product.payroll_avance_id.id
#                 elif product.payroll_type == 'avantage':
#                     line.avantage_id = product.payroll_avantage_id.id
#                 elif product.payroll_type == 'majoration_net':
#                     line.payroll_type = 'majoration_net'
#                 elif product.payroll_type == 'retenu_net':
#                     line.payroll_type = 'retenu_net'
#                 else:
#                     raise Warning(
#                         _("Le type [%s] est introuvable" % product.payroll_type))
#             if not exp.payroll_date:
#                 exp.payroll_date = fields.Date.today()
#             exp.payroll_ok = True
#             exp.message_post(_("Les lignes de note de frais sera reporté à la paie."))
#             exp.state = 'paid'
#         return True
# 
#     @api.model
#     def expense_accept(self):
#         res = super(hr_expense_expense, self).expense_accept()
#         for exp in self:
#             for line in exp.line_ids:
#                 if not line.product_id:
#                     raise Warning(
#                         _("La note de frais ne peut pas être validée car un article est obligatoire"))
#         return res
# 
#     @api.model
#     def action_move_create(self):
#         res = super(hr_expense_expense, self).action_move_create()
#         self.payroll_ok = False
#         return res
# 
# 
# class hr_expense_line(models.Model):
#     _inherit = 'hr.expense.line'
# 
#     rubrique_id = fields.Many2one('hr.rubrique', string=u'Rubrique',)
#     avance_id = fields.Many2one('hr.avance', string=u'Avance',)
#     avantage_id = fields.Many2one('hr.avantage', string=u'Avantage',)
#     payroll_type = fields.Selection([
#         ('majoration_net', 'Majoration sur le salaire net'),
#         ('retenu_net', 'Retenu sur le salaire net'),
#     ], string=u'Operation on the net',)
#     payroll_date = fields.Date(
#         string=u'Date', related='expense_id.payroll_date', store=True)
