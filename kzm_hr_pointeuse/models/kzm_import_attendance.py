# -*- coding: utf-8 -*-

import base64
from odoo import api
from datetime import date, datetime, timedelta
from odoo import models, fields
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from . import format_dates

class kzm_import_attendance(models.Model):
    _name = 'kzm.import.attendance'
    _rec_name = 'name'
    _description = 'Importation des presences'

    name = fields.Char(string=_("Référence"), required=False, readonly=True)
    company_id = fields.Many2one(comodel_name="res.company", ondelete='cascade', string=_("Ferme"), required=True,
                                 default=lambda self: self.env.company)
    # kzm_sous_ferme_id = fields.Many2one(comodel_name="sub.farm", default=lambda self: self.env.user.kzm_sous_ferme_ids and self.env.user.kzm_sous_ferme_ids[0] or False, string=_("Sous Ferme"), required=False, )

    attendance_ids = fields.One2many(comodel_name="hr.attendance", inverse_name="import_attendance_id", string=_("Présences"), required=False, )
    file_path = fields.Binary(string=_("Fichier de pointage"),  filters="*.csv")
    file_name = fields.Char(string=_(""), required=False, store=False, compute="get_file_name", size=64)
    journal_log = fields.Text(string=_("Journal de log"), required=False, )
    active = fields.Boolean('Active', default=True)

    has_errors = fields.Boolean(string=_("Erreurs?"), default=True, readonly=True)

    @api.model
    def create(self, vals):
        new_record = super(kzm_import_attendance, self).create(vals)
        if new_record:
            new_record.name=self.env['ir.sequence'].next_by_code('kzm.import.attendance')
        return new_record

    
    def load_attendance(self):
        try:
            value = base64.decodestring(self.file_path).replace("\"", '')
            lignes = value.split("\r\n")
            l_index = 1
            journal_log = ''
            for l in lignes[1:]:

                data = l.split(',')
                l_index += 1
                matricule = str(data[0]).rjust(5, "0")
                employee_id = self.env['hr.employee'].search([('matricule', '=', matricule)])


                if not employee_id:
                    journal_log += "Ligne : " + str(l_index) + \
                                   _("=> Employé " + data[0] +
                                     " introuvale." + "\n")
                    self.has_errors = False
                    continue
                try:
                    try:
                        presence_date = datetime.strptime(data[1], format_dates.FORMAT_DATE_TIME_FR)
                    except Exception as e:
                        presence_date = datetime.strptime(data[1], format_dates.FORMAT_DATE_TIME_EN)
                except Exception as e:
                    raise ValidationError(u'Ligne:%s Format date de présence est incorrecte.' % (l_index))


                attendance_count = self.env['hr.attendance'].\
                            search_count([('name','=', str(presence_date)),
                            ('employee_id','=',employee_id.id),
                            ('company_id', '=', self.company_id.id),

                            ])

                if attendance_count:
                    journal_log += "Ligne:" + str(l_index) + \
                                       _("=>La présence (%s, %s) existe déjà dans le système.\n"
                                       % (matricule, data[1]))
                    self.has_errors = False
                    continue

                attendance_id = {
                        'employee_id' : employee_id.id,
                        'company_id' : self.company_id.id,

                        'name' : str(presence_date),
                        'action' : 'sign_in',
                        'import_attendance_id' : self.id
                }

                try:
                    #self.env.cr.savepoint()
                    result = self.test_altern_si_so(attendance_id, presence_date)
                    if  employee_id.contract_id and result[0] == 4:
                        self.env['hr.attendance'].create(attendance_id)
                    elif employee_id.contract_id and result[0] == 0:
                        attendance_id['action'] = 'sign_out'
                        self.env['hr.attendance'].create(attendance_id)
                    elif employee_id.contract_id and result[0] == 1:
                        new_attendance_id = {
                                'employee_id' : employee_id.id,
                                'company_id' : self.company_id.id,

                                'name' : str(result[1] + timedelta(minutes=1)),
                                'action' : 'sign_out',
                                'note' : 'Présence ajoutée automatiquement.',
                                'import_attendance_id' : self.id
                        }
                        self.env['hr.attendance'].create(new_attendance_id)
                        self.env['hr.attendance'].create(attendance_id)
                    elif result[0] == 5:
                        result[1].write({'name':result[2]})
                        attendance_id['action'] = 'sign_out'
                    elif result[0] == 3:
                        continue
                    else:
                        journal_log += "Ligne:" + str(l_index) + \
                                       _("=>La présence (%s, %s) ne peut pas être insérer."
                                       % (matricule, attendance_id['name']))
                        self.has_errors = False
                        continue
                    if employee_id:
                        employee_id.write(
                                {
                                    'last_ferm_pointage':self.company_id.id,

                                    'last_date_pointage':str(presence_date)
                                }
                        )

                    #self.env.cr.commit()
                except Exception as e:
                    raise ValidationError(_(e.message or e.value))
            self.journal_log = journal_log
        except Exception as e:
            raise ValidationError(_(e.message or e.value))

    
    def get_file_name(self):
        self.file_name = "Pointage_" + self.company_id.name.strip() \
                         + "_" + date.today().strftime('%Y%m%d') + ".txt"


    def test_altern_si_so(self, att, presence_date):
        self.ensure_one()
        """
           Alternance sign_in/sign_out check.
           Previous (if exists) must be of opposite action.
           Next (if exists) must be of opposite action.
        """
        # search and browse for first previous and first next records
        prev_att_ids = self.env['hr.attendance'].search([('employee_id', '=', att['employee_id']), ('name', '<', att['name']), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name DESC')
        next_add_ids = self.env['hr.attendance'].search([('employee_id', '=', att['employee_id']), ('name', '>', att['name']), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name ASC')
        # check for alternance, return False if at least one condition is not satisfied

        if prev_att_ids and prev_att_ids[0].action == att['action']: # previous exists and is same action
            prev_date = fields.Datetime.from_string(prev_att_ids[0].name)
            if prev_date.date() == presence_date.date():
                return [0,]
            return [1, prev_date]
            """date_start = fields.Datetime.from_string(prev_date.date().strftime('%Y-%m-%d 17:59:69'))
            date_end = fields.Datetime.from_string(prev_date.date().strftime('%Y-%m-%d 00:00:01')) + timedelta(days=1)
            if prev_date < date_start:
                return [1, prev_date]
            return [5, prev_att_ids[0], date_end]"""
        if next_add_ids and next_add_ids[0].action == att['action']: # next exists and is same action
            return [2,]
        if (not prev_att_ids) and (not next_add_ids) and att['action'] != 'sign_in': # first attendance must be sign_in
            return [3,]
        return [4,]




class hr_attendance(models.Model):

    _inherit = 'hr.attendance'
    note = fields.Text(string=_("Note"), required=False, )
    import_attendance_id = fields.Many2one(comodel_name="kzm.import.attendance", string=_(""), required=False, ondelete='cascade')