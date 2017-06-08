# encoding: utf-8

from openerp import models, fields, api, _
from openerp.addons.decimal_precision import decimal_precision as dp
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
# import calendar
# from openerp.exceptions import Warning
# from openerp.exceptions import Warning as UserError


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    @api.one
    @api.onchange("children_ids", "marital", "wife_situation", "nbr_person_charged")
    def change_charged_person(self):
        nbr_person_charged = 0
        nbr_children_charged = 0
        nbr_children_af = 0
        children = 0
        if self.children_ids and self.marital != 'C':
            children = len(self.children_ids)
            for line in self.children_ids:
                if line.a_charge:
                    nbr_person_charged += 1
                    nbr_children_charged += 1
                if line.af:
                    nbr_children_af += 1
            if self.gender == 'male' and self.marital == 'M':
                if self.wife_situation != 'A':
                    nbr_person_charged += 1
            self.children = len(self.children_ids)
            self.nbr_person_charged = nbr_person_charged
            self.nbr_children_charged = nbr_children_charged
            self.nbr_children_af = nbr_children_af

        elif not self.children_ids and self.gender == 'male' and self.marital == 'M' and self.wife_situation != 'A':
            self.nbr_children_charged = self.nbr_person_charged - 1
            self.nbr_children_af = self.nbr_person_charged - 1

    nbr_person_charged = fields.Integer(
        string=u'Nombre de personne à charge', required=True, default=0, readonly=False, store=True,compute=False)
    nbr_children_charged = fields.Integer(
        string=u'Nombre d\'enfants à charge', required=True, default=0, readonly=False, compute=False)
    nbr_children_af = fields.Integer(
        string=u'Nombre d\'enfants pour allocation familiale', required=True, default=0, readonly=False, compute=False)
    children = fields.Integer(u"Nbre d'enfants")


    @api.model
    def create(self, vals):
        if not vals.get('otherid', False):
            company = self.env['res.company'].browse(
                vals.get('company_id', False))
            if not company:
                company = self.env.user.company_id
            # if company and company.initial:
            #     employee = self.env['hr.employee'].with_context({'active_test': False, }).search(
            #         [('otherid', 'like', company.initial)], limit=1, order='otherid desc')
            #     seq = company.initial + '1'.rjust(5, '0')
            #     if employee:
            #         seq = company.initial + \
            #             str(int(''.join(
            #                 [x for x in (employee.otherid or '0') if x.isdigit()]) or '0') + 1).rjust(5, '0')
            # else:
            #     raise Warning('Veuillez configurer l\'initial de la société')

            if company:
                employee = self.env['hr.employee'].search(
                    [('otherid', '!=', False)], limit=1, order='otherid desc')
                seq = '1'.rjust(4, '0')
                if employee:
                    seq = str(int(''.join(
                            [x for x in (employee.otherid or '0') if x.isdigit()]) or '0') + 1).rjust(4, '0')
            vals.update({
                'otherid': seq,
            })
        if vals.get('name', False):
            name = vals.get('name').split(' ', 1)
            vals.update({
                'prenom': name and name[0] or '',
                'nom': len(name) > 1 and name[1] or '',
            })
        if vals.get('nom', False) or vals.get('prenom', False):
            nom, prenom = vals.get('nom'), vals.get('prenom')
            vals.update({
                'name': (prenom or '') + (nom and ' ' or '') + (nom or '')
            })
        vals = self._update_vals(vals)
        employee_id = super(hr_employee, self).create(vals)
        return employee_id
