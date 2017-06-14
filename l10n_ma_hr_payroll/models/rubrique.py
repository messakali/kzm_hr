# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, _
from odoo.osv import expression

from odoo.addons.kzm_base.controllers.tools import remove_accent

# salariale ==> exonore
# salariale plafond  = > taxable plafonne sans reste
# patronale =>  taxable non plafonnee
# patronale plafond => taxable plafonne avec reste


class hr_rubrique(models.Model):
    _name = 'hr.rubrique'
    _description = 'Rubrique'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            domain = ['|',('name', operator, name),('code', operator, name)]
            ids = self.search(expression.AND([domain, args]), limit=limit)
        else:
            ids = self.search(args, limit=limit)
        return ids.name_get()

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
    ], string=u'Exonération', required=True)

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
        string=u'Plafond d\'exonération',
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

    code_python = fields.Text(string=u'Code', default="""#taux_horaire : le salaire horaire
#taux_journalier : le salaire journalier
#base_salariale : la base salariale
#nombre_de_jours : Nombre de jours travaille
#nombre_de_heures : Nombre d'heures travaille
#anciennete : Anciienete en annees
#montant_anciennete : La prime d'anciennete
#heures_supp : Total des heures supplementaires
#smig : SMIG Horaire
#urbain : Test si habitation urbaine ou non
#nbr_enfants : Nombre des enfants
#plafond_ind_kilometrique : Plafond de l'indemnite kilometrique
#Remarique : Il est possible d'utiliser toutes les expressions et les variables disponibles pour une regle salariale
#Exemples :
#    plafond = 0.1 * base_salariale
#    plafond = 0.1 * (categories.BASE_SALARIALE + anciennete + heures_supp)
#    plafond =
    """,  )

    plafond_salariale_type = fields.Selection([
        ('fix', 'Fixe'),
        ('rate', 'Taux sur la base'),
        ('code', 'Code'),
    ], string=u'Type de plafond salarial', default='fix', required=True, )

    plafond_patronale_type = fields.Selection([
        ('fix', 'Fixe'),
        ('rate', 'Taux sur la base'),
    ], string=u'Type de plafond patronale', default='fix', required=True, )

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
    account_tax_id = fields.Many2one('account.tax', string=u'Code TVA',)
    account_debit = fields.Many2one(
        'account.account', string=u'Compte du débit')
    account_credit = fields.Many2one(
        'account.account', string=u'Compte du crédit')

    export_ok = fields.Boolean(string=u'Export/Import CSV', default=True,)
    active = fields.Boolean(string=u'Actif', default=True,    )
    auto_compute = fields.Boolean(string=u'Calcul automatique', default=False,    )
    compute_code = fields.Text(string=u'Code',  default="""#taux_horaire : le salaire horaire
#taux_journalier : le salaire journalier
#base_salariale : la base salariale
#nombre_de_jours : Nombre de jours travaille
#nombre_de_heures : Nombre d'heures travaille
#anciennete : Anciienete en annees
#montant_anciennete : La prime d'anciennete
#heures_supp : Total des heures supplementaires
#smig : SMIG Horaire
#urbain : Test si habitation urbaine ou non
#nbr_enfants : Nombre des enfants
#plafond_ind_kilometrique : Plafond de l'indemnite kilometrique
#Remarique : Il est possible d'utiliser toutes les expressions et les variables disponibles pour une regle salariale
#Exemples :
#    value = 0.1 * base_salariale
#    value = 0.1 * (categories.BASE_SALARIALE + anciennete + heures_supp)
#    value =
    """,  )


    @api.model
    def create(self, vals):
        rubrique_id = super(hr_rubrique, self).create(vals)
        self.env['hr.axe'].create({'rubrique_id': rubrique_id.id})
        return rubrique_id

    @api.multi
    def write(self, vals):
        res = super(hr_rubrique, self).write(vals)
        for rubrique in self:
            axes = self.env['hr.axe'].search(
                [('rubrique_id', '=', rubrique.id)])
            if axes:
                for axe in axes:
                    axe.sudo().write({'rubrique_id': rubrique.id})
            else:
                axes.create({'rubrique_id': rubrique.id})
        return res

    @api.multi
    def unlink(self):
        for rubrique in self:
            axes = self.env['hr.axe'].search(
                [('rubrique_id', '=', rubrique.id)])
            if axes:
                for axe in axes:
                    axe.unlink()
        return super(hr_rubrique, self).unlink()
