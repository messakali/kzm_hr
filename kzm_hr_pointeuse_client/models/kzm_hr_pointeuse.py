# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError
import xmlrpc.client
from xmlrpc import client as xmlrpclib

class HrEmployee(models.Model):
    _inherit = 'kzm.hr.pointeuse'

    id_pointeuse = fields.Integer("ID", default=4)

    @api.depends('ip', 'port')
    def get_status(self):
        # conf = self.env['res.config.settings'].set_config_pointeuse()
        # print(conf)
        models_kw, db, username, password, uid = self.connect_xml_rpc_v13('http://51.210.186.95', 'POINTAGE', 'ICESCO', 'Isec@1715@?')
        print("----", self.id_pointeuse,[[self.id_pointeuse,]])
        records = models_kw.execute_kw(db, uid, password, 'kzm.hr.pointeuse', 'get_status_connection',
                                    [[int(self.id_pointeuse),]])
        print("-*-*-*",records)


        msg = "; ".join([str(c) for c in records])
        raise ValidationError(msg)


    def connect_xml_rpc_v13(self,url, db, username, password):
        common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
        models_kw = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))
        uid = common.login(db, username, password)


        return models_kw, db, username, password, uid




#
# def sych_matricule_8_vers_13():
#         models, db, username, password, uid = connect_xml_rpc_v13(url='http://dbnord.karizma-conseil.com',
#                                                                   db=settings.TO_DB,
#                                                                   username='kadmin',
#                                                                   password='Dbnord?@1715@'
#                                                                   )
#
#         rec = models.execute_kw(db, uid, password, 'hr.employee', 'write',
#                                      [[id_v13], {'matricule': matricule, }]):