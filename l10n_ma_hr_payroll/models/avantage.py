# encoding: utf-8

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp

from odoo.addons.kzm_base.controllers.tools import remove_accent


class hr_avantage(models.Model):
    _name = 'hr.avantage'
    _description = 'Avantage'

    @api.onchange('name')
    def _onchange_name(self) :
        if self.name and not self.code:
            self.code = remove_accent(self.name.strip().replace(' ','_')).upper()

    @api.one
    @api.depends('rate_type')
    def _compute_rates(self):
        if self.rate_type == 'imp':
            self.rate_patronale = 100
            self.rate_salariale = 0
        else:
            self.rate_patronale = 0
            self.rate_salariale = 100

    rate_type = fields.Selection([
        ('exo', 'Exonoré'),
        ('imp', 'Imposable'),
    ], string=u'Exonération', required=True, default='exo')

    sequence = fields.Integer(string=u'Séquence', default=0)
    code = fields.Char(string=u'Code', size=64,  required=True)
    name = fields.Char(string=u'Nom', size=64, required=True)
    rate_salariale = fields.Float(
        string=u'Taux',
        digits=dp.get_precision('Account'),
        compute='_compute_rates',
        store=True,
    )
    rate_patronale = fields.Float(
        string=u'Taux',
        digits=dp.get_precision('Account'),
        compute='_compute_rates',
        store=True,
    )
    plafond_salariale = fields.Float(
        string=u'Plafond salarial',
        digits=dp.get_precision('Account'),
        required=True,
        default=0)
    plafond_patronale = fields.Float(
        string=u'Plafond patronal',
        digits=dp.get_precision('Account'),
        required=True,
        default=0)
    contribution_id = fields.Many2one(
        'hr.contribution.register', string=u'Contribution',)

    plafond_salariale_type = fields.Selection([
        ('fix', 'Fixe'),
        ('rate', 'Taux sur la base'),
    ], string=u'Type du plafond salarial',)

    plafond_patronale_type = fields.Selection([
        ('fix', 'Fixe'),
        ('rate', 'Taux sur la base'),
    ], string=u'Type du plafond patronal',)

    show_on_payslip = fields.Selection([
        ('never', 'Jamais'),
        ('ifnotnull', 'Si différent du zéro'),
        ('always', 'Toujours'),
    ], string=u'Affichage sur les bulletins', required=True, default='ifnotnull')

    show_on_ledger = fields.Selection([
        ('never', 'Jamais'),
        ('ifnotnull', 'Si différent du zéro'),
        ('always', 'Toujours'),
    ], string=u'Affichage dans le livre de paie', required=True, default='ifnotnull')

    can_reset = fields.Boolean(string=u'Peut être réinitialisé', default=False)
    can_request = fields.Boolean(string=u'Peut être demandé', default=False)

    analytic_account_id = fields.Many2one(
        'account.analytic.account', string=u'Compte analytique',)
    account_tax_id = fields.Many2one('account.tax.code', string=u'Code TVA',)
    account_debit = fields.Many2one(
        'account.account', string=u'Compte du débit', domain=[('type', '!=', 'view')],)
    account_credit = fields.Many2one(
        'account.account', string=u'Compte du crédit', domain=[('type', '!=', 'view')],)

    export_ok = fields.Boolean(string=u'Export/Import CSV', default=True,)
    active = fields.Boolean(string=u'Actif', default=True,    )

    type = fields.Selection([
        ('argent', 'En argent'),
        ('nature', 'En nature'),
    ], string=u'Type', required=True)

    @api.model
    def create(self, vals):
        avantage_id = super(hr_avantage, self).create(vals)
        self.env['hr.axe'].create({'avantage_id': avantage_id.id})
        return avantage_id

    @api.multi
    def write(self, vals):
        res = super(hr_avantage, self).write(vals)
        for avantage in self:
            axes = self.env['hr.axe'].search(
                [('avantage_id', '=', avantage.id)])
            if axes:
                for axe in axes:
                    axe.sudo().write({'avantage_id': avantage.id})
            else:
                axes.create({'avantage_id': avantage.id})
        return res

    @api.multi
    def unlink(self):
        for avantage in self:
            axes = self.env['hr.axe'].search(
                [('avantage_id', '=', avantage.id)])
            if axes:
                for axe in axes:
                    axe.unlink()
        return super(hr_avantage, self).unlink()
