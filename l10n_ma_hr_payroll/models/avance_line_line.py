# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning
from dateutil.relativedelta import relativedelta


class hr_avance_line_line(models.Model):
    _name = 'hr.avance.line.line'
    _description = 'Lignes d\'avance'

    @api.one
    @api.depends("avance_line_id", "echeance_ttc", "interest_tva")
    def _compute_amount(self):
        if self.avance_line_id:
            if self.avance_line_id.avance_id.interest_rate:
                self.amount = self.interest_ttc
            else:
                self.amount = self.avance
        else:
            self.amount = 0.0

    @api.one
    @api.depends("interest", "interest_tva")
    def _compute_interest_ttc(self):
        self.interest_ttc = self.interest + self.interest_tva

    interest_ttc = fields.Float(
        string=u'Intérêt TTC', digits=dp.get_precision('Account'), compute='_compute_interest_ttc', store=True,   )

    avance = fields.Float(
        string=u'Avance', digits=dp.get_precision('Account'),)


    avance_line_id = fields.Many2one(
        'hr.avance.line', string=u'Ligne d\'avance', required=True, ondelete='cascade',  )
    date = fields.Date(string=u'Date', required=True,)
    capital_restant_before = fields.Float(string=u'CRD DP', digits=dp.get_precision(
        'Account'), help=u'Capital restant dû au début de la période',)
    capital_restant_after = fields.Float(string=u'CRD FP', digits=dp.get_precision(
        'Account'), help=u'Capital restant dû à la fin de la période',)
    interest = fields.Float(
        string=u'Intérêt', digits=dp.get_precision('Account'),)
    interest_tva = fields.Float(
        string=u'Intérêt TVA', digits=dp.get_precision('Account'),)
    amortissement = fields.Float(
        string=u'Amortissement', digits=dp.get_precision('Account'),)
    echeance_ht = fields.Float(
        string=u'Echéance HT', digits=dp.get_precision('Account'),)
    echeance_ttc = fields.Float(
        string=u'Echéance TTC', digits=dp.get_precision('Account'),)

    amount = fields.Float(string=u'Montant', digits=dp.get_precision(
        'Account'), compute='_compute_amount', store=True)
    move_id = fields.Many2one(
        'account.move', string=u'Écriture comptable', copy=False,)
    state = fields.Selection([
        ('draft', u'Brouillon'),
        ('cancel', u'Annulé'),
        ('done', u'Terminé'),
    ], string=u'État', required=True, default='draft',)

    avance_state = fields.Selection(related='avance_line_id.state',   )

    saisie_line_id = fields.Many2one('hr.saisie.line', string=u'Ligne de saisie',)


    @api.multi
    def set_done(self):
        for line in self:
            line.state = 'done'

    @api.multi
    def set_draft(self):
        for line in self:
            line.state = 'draft'

    @api.multi
    def set_cancel(self):
        for line in self:
            if line.move_id:
                line.move_id.unlink()
            line.state = 'cancel'

    @api.multi
    def add_month(self):
        self.ensure_one()
        new_date = fields.Datetime.from_string(
            self.date) + relativedelta(months=1)
        self.date = fields.Datetime.to_string(new_date)

    @api.multi
    def minus_month(self):
        self.ensure_one()
        new_date = fields.Datetime.from_string(
            self.date) + relativedelta(months=-1)
        self.date = fields.Datetime.to_string(new_date)

    @api.model
    def unlink(self):
        for obj in self:
            if obj.state == 'done':
                raise Warning(
                    _('La ligne ne peut pas être supprimée car elle est validée'))
        super(hr_avance_line_line, self).unlink()
