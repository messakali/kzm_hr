from odoo import api, fields, models, _


class ContractType(models.Model):
    _name = 'hr.contract.type'
    _description = 'Type Contrat'
    _order = 'sequence, id'

    name = fields.Char(string='Type contrat', required=True, translate=True)
    sequence = fields.Integer(help="Gives the sequence when displaying a list of Contract.", default=10)


class Contract(models.Model):
    _inherit = 'hr.contract'
    # _description = 'Contract'
    # _inherit = ['mail.thread', 'mail.activity.mixin']

    type_id = fields.Many2one('hr.contract.type', string="Type contrat", required=True,
                              default=lambda self: self.env['hr.contract.type'].search([], limit=1))
