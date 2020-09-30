# -*- coding: utf-8 -*-
from datetime import timedelta
import json

from odoo import fields, models, api, _
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
        url = self.env.company.url
        user =self.env.company.user
        password = self.env.company.password
        bd = self.env.company.bd
        models_kw, db, username, password, uid = self.connect_xml_rpc_v13(url, bd, user, password)
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

    def load_attendance(self):
        url = self.env.company.url
        user = self.env.company.user
        password = self.env.company.password
        bd = self.env.company.bd
        models_kw, db, username, password, uid = self.connect_xml_rpc_v13(url, bd, user, password)
        records = models_kw.execute_kw(db, uid, password, 'kzm.hr.pointeuse', 'get_attendancies_server',
                                       [[l.id_pointeuse for l in self],])
        records = json.loads(records)
        print("records ------",type(records),records)
        error = False
        msg = _("These machines seem to be offline. Please verify if they are connected and try again :\n")
        for r in self:
            #print("before calling LEAD funct")
            r_return = records[str(r.id_pointeuse)]
            print(r_return, "----")
            attendances_list, test = r_return['attendances_list'], r_return['test']
            print("attendances_list -----",attendances_list)
            #print("ret LEAD", attendances_list, test)
            if test:
                if len(attendances_list) == 0:
                    raise ValidationError("Pas de présences !")
                for att in attendances_list:
                    # badge_id = self.env['kzm.hr.pointeuse.badge'].search([('matricule', '=', str(att.uid).rjust(5, "0"))])
                    matricule = str(att[0]).zfill(5)
                    presence_date = att[1]
                    employee_id = self.sudo().env['hr.employee'].search([
                        ('matricule', '=', matricule),
                        ])
                    if len(employee_id) > 1:
                        raise ValidationError("La matricule %s est attribuée à plusieurs employées"%matricule)
                    if not employee_id or len(employee_id) == 0:
                        employee_id = False
                    #action = att.status or 10
                    # If the attendance already imported
                    attendance_count = self.sudo().env['zk_attendance.attendance'].search(
                            [('date', '=', presence_date),
                             ('matricule_pointeuse', '=', matricule),
                             ])
                    if len(attendance_count) > 0:
                            continue

                    machine_id = r.id
                    # self.env['zk_attendance.attendance'].create(
                    attendance_id = {
                        'employee_id': employee_id and employee_id.id or False,
                        'date': presence_date,
                        'action': 'sign_in',
                        'company_id': r.company_id.id,
                        'matricule_pointeuse':  matricule,
                        # 'status': action,
                        'machine_id': machine_id,
                    }
                    print("presence date -----",presence_date)
                    result = r.test_altern_si_so(attendance_id, presence_date)
                    try:
                        attendance_id['note'] = "{}".format(result[0])
                        if result[0] == 4:
                            self.env['zk_attendance.attendance'].create(attendance_id)
                        elif result[0] == 0:
                            attendance_id['action'] = 'sign_out'
                            self.env['zk_attendance.attendance'].create(attendance_id)
                        elif result[0] == 1:
                            new_attendance_id = {
                                'employee_id': employee_id and employee_id.id or False,
                                'machine_id': result[1].machine_id.id,
                                'company_id': r.company_id.id,
                                'matricule_pointeuse':  matricule,
                                # 'sous_ferme_id': self.sous_ferme_id and self.sous_ferme_id.id or False,
                                # 'name': result[1] + timedelta(minutes=1),
                                'date': fields.Datetime.from_string(result[1].date) + timedelta(minutes=1),
                                'action': 'sign_out',
                                'note': u'Présence ajoutée automatiquement.',
                            }
                            self.env['zk_attendance.attendance'].create(new_attendance_id)
                            self.env['zk_attendance.attendance'].create(attendance_id)
                        elif result[0] == 5:
                            result[1].write({'date': result[2]})
                            attendance_id['action'] = 'sign_out'
                        elif result[0] == 3:
                            continue
                        else:
                            continue
                    except:
                        continue
                self.env.cr.commit()
                #r.clear_attendancies()
            else:
                msg += r.name + '\n'
                error = True
        if error:
            raise ValidationError(msg)



