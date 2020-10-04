# -*- coding: utf-8 -*-

from odoo import models, fields, api, modules, exceptions, _
from odoo.exceptions import ValidationError
from ..tools.pyzk import zk as pyzk
from datetime import datetime, timedelta
import time
import socket
import json
from pprint import pprint
import base64

import logging

_logger = logging.getLogger(__name__)


class machine(models.Model):
    _inherit = ['mail.thread']
    _name = 'kzm.hr.pointeuse'
    _rec_name = 'name'
    _description = 'Gestion des pointeuse'


    @api.depends('company_id', 'ip', 'port')
    def compute_name(self):
        for rec in self:
            rec.name = ""
            if rec.company_id:
                rec.name = rec.company_id.name
            if rec.is_valid_ipv4_address(rec.ip):
                rec.name += "_" + rec.ip + "_" + str(rec.port)
            else:
                rec.name += "_" + str(rec.port)

    type = fields.Selection(string=_("Type"),
                            selection=[('ouvrier', 'Worker'), ('administration', 'Administration'), ],
                            default='ouvrier', required=False, )
    company_id = fields.Many2one(comodel_name="res.company", string=_("Société"),
                                 required=True, ondelete='cascade',
                                 default=lambda self: self.env.company)


    name = fields.Char(string=_("Nom"), compute="compute_name", store=True)
    ip = fields.Char(string=_("IP Address"), required=True, default="")
    image = fields.Binary(string=_("Image"), help="", )
    port = fields.Char(string=_("Port"), required=True, default=4370, )
    connection_state = fields.Boolean(string=_("Etat"), readonly=False, default=False)
    status_img = fields.Binary(string=_("Status"), readonly=True, compute='_compute_status_img', )

    active = fields.Boolean(string=_("Active"), default=True)

    badge_ids = fields.Many2many(comodel_name="kzm.hr.pointeuse.badge", relation="kzm_r_hr_pointeuse_badge",
                                 column1="id_pointeuse", column2="id_badge", string=_("Badges"), )

    _sql_constraints = [
        ('ip_unique', 'UNIQUE (ip)', u"L'adresse ip de la pointeuse existe déjà")
    ]

    @api.model
    def create(self, values):
        # machines = values.get('machine_ids', False)
        # print("------ Maciines",machines)
        # if machines:
        # 	for l in machines:
        # 		rec_machine = self.env['kzm.hr.pointeuse'].browse(machines[0][2])
        # 		print("Records :::::", rec_machine)
        record = super(machine, self).create(values)

        record.get_status()
        return record

    @api.depends('ip', 'port')
    def get_status(self):
        for r in self:
            # self.load_attendance()
            try:
                zk = pyzk.ZK(r.ip, int(r.port), timeout=10)
                conn = zk.connect()
                r.connection_state = True
                if conn:
                    conn.disconnect()
            except Exception as e:
                r.connection_state = False

    def get_status_connection(self):
        id_res = {}
        for r in self:
            # self.load_attendance()
            print("---- start", self)
            try:
                zk = pyzk.ZK(r.ip, int(r.port), timeout=10)
                conn = zk.connect()
                r.connection_state = True
                if conn:
                    conn.disconnect()
            except Exception as e:
                r.connection_state = False
            print("---- end", self)
            id_res[r.id] = {
                    'state': r.connection_state,
                }
            id_res = json.dumps(id_res)
        print("id_res ----", id_res)
        return id_res

    @api.depends('connection_state')
    def _compute_status_img(self):
        for rec in self:
            if rec.connection_state == True:
                with open(modules.get_module_resource('kzm_zk_attendance', 'static/img', 'yes.png'), 'rb') as f:
                    rec.status_img = base64.b64encode(f.read())
            else:
                with open(modules.get_module_resource('kzm_zk_attendance', 'static/img', 'no.png'), 'rb') as f:
                    rec.status_img = base64.b64encode(f.read())
                    # r.name = str(r.ip or '') + "_" + str(r.port or '')

    def get_all_status(self):
        machines = self.search([])
        machines.get_status()

    # def cmp_attendencies(x, y):
    #     return x.uid < y.uid

    def get_attendancies(self):
        self.get_status()
        attendance_list = []

        if self.connection_state:
            try:
                zk = pyzk.ZK(self.ip, int(self.port), password=0, timeout=10)
                conn = zk.connect()
                time.sleep(1)
                attendance_list = conn.get_attendance()
                return attendance_list, True
            except:
                return attendance_list, False
        print("attttttt",attendance_list)
        return attendance_list, False

    def get_attendancies_server(self):
        attendance_res = {}
        for r in self:
            attendances_list, test = r.get_attendancies()
            attendance_res[r.id]= {
                'test': test,
                'attendances_list': [(str(att.user_id), str(att.timestamp)) for att in attendances_list],
            }
        attendance_res = json.dumps(attendance_res)
        print("attendance_res ----",attendance_res)
        return attendance_res

    def set_user_server(self,uid, name, privilege, password, groupid, userid, card):
        res = {}
        for machine_id in self:
            zk, conn = False, False
            try:
                zk = pyzk.ZK(machine_id.ip, int(machine_id.port), timeout=10)
                conn = zk.connect()
                machine_id.connection_state = True
            except:
                machine_id.connection_state = False
            if not machine_id.connection_state or not conn:
                res[machine_id.id] = {'return': False, 'msg': 'Machine non connecte'}
            else:
                try:
                    conn.set_user(int(uid), name, privilege, password, groupid, str(int(userid)).zfill(5), int(card))
                    res[machine_id.id] = {'return': True, 'msg': 'User has been successfully setted'}
                except Exception as e:
                    res[machine_id.id] = {'return': False, 'msg': str(e)}
        return  json.dumps(res)

    def set_delete_user(self,uid):
        res = {}
        for machine_id in self:
            zk, conn = False, False
            try:
                zk = pyzk.ZK(machine_id.ip, int(machine_id.port), timeout=10)
                conn = zk.connect()
                machine_id.connection_state = True
            except:
                machine_id.connection_state = False

            if not machine_id.connection_state or not conn:
                print("machine_id.connection_state ----",machine_id.connection_state)
                print("conn ----",conn)

                res[machine_id.id] = {'return': False, 'msg': 'Machine non connecte'}
            else:
                try:
                    conn.delete_user(uid=int(uid))
                    res[machine_id.id] = {'return': True, 'msg': 'User has been successfully deleted'}
                except Exception as e:
                    res[machine_id.id] = {'return': False, 'msg': str(e)}
        return json.dumps(res)


    # def load_attendance(self):
    #     error = False
    #     msg = _("These machines seem to be offline. Please verify if they are connected and try again :\n")
    #     for r in self:
    #         attendances_list, test = r.get_attendancies()
    #         if test:
    #             for att in attendances_list:
    #                 # badge_id = self.env['kzm.hr.pointeuse.badge'].search([('matricule', '=', str(att.uid).rjust(5, "0"))])
    #                 matricule = str(att.user_id).rjust(5, "0")
    #                 presence_date = att.timestamp
    #                 employee_id = self.env['hr.employee'].search([('matricule', '=', matricule)])
    #                 if not employee_id:
    #                     continue
    #                 action = att.status or 10
    #                 # If the attendance already imported
    #                 attendance_count = self.env['zk_attendance.attendance'].search_count(
    #                     [('date', '=', str(presence_date)),
    #                      ('employee_id', '=', employee_id.id),
    #                      ])
    #                 if attendance_count:
    #                     continue
    #
    #                 machine_id = r.id
    #                 # self.env['zk_attendance.attendance'].create(
    #                 attendance_id = {
    #                     'employee_id': employee_id.id,
    #                     'date': str(presence_date),
    #                     'action': 'sign_in',
    #                     'company_id': r.company_id.id,
    #                     # 'status': action,
    #                     'machine_id': machine_id,
    #                 }
    #                 result = r.test_altern_si_so(attendance_id, presence_date)
    #                 try:
    #                     attendance_id['note'] = "{}".format(result[0])
    #                     if result[0] == 4:
    #                         self.env['zk_attendance.attendance'].create(attendance_id)
    #                     elif result[0] == 0:
    #                         attendance_id['action'] = 'sign_out'
    #                         self.env['zk_attendance.attendance'].create(attendance_id)
    #                     elif result[0] == 1:
    #                         new_attendance_id = {
    #                             'employee_id': employee_id.id,
    #                             'machine_id': result[1].machine_id.id,
    #                             'company_id': r.company_id.id,
    #                             # 'sous_ferme_id': self.sous_ferme_id and self.sous_ferme_id.id or False,
    #                             # 'name': result[1] + timedelta(minutes=1),
    #                             'date': fields.Datetime.from_string(result[1].date) + timedelta(minutes=1),
    #                             'action': 'sign_out',
    #                             'note': u'Présence ajoutée automatiquement.',
    #                         }
    #                         self.env['zk_attendance.attendance'].create(new_attendance_id)
    #                         self.env['zk_attendance.attendance'].create(attendance_id)
    #                     elif result[0] == 5:
    #                         result[1].write({'date': result[2]})
    #                         attendance_id['action'] = 'sign_out'
    #                     elif result[0] == 3:
    #                         continue
    #                     else:
    #                         continue
    #                 except:
    #                     continue
    #             self.env.cr.commit()
    #             #TODO, don't delete attendancies after load
    #             #r.clear_attendancies()
    #         else:
    #             msg += r.name + '\n'
    #             error = True
    #     if error:
    #         raise ValidationError(msg)
    def load_attendance(self):
        error = False
        msg = _("These machines seem to be offline. Please verify if they are connected and try again :\n")
        for r in self:
            #print("before calling LEAD funct")
            attendances_list, test = r.get_attendancies()
            #print("ret LEAD", attendances_list, test)
            if test:
                if len(attendances_list) == 0:
                    raise ValidationError("Pas de présences !")
                for att in attendances_list:
                    # badge_id = self.env['kzm.hr.pointeuse.badge'].search([('matricule', '=', str(att.uid).rjust(5, "0"))])
                    matricule = str(att.user_id).zfill(5)
                    presence_date = att.timestamp
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
                            [('date', '=', str(presence_date)),
                             ('matricule_pointeuse', '=', matricule),
                             ])
                    if len(attendance_count) > 0:
                            continue

                    machine_id = r.id
                    # self.env['zk_attendance.attendance'].create(
                    attendance_id = {
                        'employee_id': employee_id and employee_id.id or False,
                        'date': str(presence_date),
                        'action': 'sign_in',
                        'company_id': r.company_id.id,
                        'matricule_pointeuse':  matricule,
                        # 'status': action,
                        'machine_id': machine_id,
                    }
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

    def clear_attendancies_from_one(self):
        """ KZM METHOD"""
        zk, conn = False, False
        try:
            zk = pyzk.ZK(self.ip, int(self.port), timeout=10)
            conn = zk.connect()
            self.connection_state = True
        except:
            self.connection_state = False

        if self.connection_state and conn:
            try:
                time.sleep(0.5)
                if conn:
                    conn.clear_attendance()
                    conn.disconnect()
                    return True
            except:
                return False
        return False


    def clear_attendancies(self):
        """ KZM METHOD """
        error = False
        msg = _("These machines seem to be offline. Please verify if they are connected :\n")
        for r in self:
            if not r.clear_attendancies_from_one():
                msg += r.name + '\n'
                error = True
        if error:
            raise ValidationError(msg)

    
    def clear_attendance(self):
        # self.get_status()
        if self.connection_state:
            test = True
            _logger.warning(u"Début de nétoyage de la pointeuse %s " % self.name)
            if self.clear_attendancies_from_one():
                message = _(u"Toutes les présences de la pointeuse %s sont suprimées avec succés" % self.name)
                _logger.warning(message)
            else:
                message = _(u"Operation de netoyage pointeuse %s échouée" % self.name)
                _logger.warning(message)
        else:
            test = False
            message = _(u"La pointeuse %s est  hors service" % self.name)
            _logger.warning(message)
        _logger.warning(u"Fin de nétoyage de la pointeuse %s " % self.name)
        return message,test

    
    def clear_attendance_with_msg(self):
        message = self.clear_attendance()
        if len(message) > 1:
            raise ValidationError(message)

    
    def load_attendance_from_cron(self):
        self.sudo().load_attendance()

    def write_badge(self, badge_ids):
        if not badge_ids:
            return
        for pointeuse in self:
            # pointeuse.get_status()
            # time.sleep(1)
            if pointeuse.connection_state:
                # zk.EnableDevice(iMachineNumber, False)
                for badge_id in badge_ids:
                    badge_id.add_user_to_machine(pointeuse.id)
            else:
                raise Exception(_(u'Erreur de connexion à la pointeuse %s' % (self.name)))

    
    def nettoyer_pointeuse(self, with_message=True):
        # charche les employés qui n'ont pas de badge et qu'on trouve dans la pointeuse
        # puis les supprimes du système
        type_employee = 'journalier'

        req = "select cast(matricule as int) from hr_employee " \
              "where id not in (select employee_id from kzm_hr_pointeuse_badge) "
        self._cr.execute(req)
        matricule_ids = self.env.cr.dictfetchall()
        ids = []
        for x in matricule_ids:
            ids.append(x['matricule'])
        user_a_supprimer = []
        odoo_user_a_supprimer = None
        if not ids:
            return
        if not self.is_valid_ipv4_address(self.ip):
            if with_message:
                raise ValidationError(u'Adresse IP de la pointeuse sélectionnée est invalide.')
            else:
                _logger.warning(u'Adresse IP de la pointeuse sélectionnée est invalide.')

        self.get_status()
        connect = self.connection_state
        if not connect:
            if with_message:
                raise ValidationError(_("La pointeuse %s est hors connexion" % str(self.name)))
            else:
                _logger.warning(_("La pointeuse %s est hors connexion" % str(self.name)))

        if connect:
            zk = pyzk.ZK(self.ip, int(self.port), timeout=10)
            conn = zk.connect()
            time.sleep(0.5)
            try:
                _logger.warning(u"Début de néttoyage de la pointeuse %s " % self.name)
                test = True
                try:
                    users = None
                    if conn:
                        users = conn.get_users()
                    if not users:
                        _logger.warning(u"Pas d'utilisateurs au niveau de la pointeuse %s " % self.name)
                        raise Exception(_("Pas d'utilisateurs {}!".format(self.name)))

                    for user in users:
                        user_a_supprimer.append(str(user.uid).rjust(5, "0"))
                        odoouser = self.env['kzm.hr.pointeuse.badge'].search(
                            [('matricule', '=', str(user.uid).rjust(5, "0"))])
                        if odoo_user_a_supprimer and odoouser:
                            odoo_user_a_supprimer += odoouser
                        elif not odoo_user_a_supprimer and odoouser:
                            odoo_user_a_supprimer = odoouser

                            # if not odoouser:
                            #     zk.delete_user(user.uid)
                    test = True
                except:
                    test = False

                if test:
                    if user_a_supprimer:
                        if True:  # MJID Says:here it was a while 1: i dont understand why ?
                            # self.get_status()
                            isConnected = self.connection_state
                            if isConnected == True:
                                # zk = pyzk.ZK(self.ip, int(self.port), timeout=10)
                                # conn = zk.connect()
                                time.sleep(0.5)
                                deleted = []
                                not_delted = []
                                for user_att in user_a_supprimer:
                                    try:
                                        conn.delete_user(int(user_att))
                                        deleted.append(user_att)
                                    except:
                                        not_delted.append(user_att)
                                _logger.warning(
                                    u"Néttoyage de la pointeuse {} des matricules {} ".format(self.name,
                                                                                              deleted))
                                self.message_post(
                                    body=u"Néttoyage de la pointeuse {} des matricules {} ".format(self.name,
                                                                                                   deleted))
                                if not_delted:
                                    _logger.warning(
                                        u"Néttoyage de la pointeuse {} des matricules non supprimerés {} ".format(
                                            self.name,
                                            deleted))
                                    self.message_post(
                                        body=u"Néttoyage de la pointeuse {} des matricules non supprimés {} ".format(
                                            self.name,
                                            not_delted))
                            else:
                                if conn: conn.disconnect()
                                raise ValidationError(_(
                                    "A la suppression des utilisateurs, La pointeuse %s est hors connexion" % str(
                                        self.name)))


                    else:
                        self.message_post(body=u"Néttoyage de la pointeuse {} : aucun matricule".format(self.name))


            except Exception as ex:
                if conn: conn.disconnect()
                _logger.warning(u"Erreur de chargement des utilisateurs de la pointeuse %s :\n%s " % (self.name, ex))
                raise exceptions.Warning(ex)
        return test

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

    def sync_machine_odoo_one(self):
        time.sleep(1)
        zk, conn = False, False
        try:
            zk = pyzk.ZK(self.ip, int(self.port), timeout=10)
            conn = zk.connect()
            rec.connection_state = True
        except:
            rec.connection_state = False

        if self.connection_state and conn:
            try:

                time.sleep(0.5)
                users = []
                if conn:
                    users = conn.get_users()
                for user in users:
                    odoouser = self.env['kzm.hr.pointeuse.badge'].search([('matricule', '=',
                                                                           str(user.uid).rjust(5, "0"))])
                    if not odoouser:
                        conn.delete_user(int(user.uid))
                if conn:
                    conn.disconnect()
                return True
            except:
                if conn:
                    conn.disconnect()
                return False
        if conn:
            conn.disconnect()
        return False


    def sync_machine_odoo(self):
        error = False
        msg = _("These machines seem to be offline. Please verify if they are connected :\n")
        for r in self:
            if not r.sync_machine_odoo_one():
                msg += r.name + '\n'
                error = True
        if error:
            raise ValidationError(msg)

    #########################################################
    #               IP ADDRESS VALIDATION                   #
    #########################################################

    def is_valid_ipv4_address(self, ip):
        try:
            socket.inet_pton(socket.AF_INET, ip)
        except AttributeError:  # no inet_pton here, sorry
            try:
                socket.inet_aton(ip)
            except:
                return False
            return ip.count('.') == 3
        except:  # not a valid address
            return False

        return True

    
    @api.constrains('ip')
    def check_ip_address(self):
        if not self.is_valid_ipv4_address(self.ip):
            raise ValidationError(_('Adresse IP saisi est invalide.'))

    ########################################################
    #                   CONNECTION STATUS                  #
    ########################################################


    def check_connection(self):
        messages = ""
        l_index = 0
        self.env.cr.savepoint()
        for this in self:
            if not this.is_valid_ipv4_address(this.ip):
                l_index += 1
                messages += str(l_index) + ' - \t' + this.name + _(u' : Adresse IP invalide\n')
                this.connection_state = False
                continue
            this.get_status()
            if this.connection_state:
                l_index += 1
                messages += str(l_index) + ' - \t' + this.name + _(u' : Connexion réussie\n')
                this.message_post(body=this.name + _(u' : Connexion réussie\n'))
            else:
                l_index += 1
                messages += str(l_index) + ' - \t' + this.name + _(u' : Connexion échouée\n')
                this.message_post(body=this.name + _(u' : Connexion échouée\n'))
        # self.env.cr.commit()
        return messages

    ########################################################
    #                   Test Sing In/Off                   #
    ########################################################


    def test_altern_si_so(self, att, presence_date):
        self.ensure_one()
        """
           Alternance sign_in/sign_out check.
           Previous (if exists) must be of opposite action.
           Next (if exists) must be of opposite action.
        """
        # search and browse for first previous and first next records
        prev_att_ids = self.env['zk_attendance.attendance'].search(
            [('matricule_pointeuse', '=', att['matricule_pointeuse']), ('date', '<', att['date']),
             ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='date DESC')
        next_add_ids = self.env['zk_attendance.attendance'].search(
            [('matricule_pointeuse', '=', att['matricule_pointeuse']), ('date', '>', att['date']),
             ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='date ASC')
        # check for alternance, return False if at least one condition is not satisfied

        if prev_att_ids and prev_att_ids[0].action == att['action']:  # previous exists and is same action
            prev_date = fields.Datetime.from_string(prev_att_ids[0].date)
            if prev_date.date() == presence_date.date():
                return [0, ]
            return [1, prev_att_ids[0]]
            """if prev_date < prev_date.date().strftime('%Y-%m-%d 17:59:69'):
                return [1, prev_date]
            return [5, prev_att_ids[0], prev_date.date().strftime('%Y-%m-%d 00:00:01') + timedelta(days=1)]
            """
        if next_add_ids and next_add_ids[0].action == att['action']:  # next exists and is same action
            return [2, ]
        if (not prev_att_ids) and (not next_add_ids) and att['action'] != 'sign_in':  # first attendance must be sign_in
            return [3, ]
        return [4, ]


    def cron_syncroniser_pointeuses(self):
        _logger.warning(u"Début cron_syncroniser_pointeuses")
        pointeuse_ids = self.env['kzm.hr.pointeuse'].search([
            ('active', '=', True), ('type', '=', 'ouvrier')
        ])
        try:
            for pointeuse_a_copie in pointeuse_ids:
                _logger.warning(u"Début de copie de la pointeuse %s dans les autres" % pointeuse_a_copie.name)
                succes = True
                for pointeuse in pointeuse_ids - pointeuse_a_copie:
                    req = "select id_badge from kzm_r_hr_pointeuse_badge " \
                          "where id_pointeuse= %d and " \
                          "id_badge not in (select id_badge from kzm_r_hr_pointeuse_badge " \
                          "where id_pointeuse= %d )" % (pointeuse_a_copie.id, pointeuse.id)
                    self.env.cr.execute(req)
                    ids = self.env.cr.dictfetchall()
                    res = []
                    for x in ids:
                        res.append(x['id_badge'])
                    badge_ids = self.env['kzm.hr.pointeuse.badge'].sudo().search([
                        ('active', '=', True),
                        ('id', 'in', res)
                    ])
                    message = u"Début d'insertion de %d badges dans la pointeuse: %s" % (len(badge_ids), pointeuse.name)
                    _logger.warning(message)
                    try:
                        pointeuse.sudo().write_badge(badge_ids)
                        for badge_id in badge_ids:
                            badge_id.sudo().pointeuse_ids += pointeuse
                        message = u"Fin d'insertion de %d badges dans la pointeuse:%s" % (
                            len(badge_ids), pointeuse.name)
                        _logger.warning(message)

                    except Exception as exx:
                        message = u"Erreur de copie de la pointeuse" + pointeuse_a_copie.name + " dans " + pointeuse.name + ":" + exx.message
                        _logger.warning(message)
                        succes = False

                if succes:
                    message = u"Copie avec succés de la pointeuse %s dans les autres" % pointeuse_a_copie.name
                    _logger.warning(message)

            for pointeuse in pointeuse_ids:
                _logger.warning(u"Début de nétoyage de la pointeuse %s " % pointeuse_a_copie.name)
                pointeuse.nettoyer_pointeuse(False)
                _logger.warning(u"Fin de nétoyage de la pointeuse %s " % pointeuse_a_copie.name)
        except Exception as ex:
            _logger.warning("Sortie cron_syncroniser_pointeuses avec erreur :" + ex.message)

        _logger.warning(u"Fin cron_syncroniser_pointeuses")

