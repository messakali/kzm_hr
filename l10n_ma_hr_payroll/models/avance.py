# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, _
from odoo.addons.kzm_base.controllers.tools import remove_accent


class hr_avance(models.Model):
    _name = 'hr.avance'
    _description = 'Avances'

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
        string=u'Plafond exonération',
        digits=dp.get_precision('Account'),
        required=True,
        default=0)
    plafond_patronale = fields.Float(
        string=u'Plafond taxable',
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
    ], string=u'Type de plafond patronale',)

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

    is_retained = fields.Boolean(
        string=u'Est une base de l\'IR', default=True)
    can_reset = fields.Boolean(string=u'Peut être réinitialisé', default=False)
    can_request = fields.Boolean(string=u'Peut être demandé', default=False)
    instant_move = fields.Boolean(string=u'Générer l\'écriture comptable instantanément', default=True)

    analytic_account_id = fields.Many2one(
        'account.analytic.account', string=u'Compte analytique',)
    account_tax_id = fields.Many2one('account.tax', string=u'Code TVA',)
    account_debit = fields.Many2one(
        'account.account', string=u'Compte du débit')
    account_credit = fields.Many2one(
        'account.account', string=u'Compte du crédit')

    interest_rate = fields.Float(
        string=u'Taux d\'intérêt', digits=dp.get_precision('Account'), default=0)

    csv_erase = fields.Boolean(string=u'Écraser les données par les données du fichier CSV', default=False,)
    export_ok = fields.Boolean(string=u'Export/Import CSV', default=True,)
    active = fields.Boolean(string=u'Actif', default=True,    )

    @api.model
    def create(self, vals):
        avance_id = super(hr_avance, self).create(vals)
        self.env['hr.axe'].create({'avance_id': avance_id.id})
        return avance_id

    @api.multi
    def write(self, vals):
        res = super(hr_avance, self).write(vals)
        for avance in self:
            axes = self.env['hr.axe'].search(
                [('avance_id', '=', avance.id)])
            if axes:
                for axe in axes:
                    axe.sudo().write({'avance_id': avance.id})
            else:
                axes.create({'avance_id': avance.id})
        return res

    @api.multi
    def unlink(self):
        for avance in self:
            axes = self.env['hr.axe'].search(
                [('avance_id', '=', avance.id)])
            if axes:
                for axe in axes:
                    axe.unlink()
        return super(hr_avance, self).unlink()
