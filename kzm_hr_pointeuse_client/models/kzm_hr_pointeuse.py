# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
import json

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, _logger
import xmlrpc.client
from xmlrpc import client as xmlrpclib

def convert_TZ_UTC(self, TZ_datetime):
    fmt = "%Y-%m-%d %H:%M:%S"
    # Current time in UTC
    now_utc = datetime.now(timezone('UTC'))
    # Convert to current user time zone
    now_timezone = now_utc.astimezone(timezone(self.env.user.tz))
    UTC_OFFSET_TIMEDELTA = datetime.strptime(now_utc.strftime(fmt), fmt) - datetime.strptime(now_timezone.strftime(fmt), fmt)
    local_datetime = datetime.strptime(TZ_datetime, fmt)
    result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
    return result_utc_datetime.strftime(fmt)


class HrPointeuse(models.Model):
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
        try:
            records = models_kw.execute_kw(db, uid, password, 'kzm.hr.pointeuse', 'get_status_connection',
                                    [[l.id_pointeuse for l in self],])
        except Exception as e:
            raise ValidationError("Error :"+str(e))

        records = json.loads(records)
        for r in self:
            r.connection_state = records.get(str(r.id_pointeuse), False)



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
        error = False
        msg = _("These machines seem to be offline. Please verify if they are connected and try again :\n")
        for r in self:
            #print("before calling LEAD funct")
            r_return = records[str(r.id_pointeuse)]
            attendances_list, test = r_return['attendances_list'], r_return['test']
            #print("ret LEAD", attendances_list, test)
            if test:
                if len(attendances_list) == 0:
                    raise ValidationError("Pas de présences !")
                for att in attendances_list:
                    # badge_id = self.env['kzm.hr.pointeuse.badge'].search([('matricule', '=', str(att.uid).rjust(5, "0"))])
                    matricule = str(att[0]).zfill(5)
                    presence_date = att[1]
                    presence_date = convert_TZ_UTC(self, str(presence_date))
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
                    presence_date = datetime.strptime(presence_date, '%Y-%m-%d %H:%M:%S')
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

    def nettoyer_pointeuse(self, with_message=True):
        url = self.env.company.url
        user = self.env.company.user
        password = self.env.company.password
        bd = self.env.company.bd
        models_kw, db, username, password, uid = self.connect_xml_rpc_v13(url, bd, user, password)
        records = models_kw.execute_kw(db, uid, password, 'kzm.hr.pointeuse', 'nettoyer_pointeuse',
                                       [[l.id_pointeuse for l in self],])
        print("records",records)
        msg = str(records)
        raise ValidationError(msg)


    def clear_attendance(self):
        url = self.env.company.url
        user = self.env.company.user
        password = self.env.company.password
        bd = self.env.company.bd
        models_kw, db, username, password, uid = self.connect_xml_rpc_v13(url, bd, user, password)
        records = models_kw.execute_kw(db, uid, password, 'kzm.hr.pointeuse', 'nettoyer_pointeuse',
                                       [[l.id_pointeuse for l in self],])
        print("records",records)
        msg = str(records)
        raise ValidationError(msg)

    def delete_badge(self, badge_ids):
        for pointeuse in self:
            pointeuse.get_status()
            connect = pointeuse.connection_state
            if connect:
                # zk.EnableDevice(iMachineNumber, False)
                for badge_id in badge_ids:
                    sUserID = str(int(badge_id.employee_id.matricule))
                    msg, result = badge_id.delete_user(pointeuse.id, sUserID)
                    if not result:
                        _logger.warning(_(
                            u"Delete_badge:Operation de suppression de l'utilisateur %s a échouée, Pointeuse : %s" % (
                                badge_id.employee_id.matricule, pointeuse.name)))
                        raise Exception(_(u"Operation de suppression de l'utilisateur %s a échouée, Pointeuse : %s" % (
                            badge_id.employee_id.matricule, pointeuse.name)))
                    else:
                        _logger.warning(_(
                            u"Delete_badge:Operation de suppression de l'utilisateur %s, Pointeuse : %s " % (
                                badge_id.employee_id.matricule, pointeuse.name)))
                # zk.EnableDevice(iMachineNumber, True)
            else:
                _logger.warning(_(
                    u"delete_badge:Operation de suppression des utilisateurs a échouée,Echec de connexion, Pointeuse : %s" % (
                        pointeuse.name)))
                raise Exception(
                    _(u"Operation de suppression des utilisateurs a échouée,Echec de connexion à la pointeuse : %s" % (
                        pointeuse.name)))

class HrPointeuseBadge(models.Model):
    _inherit = 'kzm.hr.pointeuse.badge'

    def add_user(self, machineid, uid, name, privilege, password_p, groupid, userid, card):
        print("llllllllllllllp")
        machine_id = self.env['kzm.hr.pointeuse'].browse(machineid)
        url = self.env.company.url
        user = self.env.company.user
        password = self.env.company.password
        bd = self.env.company.bd
        models_kw, db, username, password, uid = self.connect_xml_rpc_v13(url, bd, user, password)
        records = []
        try:
            # time.sleep(1)
            records = models_kw.execute_kw(db, uid, password, 'kzm.hr.pointeuse', 'set_user_server',
                                           [[machine_id.id_pointeuse], uid, name, privilege, password_p, groupid, userid,
                                            card])
            records = json.loads(records)
            res = records.get(str(machine_id.id_pointeuse), False)
            if res and res['return']:
                return (_("User ") + name + _(" est ajouté au ") + machine_id.name + '\n'), True
            else:
                return  res['msg'], res['return']
        except Exception as e:
            return _(" Erreur d'insertion badge XmlRpc"), False


    def connect_xml_rpc_v13(self,url, db, username, password):
        common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
        models_kw = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))
        uid = common.login(db, username, password)


        return models_kw, db, username, password, uid

    def delete_user(self, machineid, uid):
        machine_id = self.env['kzm.hr.pointeuse'].browse(machineid)
        url = self.env.company.url
        user = self.env.company.user
        password = self.env.company.password
        bd = self.env.company.bd
        models_kw, db, username, password, uid = self.connect_xml_rpc_v13(url, bd, user, password)
        records = []
        try:
            records = models_kw.execute_kw(db, uid, password, 'kzm.hr.pointeuse', 'set_delete_user',
                                           [[machine_id.id_pointeuse], uid])
            records = json.loads(records)
            res = records.get(str(machine_id.id_pointeuse), False)
            if res and res['return']:
                return (_("User does not exist or deleted from") + machine_id.name + '\n'), False
            else:
                return res['msg'], res['return']
        except Exception as e:
            return (_("Connection to ") + machine_id.name + _(" has been lost, couldn't delete user") + '\n'), False

    def unlink(self):
        badges_administration_ids = self#.filtered(lambda l: l.employee_id.type_employe == 'mensuel')
        for rec in badges_administration_ids:
            for p in rec.sudo().pointeuse_ids:
                try:
                    p.delete_badge(rec)
                except Exception as ex:
                    rec.message_post(
                        body=_(u"Echec de suppression de %s de la pointeuse %s.\n%s" % (
                        rec.employee_id.name, p.name, ex)))
                    #

        res = super(HrPointeuseBadge, self).unlink()
        return res