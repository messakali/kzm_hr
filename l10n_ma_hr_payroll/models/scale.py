# encoding: utf-8

from odoo import models, fields, api, _
from odoo.exceptions import Warning
import odoo.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)


class hr_scale_seniority(models.Model):
    _name = 'hr.scale.seniority'
    _order = 'age_from'

    @api.model
    def get_seniority_rate(self, age):
        age = int(age)
        for seniority in self.search([]):
            if seniority.age_from <= age and age <= seniority.age_to:
                return seniority.rate
        raise Warning(
            _('Erreur lors du calcul de l\'ancienneté, aucune ligne trouvé pour la base [%d]') % age)

    @api.model
    def get_seniority_leave(self, age):
        age = int(age)
        for seniority in self.search([]):
            if seniority.age_from <= age and age <= seniority.age_to:
                return seniority.leave
        raise Warning(
            _('Erreur lors du calcul de l\'ancienneté, aucune ligne trouvé pour la base [%d]') % age)

    @api.one
    @api.depends("age_from", "age_to")
    def _compute_name(self):
        self.name = _('De') + ' ' + str(self.age_from) + \
            ' ' + _('À') + ' ' + str(self.age_to)

    name = fields.Char(
        string=u'Nom', size=64, compute='_compute_name', store=True)
    age_from = fields.Float(
        string=u'De', digits=dp.get_precision('Seniority'), required=True)
    age_to = fields.Float(
        string=u'À', digits=dp.get_precision('Seniority'), required=True)
    rate = fields.Float(
        string=u'Taux', digits=dp.get_precision('Seniority'), required=True)
    deduction = fields.Float(
        string=u'Déduction', digits=dp.get_precision('Seniority'), required=True,)
    leave = fields.Float(
        string=u'Nb. congé par mois', digits=dp.get_precision('Salary Rate'), required=True,)
    @api.multi
    @api.depends('leave')
    def _compute_leave_year(self):
        for obj in self:
            obj.leave_year = obj.leave * 12
    leave_year = fields.Float(
        string=u'Nb. congé par année', digits=dp.get_precision('Salary Rate'), compute='_compute_leave_year',)


class hr_scale_ir(models.Model):
    _name = 'hr.scale.ir'
    _order = 'amount_from'

    @api.model
    def get_ir(self, base, nbr):
        base *= 12 / nbr
        base = int(base)
        for ir in self.search([]):
            if ir.amount_from <= base and base <= ir.amount_to:
                return ((base * (ir.rate / 100.) - ir.deduction) / 12) * nbr
        _logger.error(
            'Error when computing the IR, no line found for the base [%d]' % base)
        raise Warning(
            _('Error when computing the IR, any line found for the base [%d]') % base)

    @api.one
    @api.depends("amount_from", "amount_to")
    def _compute_name(self):
        self.name = _('From') + ' ' + str(self.amount_from) + \
            ' ' + _('To') + ' ' + str(self.amount_to)

    name = fields.Char(
        string=u'Nom', size=64, compute='_compute_name', store=True)
    amount_from = fields.Float(
        string=u'De', digits=dp.get_precision('IR'),  required=True)
    amount_to = fields.Float(
        string=u'À', digits=dp.get_precision('IR'), required=True)
    rate = fields.Float(
        string=u'Taux', digits=dp.get_precision('IR'), required=True)
    deduction = fields.Float(
        string=u'Déduction', digits=dp.get_precision('IR'), required=True)


class hr_scale_solidarity(models.Model):
    _name = 'hr.scale.solidarity'
    _order = 'amount_from'

    @api.model
    def get_solidarity(self, base, nbr):
        base *= 12 / nbr
        base = int(base)
        for solidarity in self.search([]):
            if solidarity.amount_from <= base and base <= solidarity.amount_to:
                return (base * (solidarity.rate / 100.) / 12) * nbr
        _logger.error(
            'Error when computing the contribution of solidarity, any line found for the base [%d]' % base)
        raise Warning(
            _('Error when computing the contribution of solidarity, any line found for the base [%d]') % base)

    @api.one
    @api.depends("amount_from", "amount_to")
    def _compute_name(self):
        self.name = _('From') + ' ' + str(self.amount_from) + \
            ' ' + _('To') + ' ' + str(self.amount_to)

    name = fields.Char(
        string=u'Nom', size=64, compute='_compute_name', store=True)
    amount_from = fields.Float(
        string=u'De', digits=dp.get_precision('Solidarity'),  required=True)
    amount_to = fields.Float(
        string=u'À', digits=dp.get_precision('Solidarity'), required=True)
    rate = fields.Float(
        string=u'Taux', digits=dp.get_precision('Solidarity'), required=True)


class hr_scale_licenciement(models.Model):
    _name = 'hr.scale.licenciement'
    _order = 'age_from'

    @api.model
    def get_licenciement_rate(self, age, rate):
        for lc in self.search([]):
            if lc.age_from <= age and age <= lc.age_to:
                return lc.nbr_hour * rate
        raise Warning(
            _('Error when computing the lc, any line found for the base [%d]') % age)

    @api.one
    @api.depends("age_from", "age_to")
    def _compute_name(self):
        self.name = _('From') + ' ' + str(self.age_from) + \
            ' ' + _('To') + ' ' + str(self.age_to)

    name = fields.Char(
        string=u'Nom', size=64, compute='_compute_name', store=True)
    age_from = fields.Float(
        string=u'De', digits=dp.get_precision('Licenciement'), required=True)
    age_to = fields.Float(
        string=u'À', digits=dp.get_precision('Licenciement'), required=True)
    nbr_hour = fields.Float(
        string=u'Nombre d\'heures', digits=dp.get_precision('Licenciement'), required=True)
    deduction = fields.Float(
        string=u'Déduction', digits=dp.get_precision('Licenciement'), required=True)

class hr_scale_km(models.Model):
    _name = 'hr.scale.km'
    _order = 'cv_from'

    @api.model
    def get_km_rate(self, val):
        for km in self.search([]):
            if km.cv_from <= val and val <= km.cv_to:
                return km.value
        raise Warning(
            _('Erreur lors d ela recherche pour le taux de CV, aucune ligne trouvé pour la base [%d]') % val)

    @api.one
    @api.depends("cv_from", "cv_to")
    def _compute_name(self):
        self.name = _('From') + ' ' + str(self.cv_from) + \
            ' ' + _('To') + ' ' + str(self.cv_to)

    name = fields.Char(string=u'Nom', size=64, compute='_compute_name', store=True)
    cv_from = fields.Integer(string=u'De', required=True)
    cv_to = fields.Integer(string=u'À', required=True)
    value = fields.Float(string=u'Valeur', digits=dp.get_precision('Account'), required=True)
