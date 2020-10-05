# -*- encoding: utf-8 -*-

from odoo import api
from odoo import exceptions
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class kzm_all_attendances(models.Model):
    _inherit = 'mail.thread'
    _name = 'kzm.all.attendances'
    _description = 'Pointage Journalier'
    _order = "name desc"

    @api.depends("name")
    def _compute_is_free_day(self):
        for o in self:
            if o.name:
                o.is_free_day = self.env['specific.holidays'].is_free_date(o.name)

    reference = fields.Char(string=_("Référence"), required=False, readonly=True,
                            default=lambda self: self.env['ir.sequence'].next_by_code('kzm.all.attendances.sequence'))
    name = fields.Date(string=_("Date Pointage Journalier"), index=True, required=True, default=fields.Date.today())
    company_id = fields.Many2one(comodel_name="res.company", ondelete='cascade', string=_("Société"), required=True,
                                 default=lambda self: self.env.company)


    state = fields.Selection(string=_("Etat"), selection=[('draft', 'Ouvert'), ('done', 'Fermé'), ], required=False,
                             default="draft")
    kzm_daily_attendance_ids = fields.One2many(comodel_name="kzm.daily.attendance",
                                               inverse_name="kzm_all_attendances_id",
                                               string=_("Liste des pointages journaliers"),
                                               required=False,
                                               )
    active = fields.Boolean('Active', default=True)
    statistic_ids = fields.One2many(comodel_name="kzm.poste.pointage.journalier",
                                    inverse_name="kzm_all_attendances_id",
                                    string=_("Statistique"), required=False, )
    total_jour = fields.Float(string=_("Total jours"), )
    # store=True, compute='compute_total_jour', )
    total_employee = fields.Integer(string=_("Total Employés"), required=False, )

    # store=True, compute='compute_total_employee', default=0)
    is_free_day = fields.Boolean("Jour férié", compute=_compute_is_free_day, store=True)


    def update_jf_pd(self):
        self._compute_is_free_day()
        for o in self:
            o.kzm_daily_attendance_ids.update_ps_dejeuner()


    def action_pointage_journalier_pnt(self):
        self.ensure_one()
        action = self.env.ref('kzm_hr_pointeuse.action_kzm_daily_attendance_all')
        action = action.read()[0]
        action['domain'] = [
            ('id', 'in', [l.id for l in self.kzm_daily_attendance_ids])]
        action['context'] = {'default_kzm_all_attendances_id': self.id,
                             'search_default_kzm_all_attendances_id': self.id}

        return action


    def action_statistiques_pnt(self):
        self.ensure_one()
        action = self.env.ref('kzm_hr_pointeuse.action_kzm_poste_pointage_jrn_all')
        action = action.read()[0]
        action['domain'] = [
            ('id', 'in', [l.id for l in self.statistic_ids])]
        action['context'] = {'default_kzm_all_attendances_id': self.id,
                             'search_default_kzm_all_attendances_id': self.id}

        return action

    
    # @api.depends('kzm_daily_attendance_ids')
    def compute_total_employee(self):
        self.total_employee = len(self.kzm_daily_attendance_ids)


    # @api.depends('kzm_daily_attendance_ids.heure_normal')
    def compute_total_jour(self):
        for rec in self:
            if rec.kzm_daily_attendance_ids:
                nbr_heures_jour = rec.kzm_daily_attendance_ids[0].employee_id.type_contract_id.nbr_heur_par_jour
                total_heures = sum([x.heure_normal for x in rec.kzm_daily_attendance_ids])
                if nbr_heures_jour > 0:
                    rec.total_jour = total_heures / nbr_heures_jour
                else:
                    rec.total_jour = total_heures / 8


    def write(self, vals):

        super(kzm_all_attendances, self).write(vals)
        if 'kzm_daily_attendance_ids' in vals:
            self.compute_total_jour()
            self.compute_total_employee()
        return True

    _sql_constraints = [('all_attendance_date_uniq', 'UNIQUE (name, company_id)',
                         u'Un seul pointage journalier est possible par jour et par société.')]

    
    def generate_kzm_daily_attendance_ids(self):
        hr_ids = []
        if self.kzm_daily_attendance_ids:
            attendance_ids = self.kzm_daily_attendance_ids.filtered(lambda l: l.loaded == 'auto')
            for att in attendance_ids:
                att.generate_attendances()
                att.calcule_duree()
                hr_ids += [att.employee_id.id]

                # ib select maybe will add
                # "hr_attendance.check_in as check_in, " \
                # "hr_attendance.check_out as check_out," \
                # "hr_attendance.worker_hours as worker_hours, " \
        req = "DELETE FROM kzm_daily_attendance where kzm_all_attendances_id is null; " \
              "SELECT DISTINCT hr_attendance.company_id as company_id,type_contract_id, " \
              "hr_attendance.employee_id as employee_id, " \
              "date(hr_attendance.check_in) as date " \
              "FROM hr_attendance , hr_employee " \
              "WHERE hr_attendance.employee_id = hr_employee.id " \
              "and date(hr_attendance.check_in) = '{}' " \
              "and hr_attendance.company_id = {} " \
              "AND hr_attendance.type_employe='journalier' " \
              "".format(self.name, self.company_id.id)
        if hr_ids:
            str = "{}".format(hr_ids)
            str = str.replace('[', '(')
            str = str.replace(']', ')')
            req += " AND hr_attendance.employee_id not in {} ".format(str)

        self.env.cr.execute(req)

        kzm_daily_attendance_ids = self.env['kzm.daily.attendance']
        for att in self.env.cr.dictfetchall():
            att['kzm_all_attendances_id'] = self.id
            att['loaded'] = 'auto'
            # TODO verifiy the fields "check_in,check_out,worker_hours" if are exists in kzm.daily.attendance
            daily = self.env['kzm.daily.attendance'].new(att)
            daily.generate_attendances()
            daily.calcule_duree()

            # daily.type_contract_id=daily.employee_id.type_contract_id
            kzm_daily_attendance_ids += daily
        self.kzm_daily_attendance_ids += kzm_daily_attendance_ids
        # kzm_daily_attendance_ids.commited()

    
    def calculer_montants(self):
        self.kzm_daily_attendance_ids.initialisation_valeur()
        for daily in self.kzm_daily_attendance_ids:
            daily.compute_montant_heure_normal()
            daily.compute_montant_heure_sup()

    
    def action_cancel(self):
        self.state = 'draft'

    
    def action_terminer(self):
        self.state = 'done'

    
    def copy(self, default=None):

        default = default or {}
        default.update({
            'name': fields.Datetime.from_string(self.name) + timedelta(days=1),
            'reference': self.env['ir.sequence'].next_by_code('kzm.all.attendances.sequence'),

        })
        result = super(kzm_all_attendances, self).copy(default)

        default = {'kzm_all_attendances_id': result.id}

        result.kzm_daily_attendance_ids = self.kzm_daily_attendance_ids.copy(default)

        for d in result.kzm_daily_attendance_ids:
            d.duree = 0.0
            d.heure_normal = d.employee_id.type_contract_id.nbr_heur_par_jour
            d.heure_sup = 0.0
            d.loaded = 'free'
            d.exception = ''

        return result


class kzm_daily_attendance(models.Model):
    _name = 'kzm.daily.attendance'
    _rec_name = 'employee_id'
    _description = 'Pointage journalier'


    def initialisation_valeur(self):
        for rec in self:
            if rec.employee_id and rec.employee_id.type_contract_id:
                rec.type_contract_id = rec.employee_id.type_contract_id
            else:
                rec.type_contract_id = False

    def _compute_pause_dej(self):
        return self.env['specific.pause'].get_pause_text()

    type_contract_id = fields.Many2one(comodel_name="hr.contract.type", string=_("Type de contrat"),
                                       # related='employee_id.type_contract_id',store=True)
                                       # default=lambda self: self.employee_id.type_contract_id,
                                       required=True
                                       )

    attendance_ids = fields.One2many(comodel_name="hr.attendance",
                                     inverse_name="kzm_daily_attendance_id",
                                     string=_("Pointages"), required=False,
                                     # compute="generate_attendances",
                                     copy=False)
    kzm_all_attendances_id = fields.Many2one(comodel_name="kzm.all.attendances", string=_("Liste des pointages"),
                                             required=False, ondelete='cascade')
    date = fields.Date(string=_("Date"), store=True, related='kzm_all_attendances_id.name',
                       index=True, )
    # check_in = fields.Datetime(string="Check In")
    # check_out = fields.Datetime(string="Check Out")
    # worked_hours = fields.Float(string='Worked Hours')

    company_id = fields.Many2one(comodel_name="res.company", ondelete='cascade', string=_("Société"),
                                 store=True, related="kzm_all_attendances_id.company_id", )


    employee_id = fields.Many2one(comodel_name="hr.employee", string=_("Employé"),
                                  required=True, ondelete='cascade', index=True)
    matricule = fields.Char(string=_("Matricule"), related='employee_id.matricule', required=False, store=True)

    duree = fields.Float(string=_("Durée"), readonly=True, digits=(8, 2))
    heure_normal = fields.Float(string=_("H.N."), required=False, help=u'Heure normal', digits=(8, 2),
                                default=lambda self: self.employee_id.type_contract_id.nbr_heur_par_jour)
    heure_sup = fields.Float(string=_("H.S."), required=False, default=0.0, help=u'Heure supplémentaire', digits=(8, 2))
    note = fields.Char(string=_("Observation"), required=False, )
    state = fields.Selection(string=_("State"), selection=[('draft', 'Nouveau'), ('done', 'Terminé'), ], required=False,
                             default='draft')
    exception = fields.Text(string=_("Erreur de pointage"), required=False, readonly=True)
    loaded = fields.Selection(string=_("Type"),
                              selection=[('manu', 'Manuel'), ('auto', 'Automatique'), ('free', 'Férié')],
                              required=False, default='manu')

    montant_heure_normal = fields.Float(string=_("M.H.N"), required=False,
                                        default=0.0,
                                        store=True,
                                        help=u'Montant heures normales', digits=(8, 2))
    montant_heure_sup = fields.Float(string=_("M.H.S."), required=False,

                                     default=0.0,
                                     store=True,
                                     help=u'Montant des heures supplémentaires', digits=(8, 2))
    montant_total = fields.Float(string=_("M.T."),
                                 compute='compute_montant_total',
                                 store=True,
                                 help=u'Montant total', digits=(8, 2))

    is_free_day = fields.Boolean(u"Jour férié", related='kzm_all_attendances_id.is_free_day')
    pause_djr = fields.Char("Pause déjeuner", default=_compute_pause_dej)


    def update_ps_dejeuner(self):
        dj = self.env['specific.pause'].get_pause_text()
        self.write({'pause_djr': dj})

    
    @api.depends('montant_heure_normal', 'montant_heure_sup')
    def compute_montant_total(self):
        self.montant_total = self.montant_heure_normal + self.montant_heure_sup

    
    # @api.depends('heure_normal')
    # def compute_montant_heure_normal(self):
    #     if self.type_contract_id and self.type_contract_id.nbr_heur_par_jour != 0:
    #         taux_horaire = self.type_contract_id.salaire_journalier / self.type_contract_id.nbr_heur_par_jour
    #         self.montant_heure_normal = self.heure_normal * taux_horaire

    
    @api.depends('heure_sup')
    def compute_montant_heure_sup(self):
        if self.type_contract_id:
            taux_horaire = self.type_contract_id.hour_salary
            self.montant_heure_sup = self.heure_sup * taux_horaire

    
    @api.constrains('heure_normal', 'heure_sup')
    def _check_value(self):
        if not self.type_contract_id:
            raise exceptions.Warning("L'employée ne posséde pas de type de contrat, Merci de le recruter")
        nb_heure_jour = self.type_contract_id.nbr_heur_par_jour
        if self.heure_normal > nb_heure_jour:  # or self.heure_sup > nb_heure_jour*2:
            raise exceptions.Warning("Heures normales (respéctivement Heures supplémentaires)"
                                     " ne peuvent pas dépasser 08 heurs/jour ")

    @api.onchange('heure_normal')
    def compute_heures(self):
        for o in self:
            nb_heure_jour = o.type_contract_id.nbr_heur_par_jour
            if o.heure_normal and o.heure_normal > nb_heure_jour:
                o.heure_sup = o.heure_normal - nb_heure_jour
                o.heure_normal = nb_heure_jour

    @api.model
    def create(self, vals):
        try:
            new_record = super(kzm_daily_attendance, self).create(vals)
            new_record.heure_normal = new_record.type_contract_id.nbr_heur_par_jour
            date1 = fields.Datetime.from_string(new_record.date).strftime('%Y-%m-%d 08:00:00')
            date1 = fields.Datetime.from_string(date1)
            date2 = new_record.employee_id.last_date_pointage \
                    and fields.Datetime.from_string(new_record.employee_id.last_date_pointage) \
                    or False

            if not date2 or date1 > date2:
                new_record.employee_id.write(
                    {'last_ferm_pointage': new_record.company_id.id,


                     'last_date_pointage': date1})

            return new_record
        except Exception as ex:
            self.env.cr.rollback()
            employee_id = self.env['hr.employee'].search([('id', '=', vals['employee_id'])])
            if employee_id:
                if str(ex).find('kzm_daily_attendance_company_id_employee_id_uniq') > 0 and vals['loaded'] == 'auto':

                    raise ValidationError(_(
                        u"L'employé %s , matricule = %s est présent dans la pointeuse et vous l'avez ajouter manuellement\n Merci de le supprimer afin de pouvoir faire le chargement " % (
                            employee_id.name, employee_id.matricule)))
                else:
                    raise ValidationError(_(
                        "Erreur de creation de la presence de L'employé %s , matricule = %s \nUn seul pointage journalier est possible par jour et par ferme \n" %(
                            employee_id.name, employee_id.matricule)))
            else:
                employee_id = self.env['hr.employee'].search([('id', '=', vals['employee_id']), ('active', '=', False)])
                if employee_id:
                    raise ValidationError(_(
                        u"L'employé %s , matricule = %s est inactif et présent dans la pointeuse \n Merci de consulter votre administrateur " % (
                            employee_id.name, employee_id.matricule)))
                else:
                    raise ValidationError(_(
                        u"Erreur inattendu, L'employée avec l'id=%s n'existe plus dans le sysstème\n Merci de le supprimer afin de pouvoir faire le chargement " % (
                            vals['employee_id'])))

    
    def calcule_duree(self):
        duree = 0.0
        # for att in self.attendance_ids:
        #     if not att.sign_in or not att.sign_out:
        #         self.exception = u'Entrée (resp. Sortie) est manquante dans quelques présences.'
        #         break
        #     if att.sign_in and att.sign_out:
        #         start_date = fields.Datetime.from_string(att.sign_in)
        #         end_date = fields.Datetime.from_string(att.sign_out)
        #         duree += (end_date - start_date).seconds / 3600.0
        self.duree = sum([att.worked_hours for att in self.attendance_ids])

    
    def generate_attendances(self):
        if self.kzm_all_attendances_id.name:
            start_date = fields.Datetime.from_string(self.kzm_all_attendances_id.name).strftime('%Y-%m-%d 00:00:00')
            end_date = fields.Datetime.from_string(self.kzm_all_attendances_id.name).strftime('%Y-%m-%d 23:59:59')
            self.attendance_ids = self.env['hr.attendance'].search(
                [
                    ("check_in", '>=', start_date),
                    ("check_in", '<=', end_date),
                    ('company_id', '=', self.kzm_all_attendances_id.company_id.id),
                    ('employee_id', '=', self.employee_id.id)
                ],
                order="id"
            )

    @api.onchange('employee_id')
    def check_unique_employee(self):
        for o in self:
            parent_id = o.env.context.get('parent_id', False)
            parent_id = o.env['kzm.all.attendances'].browse(parent_id) or False
            if parent_id and parent_id.kzm_daily_attendance_ids and o.employee_id:
                for x in parent_id.kzm_daily_attendance_ids:
                    if o.employee_id.id == x.employee_id.id:
                        # name = self.employee_id.name
                        # self.env.cr.savepoint()
                        # self.employee_id = False
                        # self.env.cr.commit()
                        raise ValidationError(_(u"L'employé %s est dejà saisi" % (o.employee_id.name)))
            o.type_contract_id = o.employee_id.type_contract_id

    _sql_constraints = [
        ('kzm_employee_id_all_attendances_id_uniq',
         'UNIQUE (employee_id, kzm_all_attendances_id)',
         _(u'Vous avez saisie des employés en double.'))
    ]


    def details(self):
        view = {
            'name': _('Détail'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'kzm.daily.attendance',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'readonly': True,
            'res_id': self.id,
        }
        return view


    def unlink(self, bAuto=False):
        if not bAuto:
            for this in self:
                if this.loaded == 'auto':
                    raise ValidationError(_(u'Suppression de la ligne chargée automatiquement est impossible.'))
        super(kzm_daily_attendance, self).unlink()
        return True


class kzm_hr_attendance(models.Model):
    _inherit = 'hr.attendance'
    kzm_daily_attendance_id = fields.Many2one(comodel_name="kzm.daily.attendance",
                                              string=_("Pointage Journalier"),
                                              required=False, )


class kzm_conf_categorie_ressource_humaine(models.Model):
    _inherit = 'hr.contract.type'
    nbr_heur_par_jour = fields.Float(string=("Nombre d'heures/jour"), default=8.0)


class hr_employee(models.Model):
    _inherit = 'hr.employee'


    last_ferm_pointage = fields.Many2one(comodel_name="res.company",
                                         string=_("Ferme de dernier pointage"), required=False, )

    last_date_pointage = fields.Datetime(string=_("Date de dernier pointage"), required=False, )
