# -*- coding: utf-8 -*-
from inspect import getmembers
from pprint import pprint
from odoo import models, fields, api , _
from odoo.exceptions import ValidationError
from ..tools.pyzk import zk as pyzk
import time


class KzmBadge(models.Model):
    _name = "kzm.hr.pointeuse.badge"
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _description = 'Badge'
    _order = 'date desc'

    @api.depends('employee_id')
    def _compute_name(self):
        for r in self:
            r.name = "Badge_%s" % (r.employee_id.matricule or '')

    @api.depends('employee_id', 'employee_id.matricule')
    def compute_uid_userid_fields(self):
        for o in self:
            o.uid = int(o.matricule or 0)
            o.userid = int(o.matricule or 0)

    matricule = fields.Char(string=_("Matricule"), required=False, readonly=True, related='employee_id.matricule',
                            store=True)
    name = fields.Char(string=_("Nom"), compute="_compute_name", store=True, )
    active = fields.Boolean(string=_("Active"), default=True)

    date = fields.Date(string=_("Creation Date"), default=fields.Date.today)
    cardnumber = fields.Char(string=_("Numéro de badge"), required=True, )
    cardstr = fields.Char(string=_("Badge Number:"), compute='_card_to_str')
    pointeuse_ids = fields.Many2many(comodel_name="kzm.hr.pointeuse",
                                     relation="kzm_r_hr_pointeuse_badge", column1="id_badge",
                                     column2="id_pointeuse", string=_("Pointeuses"), required=True)
    privilege = fields.Selection([
        ('0', 'Normal'),
        ('1', _('User')),
        ('14', _('Admin')),
    ], string=_("Privilige"),
        default='0',
        required=True
    )
    password = fields.Char(string=_("Password"), required=False, default="123456")
    groupid = fields.Integer(string=_("Group ID"))
    employee_id = fields.Many2one(comodel_name="hr.employee", string=_("Employé"), required=True, )

    #mandatory by kzm_zk_attendance
    # uid and userid will be the matricule
    # userid will have the id of the badge
    uid = fields.Integer(string=_("uid"), compute=compute_uid_userid_fields)
    userid = fields.Integer(string=_("userid"), compute=compute_uid_userid_fields)
    company_id = fields.Many2one(comodel_name="res.company", ondelete='cascade', string=_("Society"),
                                 required=True,
                                 default=lambda self: self.env.company)


    _sql_constraints = [
        # ('badge_name_uniq','UNIQUE (name)', 'Le badge doit être unique.'),
        ('cardnumber_uniq', 'UNIQUE (cardnumber)', 'Le numéro de badge est déjà attribué.')
    ]



    def are_connected(self, args):
        verify_online = True
        for machines_list in args:
            for machineid in machines_list:
                machine_id = self.env['kzm.hr.pointeuse'].browse(machineid)
                machine_id.get_status()
                verify_online = verify_online and machine_id.connection_state
                if not verify_online: break;
        return verify_online

    def list_not_connected(self, args):
        verify_online = []
        for machines_list in args:
            for machineid in machines_list:
                machine_id = self.env['kzm.hr.pointeuse'].browse(machineid)
                machine_id.get_status()
                if not machine_id.connection_state:
                    verify_online.append(machine_id.name)
        return verify_online

    # def add_user(self, machineid, uid, name, privilege, password, groupid, userid, card):
    #     machine_id = self.env['kzm.hr.pointeuse'].browse(machineid)
    #     machine_id.get_status()
    #     isConnected = machine_id.connection_state
    #
    #     if isConnected == True:
    #         try:
    #             zk = pyzk.ZK(machine_id.ip, int(machine_id.port), timeout=10)
    #             conn = zk.connect()
    #             time.sleep(1)
    #             print("AAAAAAAAAAAAAAAAAAAAA")
    #             # print(type(uid), type(name), type(privilege), type(password), type(groupid), str(int(userid)), type(card))
    #             # print(uid, name, privilege, password, groupid, userid, card)
    #             # conn.set_user(uid, name, privilege, password, groupid, str(int(userid)), card)
    #             dict = {
    #                 'uid' : uid,
    #                 'name' : name,
    #                  'privilege' : privilege,
    #                  'password' : password,
    #                 'group_id' : groupid,
    #                'user_id' : str(int(userid)),
    #                  'card' : card
    #             }
    #             # pprint(dict)
    #             conn.set_user(
    #                 uid=uid,
    #                 name=name,
    #                 privilege=privilege,
    #                 password=password,
    #                 group_id=groupid,
    #                 user_id=str(int(userid)),
    #                 card=card
    #             )
    #             # machineid, uid, name, privilege, password, groupid, userid, card
    #             # (machine_id.id, record.uid, str(record.employee_id.name), int(record.privilege),
    #             #  str(record.password), str(record.groupid), str(record.userid), int(record.cardnumber))
    #
    #             # conn.set_user(uid=uid, name=name, privilege=privilege,
    #             #               password=password, group_id=groupid, user_id=str(int(userid)), card=card)
    #
    #             if conn: conn.disconnect()
    #             return (_("User ") + name + _(" est ajouté au ") + machine_id.name + '\n'), True
    #         except Exception as e:
    #             return (_("Echec d'ajout d'utilisateur ") + name+_(" dans la pointeuse ") + machine_id.name + '\n Erreur:'+str(e)), False
    #     else:
    #         return (_("Connection to ") + machine_id.name + _(" has been lost, couldn't add user ") + name + '\n'), False

    def add_user(self, machineid, uid, name, privilege, password, groupid, userid, card):
        machine_id = self.env['kzm.hr.pointeuse'].browse(machineid)
        #machine_id.get_status()
        zk, conn = False, False
        try:
            zk = pyzk.ZK(machine_id.ip, int(machine_id.port), timeout=10)
            conn = zk.connect()
            machine_id.connection_state = True
        except:
            machine_id.connection_state = False

        if machine_id.connection_state and conn:
            try:
                #time.sleep(1)
                conn.set_user(int(uid), name, privilege, password, groupid, str(int(userid)).zfill(5), int(card))
                if conn:
                    conn.disconnect()
                return (_("User ") + name + _(" est ajouté au ") + machine_id.name + '\n'), True
            except Exception as e:
                return (_("Echec d'ajout d'utilisateur ") + name+_(" dans la pointeuse ") + machine_id.name + '\n Erreur:'+str(e)), False
        else:
            return (_("Connection to ") + machine_id.name + _(" has been lost, couldn't add user ") + name + '\n'), False

    def add_user_to_machine(self, machineid):
        for record in self:
            machine_ids = self.env['kzm.hr.pointeuse'].browse(machineid)
            print("T1T1T1T1T1T1T1T1T1T1")
            print("T1T1T1T1T1T1T1T1T1T1")
            print(machineid)
            print(machine_ids)
            for machine_id in machine_ids:
                machine_id.get_status()
                if machine_id.connection_state == True:
                    # try:

                    print("TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT")
                    print(machine_id.id, record.uid, str(record.employee_id.name),
                                  int(record.privilege),str(record.password), str(record.groupid), str(record.userid), int(record.cardnumber))
                    msg, state = record.add_user(machine_id.id, record.uid, str(record.employee_id.name), int(record.privilege),
                              str(record.password), str(record.groupid), str(record.userid), int(record.cardnumber))
                    print("TTT:", state, msg)
                    if state:
                        record.with_context(ignorecode=True).write({'pointeuse_ids': [(6, False, [machine_id.id,])]})
                    else:
                        raise Exception(_("Operation d'ajout d'utilisateur ") + (record.employee_id.name) + " a échouée\n"+msg)

                    # except Exception as e:
                    #     raise Exception(e)

    # def delete_user(self, machineid, uid):
    #     machine_id = self.env['kzm.hr.pointeuse'].browse(machineid)
    #     machine_id.get_status()
    #     isConnected = machine_id.connection_state
    #     if isConnected == True:
    #         zk = pyzk.ZK(machine_id.ip, int(machine_id.port), timeout=10)
    #         conn = zk.connect()
    #         time.sleep(1)
    #         print("======================", int(uid))
    #         ok = conn.delete_user(int(uid))
    #         print("======================", ok)
    #         if conn : conn.disconnect()
    #         if ok:
    #             return (_('User Deleted from ') + machine_id.name + '\n'), True
    #         else:
    #             return (_("User does not exist in ") + machine_id.name + '\n'), False
    #     else:
    #         return (_("Connection to ") + machine_id.name + _(" has been lost, couldn't delete user") + '\n'), False
    def delete_user(self, machineid, uid):
        machine_id = self.env['kzm.hr.pointeuse'].browse(machineid)
        zk, conn = False, False
        try:
            zk = pyzk.ZK(machine_id.ip, int(machine_id.port), timeout=10)
            conn = zk.connect()
            machine_id.connection_state = True
        except:
            machine_id.connection_state = False

        if machine_id.connection_state and conn:

            time.sleep(1)
            try:
                conn.delete_user(int(uid))
            except:
                return (_("User does not exist in ") + machine_id.name + '\n'), False
            if conn:
                conn.disconnect()
            return (_('User Deleted from ') + machine_id.name + '\n'), True

        else:
            return (_("Connection to ") + machine_id.name + _(" has been lost, couldn't delete user") + '\n'), False


    def _card_to_str(self):
        for r in self:
            if (r.cardnumber == 0):
                r.cardstr = 'N/A'
            else:
                r.cardstr = str(r.cardnumber)

    # @api.model
    # def create(self, values):
    #     """
    #     Method kzm_attendance
    #     :param values:
    #     :return:
    #     """
    #     # machines = values.get('pointeuse_ids', False)
    #     # print("------ Maciines",machines)
    #     # if machines:
    #     # 	for l in machines:
    #     # 		rec_machine = self.env['kzm.hr.pointeuse'].browse(machines[0][2])
    #     # 		print("Records :::::", rec_machine)
    #     print("####1###")
    #     records = super(KzmBadge, self).create(values)
    #     print("###2###")
    #     for record in records:
    #         # record.uid    = record.id
    #         # record.userid = record.employee_id.id
    #         # record.with_context(ignorecode=True).write({'uid': record.id, 'userid': record.employee_id.id})
    #         record.with_context(ignorecode=True).write({'uid': record.matricule, 'userid': record.matricule})
    #         mymachines = []
    #         mymachines_failed = []
    #
    #         for machine_id in record.machine_ids:
    #             machine_id.get_status()
    #             isConnected = machine_id.connection_state
    #             if isConnected == True:
    #                 mymachines.append(machine_id)
    #             self.add_user(machine_id.id, record.uid, str(record.employee_id.name_related), int(record.privilege),
    #                           str(record.password), str(record.groupid), str(record.userid), int(record.cardnumber))
    #         record.with_context(ignorecode=True).write({'pointeuse_ids': [(6, False, [l.id for l in mymachines])]})
    #         pprint(mymachines)
    #
    #     return records

    @api.model
    def create(self, vals):
        """
        Method Db_domaine
        :param vals:
        :return:
        """
        new_record = super(KzmBadge, self.with_context(ignorecode=True)).create(vals)
        new_record.with_context(ignorecode=True).ajouter_badge_pointeuse()
        return new_record

    #
    # def write(self, values):
    #     """
    #     Method kzm_zk_attendance
    #     :param values:
    #     :return:
    #     """
    #     msg = ""
    #     pprint(values)
    #     pprint(self)
    #     records_oldmachines = {}
    #     for record in self:
    #         records_oldmachines[record.id] = list(record.pointeuse_ids.ids)
    #     res = super(KzmBadge, self).write(values)
    #     print("Context:", self._context)
    #     if not self._context.get('ignorecode', False):
    #         print("Edit Code:")
    #         for record in self:
    #             # print("#Newmachines")
    #             # pprint(newmachines)
    #             edits = True
    #             if (len(values) == 1 and values.has_key(u'pointeuse_ids')):
    #                 edits = False
    #
    #             uid = int(record.matricule)
    #             userid = str(record.matricule)
    #             pprint(values)
    #             if values.has_key(u'name'):
    #                 name = str(self.env['hr.employee'].browse(values.get(u'employee_id')))
    #             else:
    #                 name = str(record.employee_id.name_related)
    #
    #             if values.has_key(u'privilege'):
    #                 privilege = int(values.get(u'privilege'))
    #             else:
    #                 privilege = int(record.privilege)
    #
    #             if values.has_key(u'password'):
    #                 password = str(values.get(u'password'))
    #             else:
    #                 password = str(record.password)
    #
    #             if values.has_key(u'groupid'):
    #                 groupid = str(values.get(u'groupid'))
    #             else:
    #                 groupid = str(record.groupid)
    #
    #             if values.has_key(u'cardnumber'):
    #                 card = int(values.get(u'cardnumber'))
    #             else:
    #                 card = int(record.cardnumber)
    #
    #             if values.has_key(u'pointeuse_ids'):
    #                 newmachines = values.get(u'pointeuse_ids')
    #                 newmachines = list(newmachines[0][2])
    #             else:
    #                 # newmachines=list(record.pointeuse_ids.ids)
    #                 newmachines = records_oldmachines[record.id]
    #             # print("########")
    #             # pprint(newmachines)
    #             # oldmachines = list(record.pointeuse_ids.ids)
    #             oldmachines = records_oldmachines[record.id]
    #             pprint(oldmachines)
    #             pprint(newmachines)
    #             final = list(set(oldmachines).intersection(set(newmachines)))
    #             toadd = list(set(newmachines) - set(oldmachines))
    #             todelete = list(set(oldmachines) - set(newmachines))
    #             # Suppose all machines are online
    #             verify_online = True
    #             print("final", final)
    #             print("toadd", toadd)
    #             print("todelete", todelete)
    #             print(uid, name, privilege, password, groupid, userid, card)
    #
    #             if edits:
    #                 verify_online = verify_online and self.are_connected([toadd, todelete, final])
    #                 if verify_online:
    #                     for machineid in final:
    #                         print("###", machineid)
    #                         print("###", machineid, uid, name, privilege, password, groupid, userid, card)
    #                         msg += self.add_user(machineid, uid, name, privilege, password, groupid, userid, card)[0]
    #                     for machineid in toadd:
    #                         msg += self.add_user(machineid, uid, name, privilege, password, groupid, userid, card)[0]
    #                     for machineid in todelete:
    #                         msg += self.delete_user(machineid, uid)[0]
    #             else:
    #                 if (len(toadd) > 0 and len(todelete) > 0):
    #                     verify_online = verify_online and self.are_connected([toadd, todelete])
    #                     print("==> ", verify_online)
    #                     if verify_online:
    #                         for machineid in toadd:
    #                             msg += self.add_user(machineid, uid, name, privilege, password, groupid, userid, card)[0]
    #                         for machineid in todelete:
    #                             msg += self.delete_user(machineid, uid)[0]
    #                 elif (len(toadd) > 0):
    #                     verify_online = verify_online and self.are_connected([toadd])
    #                     if verify_online:
    #                         for machineid in toadd:
    #                             print(machineid, uid, name, privilege, password, groupid, userid, card)
    #                             msg += self.add_user(machineid, uid, name, privilege, password, groupid, userid, card)[0]
    #                 else:
    #                     verify_online = verify_online and self.are_connected([todelete])
    #                     if verify_online:
    #                         for machineid in todelete:
    #                             msg += self.delete_user(machineid, uid)[0]
    #     return res


    def write(self, vals):

        res = super(KzmBadge, self).write(vals)
        if self.write_uid.id == 1 and 'pointeuse_ids' in vals:
            return res
        not_upadte_badge = self._context.get('ignorecode', False)
        if not not_upadte_badge and (
                vals.get('matricule', False) or vals.get('pointeuse_ids', False) or vals.get('password',
                                                                                             False) or vals.get(
                'cardnumber', False)):
            for this in self:
                this.ajouter_badge_pointeuse()
        return res

    #
    # def unlink(self):
    #     """
    #     Method kzm_zk_attendance
    #     :return:
    #     """
    #     pprint(self)
    #     flag = True
    #     not_connected = []
    #     for record in self:
    #         Machines = list(record.pointeuse_ids.ids)
    #         not_connected += self.list_not_connected([Machines])
    #         print(not_connected)
    #         verify_online = self.are_connected([Machines])
    #         if not not_connected:
    #             for machineid in Machines:
    #                 self.delete_user(machineid, record.uid)
    #             res = super(KzmBadge, record).unlink()
    #             return res
    #         else:
    #             flag = False
    #
    #     if not flag:
    #         raise ValidationError(_("Not All machines are connected! :") + "\n%s" % "\n".join(not_connected))

    # def unlink(self):
    #     # res = super(KzmBadge, self).unlink()
    #     badges_administration_ids = self.filtered(lambda l: l.employee_id != False)
    #     for rec in badges_administration_ids:
    #         for p in rec.sudo().pointeuse_ids:
    #             try:
    #                 p.delete_badge(rec)
    #                 rec.message_post(body=_(u'%s est supprimé de la pointeuse %s.' % (rec.employee_id.name, p.name)))
    #                 # squery = "delete from kzm_r_hr_pointeuse_badge where id_badge=%s and id_pointeuse=%s " % (rec.id, p.id)
    #                 # self._cr.execute(squery)
    #                 # self._cr.commit()
    #             except Exception as ex:
    #                 rec.message_post(
    #                     body=_(u"Echec de suppression de %s de la pointeuse %s.\n%s" % (
    #                     rec.employee_id.name, p.name, str(ex))))
    #                 if not "ErrorCode=" in str(ex):
    #                     raise ValidationError(_(u"Echec de suppression de %s de la pointeuse %s.\n%s" % (
    #                     rec.employee_id.name, p.name, str(ex))))
    #
    #     # if len(rec.pointeuse_ids) == 0:
    #     res = super(KzmBadge, self).unlink()
    #     return res

    def unlink(self):
        badges_administration_ids = self#.filtered(lambda l: l.employee_id.type_employe == 'mensuel')
        for rec in badges_administration_ids:
            for p in rec.sudo().pointeuse_ids:
                try:
                    p.delete_badge(rec)
                    rec.message_post(body=_(u'%s est supprimé de la pointeuse %s.' % (rec.employee_id.name, p.name)))
                    # squery = "delete from kzm_r_hr_pointeuse_badge where id_badge=%s and id_pointeuse=%s " % (rec.id, p.id)
                    # self._cr.execute(squery)
                    # self._cr.commit()
                except Exception as ex:
                    rec.message_post(
                        body=_(u"Echec de suppression de %s de la pointeuse %s.\n%s" % (
                        rec.employee_id.name, p.name, ex.message)))
                    raise ValidationError(_(u"Echec de suppression de %s de la pointeuse %s.\n%s" % (
                        rec.employee_id.name, p.name, ex.message)))

        # if len(rec.pointeuse_ids) == 0:
        res = super(KzmBadge, self).unlink()
        return res



    def force_unlink(self):
        return super(KzmBadge, self).unlink()

    #
    # def maj_badge(self):
    #     """ Method kzm_zk_attendance"""
    #     for b in self:
    #         machines = list(b.pointeuse_ids.ids)
    #         for machineid in machines:
    #             self.add_user(machineid, int(b.uid), str(b.employee_id.name_related), int(b.privilege), str(b.password),
    #                           str(b.groupid), str(b.userid), int(b.cardnumber))

    
    def maj_badge(self):
        """ Method db_domaine"""
        self.sudo().ajouter_badge_pointeuse()

    
    def ajouter_badge_pointeuse(self):
        message = ""
        for p in self.pointeuse_ids:
            try:
                p.write_badge(self)
                self.message_post(
                    body=_(u'Ajout réussi de %s dans la pointeuse %s.' % (self.employee_id.name, p.name)))
            except Exception as ex:
                self.message_post(
                    body=_(u'Ajout échoué de %s dans la pointeuse %s.\n Erreur :%s ' % (
                    self.employee_id.name, p.name, str(ex))))
                message += ", " + p.name + "\nErreur : " + str(ex)
        # self.env.commit()
        if len(message) > 1:
            raise ValidationError(
                u"Le systéme n'arrive pas à inserer l'empoyé %s dans les pointeuses : %s " % (
                self.employee_id.name, message))

    
    @api.constrains('employee_id')
    def insertion_pointeuses(self):
        contract_id = self.employee_id.contract_id
        if not contract_id or contract_id.date_end:
            raise ValidationError(
                    u"L'employé : %s matricule : %s ne posséde pas de contrat active \n il faut l'embaucher avant de lui créer le badge!" % (
                    self.employee_id.name, self.employee_id.matricule))

    def is_valid_cardnumber(self, cardnumber):
        try:
            int(cardnumber)
        except:
            return False

        if len(cardnumber) < 7 or len(cardnumber) > 9:
            return False

        return True

    
    @api.constrains('cardnumber')
    def check_cardnumber(self):
        if not self.is_valid_cardnumber(self.cardnumber):
            raise ValidationError(u'Numéro de badge saisi est invalide.\n il doit être sur 7 numéros !')



# class hr_employee(models.Model):
#     _inherit = 'hr.employee'
#     matricule = fields.Char(string=_("Matricule"), required=False, )
#     badge_ids = fields.One2many(comodel_name="kzm.hr.pointeuse.badge",
#                                 inverse_name="employee_id", string=_("Badges"),
#                                 required=False, readonly=False)
#
#
#
