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

    
    def add_user(self, machineid, uid, name, privilege, password, groupid, userid, card):
        machine_id = self.env['kzm.hr.pointeuse'].browse(machineid)
        #machine_id.get_status()
        zk, conn = False, False
        try:
            zk = pyzk.ZK(machine_id.ip, int(machine_id.port), timeout=10)
            conn = zk.connect()
            conn.disable_device()
            machine_id.connection_state = True
        except:
            machine_id.connection_state = False

        if machine_id.connection_state and conn:
            try:
                #time.sleep(1)
                conn.set_user(int(uid), name, privilege, password, groupid, str(int(userid)).zfill(5), int(card))
                if conn:
                    conn.enable_device()
                    conn.disconnect()
                return (_("User ") + name + _(" est ajouté au ") + machine_id.name + '\n'), True
            except Exception as e:
                if conn:
                    conn.enable_device()
                    conn.disconnect()
                return (_("Echec d'ajout d'utilisateur ") + name+_(" dans la pointeuse ") + machine_id.name + '\n Erreur:'+str(e)), False
        else:
            if conn:
                conn.enable_device()
                conn.disconnect()
            return (_("Connection to ") + machine_id.name + _(" has been lost, couldn't add user ") + name + '\n'), False




    def add_user_to_machine(self, machineid):
        for record in self:
            machine_ids = self.env['kzm.hr.pointeuse'].browse(machineid)
            for machine_id in machine_ids:
                machine_id.get_status()
                if machine_id.connection_state == True:
                    # try:

                    msg, state = record.add_user(machine_id.id, record.uid, str(record.employee_id.name), int(record.privilege),
                              str(record.password), str(record.groupid), str(record.userid), int(record.cardnumber))
                    if state:
                        record.with_context(ignorecode=True).write({'pointeuse_ids': [(6, False, [machine_id.id,])]})
                    else:
                        raise Exception(_("Operation d'ajout d'utilisateur ") + (record.employee_id.name) + " a échouée\n"+msg)

                    # except Exception as e:
                    #     raise Exception(e)

    def delete_user(self, machineid, uid):
        machine_id = self.env['kzm.hr.pointeuse'].browse(machineid)
        zk, conn = False, False
        try:
            zk = pyzk.ZK(machine_id.ip, int(machine_id.port), timeout=10)
            conn = zk.connect()
            conn.disable_device()
            machine_id.connection_state = True
        except:
            machine_id.connection_state = False

        if machine_id.connection_state and conn:

            time.sleep(1)
            try:
                conn.delete_user(int(uid))
            except:
                if conn:
                    conn.enable_device()
                    conn.disconnect()
                return (_("User does not exist in ") + machine_id.name + '\n'), False
            if conn:
                conn.enable_device()
                conn.disconnect()
            return (_('User Deleted from ') + machine_id.name + '\n'), True

        else:
            if conn:
                conn.enable_device()
                conn.disconnect()
            return (_("Connection to ") + machine_id.name + _(" has been lost, couldn't delete user") + '\n'), False


    def _card_to_str(self):
        for r in self:
            if (r.cardnumber == 0):
                r.cardstr = 'N/A'
            else:
                r.cardstr = str(r.cardnumber)



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



    def write(self, vals):

        res = super(KzmBadge, self).write(vals)
        not_upadte_badge = self._context.get('ignorecode', False)
        if not not_upadte_badge and (
                vals.get('matricule', False) or vals.get('pointeuse_ids', False) or vals.get('password', False) or vals.get('cardnumber', False)):
            for this in self:
                this.with_context(ignorecode=not_upadte_badge).ajouter_badge_pointeuse()
        return res


    def unlink(self):
        badges_administration_ids = self#.filtered(lambda l: l.employee_id.type_employe == 'mensuel')
        for rec in badges_administration_ids:
            for p in rec.sudo().pointeuse_ids:
                try:
                    p.delete_badge(rec)
                    # squery = "delete from kzm_r_hr_pointeuse_badge where id_badge=%s and id_pointeuse=%s " % (rec.id, p.id)
                    # self._cr.execute(squery)
                    # self._cr.commit()
                except Exception as ex:
                    rec.message_post(
                        body=_(u"Echec de suppression de %s de la pointeuse %s.\n%s" % (
                        rec.employee_id.name, p.name, ex)))
                    #raise ValidationError(_(u"Echec de suppression de %s de la pointeuse %s.\n%s" % (
                        #rec.employee_id.name, p.name, ex)))

        # if len(rec.pointeuse_ids) == 0:
        res = super(KzmBadge, self).unlink()
        return res



    def force_unlink(self):
        return super(KzmBadge, self).unlink()

    
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
        # if not contract_id or contract_id.date_end:
        #     raise ValidationError(
        #             u"L'employé : %s matricule : %s ne posséde pas de contrat active \n il faut l'embaucher avant de lui créer le badge!" % (
        #             self.employee_id.name, self.employee_id.matricule))

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
            raise ValidationError(u'Numéro de badge saisi est invalide.\n il doit être sur 7 ou 8 numéros !')



