# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class kzm_poste_pointage_journalier(models.Model):
    _name = "kzm.poste.pointage.journalier"
    _description = "Poste de pointage journalier "
    _auto = False
    _order = 'id desc'

    kzm_all_attendances_id = fields.Many2one(comodel_name="kzm.all.attendances",
                                            string=_("Pointage Journalier"),
                                            readonly=True, )

    type_contract_id = fields.Many2one(comodel_name="hr.contract.type", string=_("Poste HR"), readonly=True, )
    # salaire_journalier = fields.Float(related='type_contract_id.salaire_journalier')
    # hour_salary = fields.Float(related='type_contract_id.hour_salary')

    nombre_rh = fields.Float(string=_("Nombre de ressources"), readonly=True, )
    total = fields.Float(string=_("Montant Total"), readonly=True, )

    heure_normal = fields.Float(string=_("Heure Normal"), readonly=True, )
    heure_sup = fields.Float(string=_("Heure Sup"), readonly=True, )

    total_heure_normal = fields.Float(string=_("Total Heures Normales"))
    total_heure_sup = fields.Float(string=_("Total Heures Sup"))

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS %s;
            CREATE or REPLACE VIEW %s as (
            SELECT Row_number() OVER (ORDER BY type_contract_id) as id,
                kzm_all_attendances_id, type_contract_id, count(1) as nombre_rh,
                max(heure_normal) as heure_normal,max(heure_sup) as heure_sup,
                sum(heure_normal) as total_heure_normal,sum(heure_sup) as total_heure_sup,
                sum(montant_total)  as total
            FROM kzm_daily_attendance
            GROUP BY kzm_all_attendances_id, type_contract_id)""" % (self._table,self._table))
