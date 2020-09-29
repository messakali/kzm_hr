# -*- coding: utf-8 -*-

from odoo import models, fields
import datetime
from odoo.tools.translate import _
from odoo import api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)



class kzm_hr_pointeuse_copie(models.Model):
    _name = 'kzm.hr.pointeuse.copie'
    # _rec_name = 'date'
    _description = 'Copie pointeuse'
    pointeuse_ids = fields.Many2many(comodel_name="kzm.hr.pointeuse", relation="r_kzm_hr_pointeuse_copie",
                                     column1="copie_id", column2="pointeuse_id", string=_("Pointeuses"),
                                     )
    pointeuse_id = fields.Many2one(comodel_name="kzm.hr.pointeuse", string=_("Pointeuse à copier"), required=True, )
    resultat = fields.Text(string=_("Résultat"), required=False, )
    taux = fields.Float(string=_("Taux"), required=False, )
    etat_traitement = fields.Float(string="Etat de traitement", compute='compute_etat_traitement')
    company_id = fields.Many2one(comodel_name="res.company", ondelete='cascade', string=_("Society"),
                                 required=True,
                                 default=lambda self: self.env.company)


    
    @api.depends('taux')
    def compute_etat_traitement(self):
        self.etat_traitement=100.0 * self.taux

    
    def copie_pointeuse(self):
        _logger.warning(u"Début copie_pointeuse")
        try:
            self.resultat=u"Début"
            for pointeuse in self.pointeuse_ids:
                req="select id_badge from kzm_r_hr_pointeuse_badge " \
                    "where id_pointeuse= %d and " \
                    "id_badge not in (select id_badge from kzm_r_hr_pointeuse_badge " \
                    "where id_pointeuse= %d )" % (self.pointeuse_id.id,pointeuse.id)
                self.env.cr.execute(req)
                ids=self.env.cr.dictfetchall()
                res=[]
                for x in ids:
                    res.append(x['id_badge'])
                badge_ids = self.env['kzm.hr.pointeuse.badge'].sudo().search([
                    ('active', '=', True),
                    ('id','in',res)
                ])
                message=u"Début d'insertion de %d badges dans la pointeuse:%s" % (len(badge_ids),pointeuse.name)
                self.resultat +="\n"+message
                _logger.warning(message)
                try:
                    pointeuse.sudo().write_badge(badge_ids)
                    for badge_id in badge_ids:
                        badge_id.sudo().pointeuse_ids += pointeuse
                    message=u"Fin d'insertion de %d badges dans la pointeuse:%s" % (len(badge_ids),pointeuse.name)
                    self.resultat += "\n"+message
                    _logger.warning(message)

                except Exception as exx:
                    self.resultat += "\n"+exx.message
                    _logger.warning(exx.message)
                self.env.cr.commit()
            self.resultat+=u"\nFin"
            raise ValidationError(self.resultat)
        # TODO douae à voir (l'érreur sur copie de poiteuse')
        except Exception as ex:
            print("===============",ex)
            print("==================2",message)
            print("=====================3",ex.value)

            _logger.warning(ex)
            _logger.warning(u"Fin copie_pointeuse")
            raise ValidationError(ex + ex.value and ex.value or "")
        _logger.warning(u"Fin copie_pointeuse")
