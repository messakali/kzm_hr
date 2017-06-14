# encoding: utf-8

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp

from odoo.addons.kzm_base.controllers.tools import remove_accent


class hr_cotisation(models.Model):
    _name = 'hr.cotisation'

    @api.onchange('name')
    def _onchange_name(self) :
        if self.name and not self.code:
            self.code = remove_accent(self.name.strip().replace(' ','_')).upper()

    sequence = fields.Integer(string=u'Séquence', default=0)
    code = fields.Char(string=u'Code', size=64,  required=True)
    name = fields.Char(string=u'Nom', size=64, required=True)
    rate_salariale = fields.Float(
        string=u'Taux salariale',
        digits=dp.get_precision('Account'), required=True, default=0)
    rate_patronale = fields.Float(
        string=u'Taux patronale',
        digits=dp.get_precision('Account'), required=True, default=0)
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

    group_id = fields.Many2one('hr.cotisation.group', string=u'Grouper dans le bulletin',  required=True, )
    ledger_id = fields.Many2one('hr.cotisation.ledger', string=u'Grouper dans le livre d epaie',  required=True, )

    show_on_payslip = fields.Selection([
        ('never', 'Jamais'),
        ('ifnotnull', 'Si différent du zéro'),
        ('always', 'Toujours'),
    ], string=u'Affichage sur les bulletins', required=True, default='ifnotnull')

    analytic_account_id = fields.Many2one(
        'account.analytic.account', string=u'Compte analytique',)
    account_tax_id = fields.Many2one('account.tax', string=u'Code TVA',)
    account_debit = fields.Many2one(
        'account.account', string=u'Compte du débit')
    account_credit = fields.Many2one(
        'account.account', string=u'Compte du crédit')

    type_cotisation = fields.Selection([
    ('cnss', 'CNSS'),
    ('cimr', 'CIMR'),
    ('assurance', 'Assurance retraite'),
    ('autre', 'Autre'),
    ], string=u'Type de cotisation', required=True,  )

    @api.one
    @api.depends("rate_salariale")
    def _compute_rate_inline(self):
        main = int(self.rate_salariale)
        precision = int((self.rate_salariale - main)*100)
        self.rate_salariale_inline = str(main).rjust(2,'0')+str(precision).rjust(2,'0')

    rate_salariale_inline = fields.Char(string=u'Rate inline', size =  4 ,  compute='_compute_rate_inline', store=True,   )
    @api.model
    def create(self, vals):
        cotisation_id = super(hr_cotisation, self).create(vals)
        self.env['hr.axe'].create({'cotisation_id': cotisation_id.id})
        return cotisation_id

    @api.multi
    def write(self, vals):
        res = super(hr_cotisation, self).write(vals)
        for cotisation in self:
            axes = self.env['hr.axe'].search(
                [('cotisation_id', '=', cotisation.id)])
            if axes:
                for axe in axes:
                    axe.write({'cotisation_id': cotisation.id})
            else:
                axes.create({'cotisation_id': cotisation.id})
        return res

    @api.multi
    def unlink(self):
        for cotisation in self:
            axes = self.env['hr.axe'].search(
                [('cotisation_id', '=', cotisation.id)])
            if axes:
                for axe in axes:
                    axe.unlink()
        return super(hr_cotisation, self).unlink()

class hr_cotisation_group(models.Model):
    _name = 'hr.cotisation.group'
    _description = 'Groupe'

    name = fields.Char(string=u'Nom', size =  64 ,  required=True, )
    code = fields.Char(string=u'Code', size =  64 ,  required=True, )
    sequence = fields.Integer(string=u'Séquence', default=0)

class hr_cotisation_ledger(models.Model):
    _name = 'hr.cotisation.ledger'
    _description = 'Livre de paie'

    name = fields.Char(string=u'Nom', size =  64 ,  required=True, )
    code = fields.Char(string=u'Code', size =  64 ,  required=True, )
    sequence = fields.Integer(string=u'Séquence', default=0)

    show_on_ledger = fields.Selection([
        ('never', 'Jamais'),
        ('ifnotnull', 'Si différent du zéro'),
        ('always', 'Toujours'),
    ], string=u'Affichage dans le livre de paie', required=True, default='ifnotnull')
