# encoding: utf-8

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from odoo.exceptions import Warning
from odoo.exceptions import Warning as UserError
import logging
logger = logging.getLogger('l10n_ma_hr_payroll')

FIXED_DAYS = 'fixed_days'
FIXED_HOURS = 'fixed_hours'
WORKED_DAYS = 'worked_days'
WORKED_HOURS = 'worked_hours'
ATTENDED_DAYS = 'attended_days'
ATTENDED_HOURS = 'attended_hours'
TIMESHEET_DAYS = 'timesheet_days'
TIMESHEET_HOURS = 'timesheet_hours'


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    # Gestion de l'adresse
    city2 = fields.Char(string=u'Ville', size =  64 ,  )
    street = fields.Char(string=u'Rue', size =  64 ,  )
    street2 = fields.Char(string=u'Rue', size =  64 ,  )
    website = fields.Char(string=u'Site web', size =  64 ,  )
    zip = fields.Char(string=u'Code postal', size =  64 ,  )
    state_id = fields.Many2one('res.country.state', string=u'Province',  )

#     def onchange_address_id(self, cr, uid, ids, address, context=None):
#         # if address:
#         #     address = self.pool.get('res.partner').browse(cr, uid, address, context=context)
#         #     return {'value': {'work_phone': address.phone, 'mobile_phone': address.mobile}}
#         return {'value': {}}

    @api.multi
    def check_limits(self, date, amount, obj, test_date=True, test_amount=True):
        self.ensure_one()
        contract = self.env['hr.contract'].search(
            [('is_contract_valid_by_context', '=', date), ('employee_id', '=', self.id)], limit=1)
        company = contract and contract.company_id or self.company_id
        line = None
        if 'rubrique' in obj._table:
            line = self.env['hr.rubrique.limit'].search(
                [('company_id', '=', company.id), ('rubrique_id', '=', obj.rubrique_id.id)], limit=1)
        if 'avantage' in obj._table:
            line = self.env['hr.avantage.limit'].search(
                [('company_id', '=', company.id), ('avantage_id', '=', obj.avantage_id.id)], limit=1)
        if 'avance' in obj._table:
            line = self.env['hr.avance.limit'].search(
                [('company_id', '=', company.id), ('avance_id', '=', obj.avance_id.id)], limit=1)
        if line:
            if test_date:
                if int(date[8:10]) < line.day_from or int(date[8:10]) > line.day_to:
                    raise Warning(_('You should select a day between [%s] and [%s]') % (
                        line.day_from, line.day_to))
            if test_amount:
                if amount < line.amount_from or amount > line.amount_to:
                    raise Warning(_('You should pick an amount between [%s] and [%s]') % (
                        line.amount_from, line.amount_to))

    @api.multi
    def get_slips(self):
        ctx = self._context.copy()
        force_one = False
        exceptions = False
        domain = [('employee_id', 'in', self._ids)]
        if ctx.get('state', False):
            domain.append(('state', '=', ctx.get('state')),)
        if ctx.get('contract_id', False):
            contract_id = ctx.get('contract_id')
            if isinstance(contract_id, (int, long)):
                contract_id = [contract_id]
            domain.append(('contract_id', 'in', contract_id),)
        if ctx.get('date_from', False):
            domain.append(('date_to', '>=', ctx.get('date_from')),)
        if ctx.get('date_to', False):
            domain.append(('date_to', '<=', ctx.get('date_to')),)
        if ctx.get('force_one', False):
            force_one = True
        if ctx.get('exceptions', False):
            exceptions = True
        slips = self.env['hr.payslip'].search(domain)
        if force_one:
            if len(slips) == 1:
                return slips
            else:
                if exceptions:
                    raise Warning(_('L\'employé [%s] doit avoir un bulletin de paie pour chacun.') % [
                                  x.name for x in self])
        if exceptions:
            if not slips:
                raise Warning(_('L\'employe [%s] doit avoir des bulletins de paie.') % [
                              x.name for x in self])
        return self.env['hr.payslip'].search(domain)


    cimr_ok = fields.Boolean(string=u'CIMR', readonly=True,  related='current_contract_id.cimr_ok',  store=True)
    cnss_ok = fields.Boolean(string=u'CNSS', readonly=True,  related='current_contract_id.cnss_ok', store=True)
    assurance_ok = fields.Boolean(string=u'Assurance retraite', readonly=True, related='current_contract_id.assurance_ok', store=True )

    holiday_force_remove = fields.Boolean(string=u'Forcer la consommation des congés légaux', default=True )
    # CRON
    update_contract_state_update = fields.Date(
        string=u'Dernière mise à jour de l\'état des contrats', readonly=True, )
    last_remaining_leaves_update = fields.Date(
        string=u'Dernière mise à jour de rajout de nombre de jours pour les congés légaux', readonly=True, )
    last_remaining_leaves_addition = fields.Float(
        string=u'Dernière rajout', digits=dp.get_precision('Account'), readonly=True,)

    @api.model
    def update_holiday_allocation(self):
        employees = self.env['hr.employee'].search([]).filtered(lambda r: not r.last_remaining_leaves_update or r.last_remaining_leaves_update != fields.Date.today())
        logger.info('cron call update_holiday_allocation, number of employees is %s', len(employees))
        for employee in employees:
            if employee.current_contract_id:
                contract = employee.current_contract_id
                if contract.based_on not in [FIXED_DAYS, FIXED_HOURS, WORKED_DAYS, WORKED_HOURS]:
                    continue
                if contract.holiday_allocation_type not in ['contract', 'scale']:
                    continue
                if contract.holiday_allocation_type=='scale' or (contract.holiday_allocation_type=='contract' and contract.nb_holidays_by_month):
                    if contract.holiday_allocation_type=='scale':
                        addition = self.env['hr.scale.seniority'].get_seniority_leave(age=employee.seniority)
                    else:
                        addition = contract.nb_holidays_by_month
                    if contract.date_start_cron and fields.Date.today() >= contract.date_start_cron:
                        contract_day = contract.date_start_cron[
                            8:10]
                        today = fields.Date.today()[8:10]
                        last_day = datetime.today() + relativedelta(months=-1)
                        leave_prorata = self.env['ir.config_parameter'].get_param('leave_prorata','False') == 'True'
                        if leave_prorata:
                            if contract.based_on_days:
                                declared = contract.nbr_days_declared
                                worked = self.env['hr.dictionnary'].compute_value(
                                    code='NBR_JOURS',
                                    month_of_date=last_day,
                                    employee_id=employee.id,
                                )
                                if worked and declared:
                                    addition *= worked / declared
                            else:
                                declared = contract.nbr_hours_declared
                                worked = self.env['hr.dictionnary'].compute_value(
                                    code='NBR_HEURES',
                                    month_of_date=last_day,
                                    employee_id=employee.id,
                                )
                                if worked and declared:
                                    addition *= worked / declared
                        if contract_day in ['28', '29', '30', '31']:
                            if today == str(calendar.monthrange(int(fields.Date.today()[:4]), int(fields.Date.today()[5:7]))[1]):
                                employee.write( {
                                    'remaining_leaves':  employee.remaining_leaves + addition,
                                    'last_remaining_leaves_update':  fields.Date.today(),
                                    'last_remaining_leaves_addition':  addition,
                                })
                        elif today == contract_day:
                            employee.write( {
                                'remaining_leaves':  employee.remaining_leaves + addition,
                                'last_remaining_leaves_update':  fields.Date.today(),
                                'last_remaining_leaves_addition':  addition,
                            })

    nom = fields.Char(string=u'Nom', size=64, copy=False)
    prenom = fields.Char(string=u'Prénom', size=64, copy=False)

    @api.onchange('gender')
    def _onchange_gender(self) :
        MALE, FEMALE = 'male', 'female'
        if self.gender:
            title_ids = self.env['res.partner.title'].search([('gender','=',self.gender),('employee','=', True)]).mapped('id')
            if self.title not in title_ids :
                self.title = title_ids[0]


    @api.onchange('title')
    def _onchange_title(self) :
        MALE, FEMALE = 'male', 'female'
        title_gender = False
        if self.title:
            if self.title.gender == MALE  :
                title_gender = MALE
            if self.title.gender == FEMALE :
                title_gender = FEMALE
        if title_gender and self.gender != title_gender:
            self.gender = title_gender
    title = fields.Many2one('res.partner.title', string=u'Titre',  domain=[('employee','=',  True ) ])

    @api.one
    @api.depends('name','title')
    def _compute_full_name(self):
        full_name = self.name
        if self.title:
            full_name = self.title.shortcut + ' ' + full_name
        self.full_name = full_name

    full_name = fields.Char(string=u'Nom complet', size =  128 ,  compute='_compute_full_name', store=False,   )

    @api.multi
    def _update_vals(self, vals):
        partner = vals.get('address_home_id', False) and self.env['res.partner'].browse(
            vals.get('address_home_id', False)) or False
        company = False
        if vals.get('company_id', False):
            company = self.env['res.company'].browse(vals.get('company_id', False) )
        data = {
            'name': vals.get('name', False),
            'country_id': vals.get('country_id', False),
            'email': vals.get('work_email', False),
            'phone': vals.get('work_phone', False),
            'mobile': vals.get('mobile_phone', False),
            'company_id': vals.get('company_id', False),
            'parent_id':  company and company.partner_id.id or False,
            'city':  vals.get('city2', False),
            'street':  vals.get('street', False),
            'street2':  vals.get('street2', False),
            'zip':  vals.get('zip', False),
            'state_id':  vals.get('state_id', False),
            'website':  vals.get('website', False),
        }
        if not partner:
            data.update({
                'customer' : False,
                'supplier' : False,
                'employee' : True,
            })
            partner = self.env['res.partner'].create(data)
        else:
            partner.write(data)
        vals.update({
            'address_home_id': partner.id
        })
        return vals

    @api.model
    def create(self, vals):
        if not vals.get('otherid', False):
            company = self.env['res.company'].browse(
                vals.get('company_id', False))
            if not company:
                company = self.env.user.company_id
            if company and company.initial:
                employee = self.env['hr.employee'].with_context({'active_test': False, }).search(
                    [('otherid', 'like', company.initial)], limit=1, order='otherid desc')
                seq = company.initial + '1'.rjust(5, '0')
                if employee:
                    seq = company.initial + \
                        str(int(''.join(
                            [x for x in (employee.otherid or '0') if x.isdigit()]) or '0') + 1).rjust(5, '0')
            else:
                raise Warning('Veuillez configurer l\'initial de la société')
            vals.update({
                'otherid': seq,
            })
        if vals.get('name', False):
            name = vals.get('name').split(' ', 1)
            vals.update({
                'prenom': name and name[0] or '',
                'nom': len(name) > 1 and name[1] or '',
            })
        if vals.get('nom', False) or vals.get('prenom', False):
            nom, prenom = vals.get('nom'), vals.get('prenom')
            vals.update({
                'name': (prenom or '') + (nom and ' ' or '') + (nom or '')
            })
        vals = self._update_vals(vals)
        employee_id = super(hr_employee, self).create(vals)
        return employee_id

    @api.multi
    def write(self, vals):
        vals_tmp = vals.copy()
        for employee in self:
            data = employee.read(['address_home_id', 'nom', 'prenom', 'name',
                              'country_id', 'work_email', 'work_phone', 'mobile_phone', 'company_id',
                              'street', 'street2', 'city2', 'zip', 'state_id', 'website'])[0]
            for k, v in data.iteritems():
                data[k] = isinstance(v, tuple) and v[0] or v
            data.update(vals)
            data.update({
                'email': data.get('work_email', ''),
                'phone': data.get('work_phone', ''),
                'mobile': data.get('mobile_phone', ''),
                'company_id': data.get('company_id', False),
            })
            vals = data.copy()
            if ('otherid' in vals_tmp.keys() and not vals_tmp.get('otherid', False) ) or \
                (vals_tmp.get('company_id', False) and
                 not vals_tmp.get('otherid', False)) or not employee.otherid:
                company = self.env['res.company'].browse(
                    vals.get('company_id', False))
                seq = False
                if company and company.initial:
                    if not employee.otherid or (employee.otherid and not employee.otherid.startswith(company.initial)):
                        employee = self.env['hr.employee'].with_context({'active_test': False, }).search([
                            ('otherid', 'like', company.initial),
                            ('id', '!=', employee.id),
                        ], limit=1, order='otherid desc')
                        seq = company.initial + '1'.rjust(5, '0')
                        if employee:
                            seq = company.initial + \
                                str(int(''.join(
                                    [x for x in (employee.otherid or '0') if x.isdigit()]) or '0') + 1).rjust(5, '0')
                if seq:
                    vals.update({
                        'otherid': seq,
                    })
            if vals.get('nom', False) or vals.get('prenom', False):
                nom, prenom = vals.get('nom'), vals.get('prenom')
                vals.update({
                    'name': (prenom or '') + (nom and ' ' or '') + (nom or '')
                })
            if vals.get('name', False):
                name = vals.get('name').split(' ', 1)
                vals.update({
                    'prenom': name and name[0] or '',
                    'nom': len(name) > 1 and name[1] or '',
                })
            vals = employee._update_vals(vals)
            del vals['phone']
            del vals['email']
            del vals['mobile']
        res = super(hr_employee, self).write(vals)
        return res

    children_ids = fields.One2many(
        'hr.employee.children', 'employee_id', string=u'Enfants',)
    current_contract_id = fields.Many2one(
        'hr.contract', string=u'Contrat courant',)
    first_contract_id = fields.Many2one(
        'hr.contract', string=u'Premier contrat',)
    is_contract_valid = fields.Boolean(
        string=u'Contrat valide',
        related='current_contract_id.is_contract_valid',  store=True)

    working_hours = fields.Many2one(
        'resource.calendar',
        string=u'Temps de travail',
        related='current_contract_id.working_hours',  store=True)

    cnss = fields.Char(string=u'Immatriculation CNSS', size=64,)

#     @api.one
#     @api.constrains('cnss')
#     def _check_cnss(self):
#         if self.cnss:
#             res, msg = self.check_cnss_conformite()
#             if not res :
#                 raise UserError(msg)

    @api.multi
    def check_cnss_conformite(self):
        if not self.cnss :
            return False, _('Veuillez spécifier le numéro d\'immatriculation')
        if self.cnss in ['0'*9, '9'*9]:
            return True, ''
        if self.search_count([('cnss','=', self.cnss)]) > 1 :
            return False, _('CNSS already exist')
        cnss = self.cnss
        if len(cnss) != 9 :
            return False, _('CNSS erroné, nombre de chiffres différent de 9')
        if not cnss.isdigit():
            return False, _('CNSS erroné, l\'immatriculation n\'est pas un nombre')
        C = lambda r: int(cnss[r-1])
        deuxchiffres = (C(2)+C(4)+C(6)+C(8))*2+C(3)+C(5)+C(7)
        C9 = int(str(deuxchiffres)[-1])
        if C9==0 :
            print "FOUND 0 then C(0) should be 0 : ", C(0)
            if C(0) !=0 :
                return False, _('CNSS erroné')
        else:
            print "FOUND %s then 10-%s should be %s" % (C9, C9, C(0))
            if 10 - C9 != C(0) :
                return False, _('CNSS erroné')
        return True, ''

    cimr = fields.Char(string=u'Immatriculation CIMR', size=64,)
    cimr_date = fields.Date(string=u'Date affiliation CIMR',  )
    cimr_category = fields.Integer(string=u'Catégorie CIMR' )
    cin = fields.Char(string=u'CIN', size=64,)
    identification_id = fields.Char(string=u'Identifiant fiscal', size=64, )
    mutuelle = fields.Char(string=u'Immatriculation Mutuelle', size=64,)
    qualif_id = fields.Many2one(
        'hr.employee.qualification', string=u'Qualification',)
    task_id = fields.Many2one('hr.employee.task', string=u'Tâche',)

    @api.one
    @api.depends("children_ids", "marital", "wife_situation")
    def _compute_charged_person(self):
        nbr_person_charged = 0
        nbr_children_charged = 0
        nbr_children_af = 0
        children = 0
        if self.marital != 'C':
            children = len(self.children_ids)
            for line in self.children_ids:
                if line.a_charge:
                    nbr_person_charged += 1
                    nbr_children_charged += 1
                if line.af:
                    nbr_children_af += 1
            if self.marital == 'M':
                if self.wife_situation != 'A':
                    nbr_person_charged += 1
        self.children = children
        self.nbr_person_charged = nbr_person_charged
        self.nbr_children_charged = nbr_children_charged
        self.nbr_children_af = nbr_children_af

    nbr_person_charged = fields.Integer(
        string=u'Nombre de personne à charge', required=True, default=0, compute='_compute_charged_person', store=True)
    nbr_children_charged = fields.Integer(
        string=u'Nombre d\'enfants à charge', required=True, default=0, compute='_compute_charged_person', store=True)
    nbr_children_af = fields.Integer(
        string=u'Nombre d\'enfants pour allocation familiale', required=True, default=0, compute='_compute_charged_person', store=True)
    children = fields.Integer(compute='_compute_charged_person', store=True)
    hire_date = fields.Date(
        string=u'Date d\'embauche', readonly=True, )

    marital = fields.Selection([
        ('C', 'Célibataire'),
        ('M', 'Marié(e)'),
        ('V', 'Veuf(ve)'),
        ('D', 'Divorcé(e)')
    ])

    @api.onchange('marital','gender')
    def _onchange_marital(self) :
        if self.marital == 'M' and self.gender == 'male':
            self.wife_situation = 'N'
        elif  self.marital == 'M' and self.gender == 'female':
            self.wife_situation = 'A'
        else :
            self.wife_situation = 'N'

    wife_situation = fields.Selection([
        ('A', 'Affilié(e)'),
        ('W', 'Travaille'),
        ('N', 'Aucun'),
    ], string=u'Situation du partenaire', default='N',)

    @api.one
    @api.depends("hire_date")
    def _compute_seniority(self):
        seniority_end = fields.Datetime.from_string(self.env.context.get('seniority_end', fields.Date.today()))
        if self.hire_date:
            self.seniority = ((seniority_end.year - fields.Datetime.from_string(
                self.hire_date).year) * 12 + seniority_end.month - fields.Datetime.from_string(
                    self.hire_date).month) / 12.
        else:
            self.seniority = 0

    seniority = fields.Float(
        string=u'Ancienneté', digits=dp.get_precision('Seniority'), help='Ancienneté en années', compute='_compute_seniority', store=False  )

    otherid = fields.Char(string=u'Matricule', copy=False)

    carte_sejour = fields.Char(string=u'Carte séjour', size=64,)

    date_ac = fields.Date(string=u'Date d\'autorisation de construire',)
    date_ph = fields.Date(string=u'Date de permis d\'habiter',)
    ppr = fields.Char(string=u'PPR', size=64,)

    poids = fields.Float(string=u'Poids', digits=dp.get_precision('Account'),)
    taille = fields.Float(string=u'Taille', digits=dp.get_precision('Account'),)


    distance_home = fields.Integer(string=u'Distance avec l\'emplacement d\'affectation',  )
    habitation_type = fields.Selection([
        ('urban', 'Urbain'),
        ('rural', 'Rural'),
    ], string=u'Habitation',  )
    # Attendance

    @api.one
    def _compute_attendance_vars(self):
        attendance = self.env['hr.attendance'].search(
            [('employee_id', '=', self.id)], order='name desc', limit=1)

        if attendance:
            self.gap = attendance.gap
            self.action_state = attendance.action_state
        else:
            self.gap = 0
            self.action_state = 'normal'

    gap = fields.Float(
        string=u'GAP',
        digits=dp.get_precision('Account'),
        default=0,
        compute='_compute_attendance_vars',)
    action_state = fields.Selection([
        ('in_late', 'Entrée en retard'),
        ('out_late', 'Sortie en retard'),
        ('in_early', 'Entrée tôt'),
        ('out_early', 'Sortie tôt'),
        ('normal', 'Normal'),
    ], string=u'Type d\'action',
        default='normal',
        compute='_compute_attendance_vars',)

    drive_ids = fields.Many2many(
        'hr.employee.drive.type', string=u'Permis de conduire',)
    formation_ids = fields.One2many(
        'hr.employee.formation', 'employee_id', string=u'Formation',)

    saisie_line_count = fields.Integer(
        string=u'Lignes de saisie', compute='_compute_saisie_line_count',)

    @api.one
    def _compute_saisie_line_count(self):
        self.saisie_line_count = self.sudo().env['hr.saisie.line'].search_count(
            [('employee_id', '=', self.id)])

    km_count = fields.Char(
        string=u'Kilométrage', size=128, compute='_compute_km_count',)

    @api.one
    def _compute_km_count(self):
        items = self.sudo().env['hr.employee.km'].search(
            [('employee_id', '=', self.id)]).mapped('value')
        nbr = len(items)
        total = sum(items)
        self.km_count = ' '.join([str(total),'km','('+str(nbr)+')'])

    mission_count = fields.Integer(
        string=u'Missions', compute='_compute_mission_count',)

    @api.one
    def _compute_mission_count(self):
        self.mission_count = self.sudo().env['hr.employee.mission'].search_count(
            [('employee_id', '=', self.id)])

    document_count = fields.Integer(
        string=u'Documents', compute='_compute_document_count',)

    @api.one
    def _compute_document_count(self):
        self.document_count = self.sudo().env['hr.document'].search_count(
            [('employee_id', '=', self.id)])

    warning_count = fields.Integer(
        string=u'Avertissements', compute='_compute_warning_count',)

    @api.one
    def _compute_warning_count(self):
        self.warning_count = self.sudo().env['hr.employee.warning'].search_count(
            [('employee_id', '=', self.id)])

    attendance_count = fields.Integer(
        string=u'Pointage en masse', compute='_compute_attendance_count',)

    @api.one
    def _compute_attendance_count(self):
        self.attendance_count = self.sudo().env['hr.employee.mass.attendance'].search_count(
            [('employee_id', '=', self.id)])

    avantage_count = fields.Integer(
        string=u'Avantages', compute='_compute_avantage_count',)

    @api.one
    def _compute_avantage_count(self):
        self.avantage_count = self.sudo().env['hr.avantage.line'].search_count(
            [('employee_id', '=', self.id)])

    expense_count = fields.Integer(
        string=u'Notes de frais', compute='_compute_expense_count',)

    @api.one
    def _compute_expense_count(self):
        self.expense_count = self.sudo().env['hr.expense'].search_count(
            [('employee_id', '=', self.id)])

    avance_count = fields.Integer(
        string=u'Avances/Cessions', compute='_compute_avance_count',)

    @api.one
    def _compute_avance_count(self):
        self.avance_count = self.sudo().env['hr.avance.line'].search_count(
            [('employee_id', '=', self.id)])

    rubrique_count = fields.Integer(
        string=u'Éléments de salaire', compute='_compute_rubrique_count',)

    @api.one
    def _compute_rubrique_count(self):
        self.rubrique_count = self.sudo().env['hr.rubrique.line'].search_count(
            [('employee_id', '=', self.id)])

    # Searching contract validity by context

    def _search_valid_contracts_by_context(self, operator, value):
        contracts = self.env['hr.contract'].search(
            [('is_contract_valid_by_context', operator, value)])
        ids = contracts.mapped('employee_id.id')
        return [('id', 'in', ids)]

    @api.one
    def _compute_valid_contracts_by_context(self):
        self.is_contract_valid_by_context = False

    is_contract_valid_by_context = fields.Boolean(
        string=u'Contrat valide',
        search='_search_valid_contracts_by_context',
        compute='_compute_valid_contracts_by_context',
    )

    # Searching category
    def _search_category_ref(self, operator, value):
        try:
            categ_id = self.env.ref('l10n_ma_hr_payroll.'+value).id
        except:
            return [('id','in', [])]
        return [('category_ids', 'in', [categ_id])]

    @api.multi
    def _compute_category_ref(self):
        for obj in self:
            obj.category_ref = False

    category_ref = fields.Boolean(search='_search_category_ref', compute='_compute_category_ref' )
    attendance_id = fields.Char(string=u'Pointage ID', size=64,)

    # CRON
    @api.model
    def attendance_action_signoutall(self):
        employees = self.search([]).filtered(lambda r: r.attendance_state == 'present')
        employees.attendance_action_change()

    # ROTATION

    rotation_ids = fields.One2many('hr.employee.rotation', 'employee_id', string=u'Rotation',  )

    @api.one
    def update_rotation(self):
        self.rotation_ids.unlink()
        contracts = self.env['hr.contract'].search([('employee_id','=',self.id)], order='date_start asc')
        companies = contracts.mapped('company_id')
        data = dict.fromkeys(contracts.mapped('company_id'),[])
        for contract in contracts:
            data[contract.company_id].append(contract)
        for company, contracts in data.iteritems():
            for contract in contracts:
                if contract.trial_date_start :
                    self.rotation_ids.create({
                        'company_id' : contract.company_id.id,
                        'employee_id' : self.id,
                        'date' : contract.trial_date_start,
                        'action' : 'trial_start',
                    })
                if contract.trial_date_end :
                    self.rotation_ids.create({
                        'company_id' : contract.company_id.id,
                        'employee_id' : self.id,
                        'date' : contract.trial_date_end,
                        'action' : 'trial_end',
                    })
                if contract.date_start and not contract.previous_id:
                    self.rotation_ids.create({
                        'company_id' : contract.company_id.id,
                        'employee_id' : self.id,
                        'date' : contract.date_start,
                        'action' : 'start',
                    })
                if contract.date_end and not contract.next_id:
                    self.rotation_ids.create({
                        'company_id' : contract.company_id.id,
                        'employee_id' : self.id,
                        'date' : contract.date_end,
                        'action' : 'end',
                    })

class hr_employee_children(models.Model):
    _name = 'hr.employee.children'
    _description = 'Enfants'
    _order = 'birthday desc'

    name = fields.Char(string=u'Nom', size=64, required=False)
    a_charge = fields.Boolean(string=u'À charge', default=False)
    af = fields.Boolean(string=u'Allocation familiale', default=False)
    sexe = fields.Selection([('m', 'Garçon'), ('f', 'Fille')], string=u'Sexe',)
    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé', required=False, ondelete='cascade',  )
    birthday = fields.Date(string=u'Date de naissance',)

    @api.one
    @api.depends("birthday")
    def _compute_age(self):
        if not self.birthday:
            self.age = False
        else:
            today = fields.Datetime.from_string(fields.Date.today())
            birthday = fields.Datetime.from_string(self.birthday)
            self.age = today.year - birthday.year - \
                ((today.month, today.day) < (birthday.month, birthday.day))

    age = fields.Integer(string=u'Age',  compute='_compute_age',)


class hr_employee_formation(models.Model):
    _name = 'hr.employee.formation'
    _order = 'date_from asc'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string=u'Employé', required=False, ondelete='cascade',  )
    date_from = fields.Date(string=u'Date début',)
    date_to = fields.Date(string=u'Date fin',)
    school = fields.Char(string=u'Établissment', size=64,)
    formation = fields.Char(string=u'Formation', size=64,)
    diplome = fields.Char(string=u'Diplôme', size=64,)


class drive(models.Model):
    _name = 'hr.employee.drive.type'
    _order = 'name asc'

    name = fields.Char(string=u'Nom', size=64,)
