# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError as Warning
import base64
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


import calendar
from .damancom_constants import *

NON_RENSEIGNE = SPACE

import logging
logger = logging.getLogger('damancom_construct')

class hr_teledeclaration_damancom(models.TransientModel):
    _name = 'hr.teledeclaration.damancom'

    declaration_type = fields.Selection([
        ('p', 'Principale'),
        ('c', 'Complémentaire'),
    ], string=u'Type',  required=True, default='p',)

    declaration_number = fields.Integer(
        string=u'Numéro du complément', default=1)

    company_child = fields.Boolean(string=u'Filiales', default=True,)
    company_parent = fields.Boolean(string=u'Sociétés mères', default=True,)

    @api.onchange('company_child', 'company_parent')
    def _onchange_company_child_parent(self):
        ids = []
        if self.company_child:
            companies = self.env['res.company'].search(
                [('parent_id', '!=', False)])
            if companies:
                ids += companies.mapped('id')
        if self.company_parent:
            companies = self.env['res.company'].search(
                [('parent_id', '=', False)])
            if companies:
                ids += companies.mapped('id')
        self.company_ids = self.env['res.company'].browse(ids)

    @api.depends('fichier_preetabli')
    def _init_period(self):
        for obj in self:
            if obj.fichier_preetabli:
                fd = StringIO(base64.decodestring(obj.fichier_preetabli))
                line = False
                for val in fd.readlines():
                    if val[:3] == A01:
                        line = val
                        break
                if not line:
                    raise Warning(_('Format du fichier est inalide'))
                else:
                    year, month = get_a01(line).get(
                        'L_Periode')[:4], get_a01(line).get('L_Periode')[4:6]
                    interval = calendar.monthrange(int(year), int(month))
                    date_start = year + '-' + month + '-01'
                    date_stop = year + '-' + month + '-' + \
                        str(interval[1]).rjust(2, '0')
                    fiscalyear_id = self.env[
                        'date.range'].search([('date_start', '=', date_start)])
                    period_start = self.env['date.range'].search([('date_start', '=', date_start)])
                    period_stop = self.env['date.range'].search([('date_start', '=', date_stop)])
                    period = period_start == period_stop and period_start or False
                    obj.date_from = date_start
                    obj.date_to = date_stop
                    obj.fiscalyear_id = fiscalyear_id
                    obj.period_id = period

            else:
                obj.fiscalyear_id = False
                obj.period_id = False
                obj.date_from = False
                obj.date_to = False
            

    company_ids = fields.Many2many(
        'res.company', string=u'Sociétés',  required=True, )
    fiscalyear_id = fields.Many2one(
        'date.range', string=u'Année', required=False, compute='_init_period', store=True)
    period_id = fields.Many2one(
        'date.range', string=u'Période', required=False, compute='_init_period', store=True)
    date_from = fields.Date(
        string=u'Date début',  required=False, compute='_init_period', store=True)
    date_to = fields.Date(
        string=u'Date fin',  required=False, compute='_init_period', store=True)

    departments_id = fields.Many2many(
        'hr.department', 'teledeclaration_damancom_department_rel', 'declaration_id', 'department_id', string=u'Limiter les départements', )

    state = fields.Selection([
        ('all', 'Tous'),
        ('done', 'Terminé'),
    ], string=u'État', required=True, default='done')

    name = fields.Char(string=u'Nom', size=64,)
    fichier_preetabli = fields.Binary(
        string=u'Fichier préétabli', filters='*.txt', required=True)
    generated_file = fields.Binary(string=u'Fichier généré',)

    entrant_ids = fields.Many2many(
        'hr.employee', 'damancom_entrant_rel', 'damancom_id', 'entrant_id', string=u'Entrants', context={'active_test': False, })
    courant_ids = fields.Many2many(
        'hr.employee', 'damancom_courant_rel', 'damancom_id', 'courant_id', string=u'Courants', context={'active_test': False, })
    sortant_ids = fields.Many2many(
        'hr.employee', 'damancom_sortant_rel', 'damancom_id', 'sortant_id', string=u'Sortants', context={'active_test': False, })

    erreur_ids = fields.Many2many(
        'hr.employee.temp', 'damancom_erreur_rel', 'damancom_id', 'erreur_id', string=u'Introuvables',)

    @api.one
    @api.depends('sortant_ids', 'courant_ids', 'entrant_ids', 'erreur_ids')
    def _compute_summary(self):
        e = len(self.entrant_ids)
        c = len(self.courant_ids)
        s = len(self.sortant_ids)
        r = len(self.erreur_ids)
        data = _(
            "<b>Entrants : %s.<br />Sortants : %s.<br />Courants : %s.</b><br />") % (e, s, c,)
        if r:
            data += "<b style=\"color: red;\">Erreurs : %s.</b>" % r
        else:
            data += "<b>Erreurs : %s.</b>" % r
        self.summary = data

    summary = fields.Html(string=u'Synthèse', compute='_compute_summary',)

    @api.multi
    def goto_first(self):
        action = self.env.ref(
            'l10n_ma_hr_payroll.view_hr_teledeclaration_damancom_form_first')
        return {
            'name': _('DAMANCOM'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.teledeclaration.damancom',
            'view_id': action.read()[0].get('id'),
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.multi
    def goto_intermediate(self):
        self.process_intermediate()
        action = self.env.ref(
            'l10n_ma_hr_payroll.view_hr_teledeclaration_damancom_form_intermediate')
        return {
            'name': _('DAMANCOM'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.teledeclaration.damancom',
            'view_id': action.read()[0].get('id'),
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.multi
    def goto_last(self):
        self.process_last()
        action = self.env.ref(
            'l10n_ma_hr_payroll.view_hr_teledeclaration_damancom_form_last')
        return {
            'name': _('DAMANCOM'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.teledeclaration.damancom',
            'view_id': action.read()[0].get('id'),
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.multi
    def get_as(self):
        fd = StringIO(base64.decodestring(self.fichier_preetabli))
        a00 = a01 = a03 = None
        a02 = []
        try:
            lines = fd.readlines()
            for line in lines:
                if line[0:3] == 'A00':
                    a00 = get_a00(line)
                if line[0:3] == 'A01':
                    a01 = get_a01(line)
                if line[0:3] == 'A02':
                    a02.append(get_a02(line))
                if line[0:3] == 'A03':
                    a03 = get_a03(line)
        except:
            raise Warning(_('Format de fichier non conforme'))
        return {
            A00: a00,
            A01: a01,
            A02: a02,
            A03: a03,
        }

    @api.multi
    def get_assure(self, number):
        for item in self.get_as().get(A02):
            if item.get('N_Num_Assure') == number:
                return {
                    'nom': item.get('L_Nom_Prenom')[:30].strip().title(),
                    'prenom': item.get('L_Nom_Prenom')[30:].strip().title(),
                }
        return {
            'nom': _('Unknow'),
            'prenom': _('Unknow'),
        }

    @api.multi
    def get_entrants_cnss(self):
        return [x.cnss for x in self.entrant_ids]

    @api.multi
    def get_sortants_cnss(self):
        return [x.cnss for x in self.sortant_ids]

    @api.multi
    def get_courants_cnss(self):
        return [x.cnss for x in self.courant_ids]

    @api.multi
    def process_intermediate(self):
        company = self.company_ids[0].main_company_id
        if not company.cnss:
            raise Warning(
                _('Please define the CNSS Number on the company'))
        pre = self.declaration_type == 'p' and 'DS_' or (
            'DSC' + str(self.declaration_number) + '_')
        company_cnss = company.cnss and company.cnss.strip() or ''
        company_cnss = company_cnss.replace(' ','').replace('_','')
        self.name = pre + company_cnss + '_' + \
            self.date_to[0:4] + self.date_from[5:7] + '.txt'
        self.data_analyse()

    @api.multi
    def check_intermediate(self):
        ids_1 = list(set(self.entrant_ids.mapped('id')) & set(
            self.sortant_ids.mapped('id')))
        ids_2 = list(
            set(self.entrant_ids.mapped('id')) & set(self.courant_ids.mapped('id')))
        ids_3 = list(set(
            self.sortant_ids.mapped('id')) & set(self.courant_ids.mapped('id')))
        ids = list(set(ids_1 + ids_2 + ids_3))
        if len(self.erreur_ids) > 0:
            employees = ''
            for error_temp in self.erreur_ids:
                employees += ' ' + error_temp.name + '\n'
            raise Warning(
                _('Employees to be created on the system : \n%s' % employees))
        if len(ids) > 0:
            raise Warning(_('Les employees : \n%s\nDoivent etre soient entrants, sortants ou courants' %
                            '\n'.join(['* ' + x.prenom + ' ' + x.nom for x in self.env['hr.employee'].browse(ids)])))
        ctx = {'date': self.date_to, 'default': SPACE}
        for sortant in self.sortant_ids:
            situation = sortant.with_context(ctx).get_situation()
            if not situation or situation != 'SO':
                raise Warning(_('The situation of the employee [%s] should be <Sortant> at [%s]') % (
                    sortant.name, self.date_to))

        for emp in self.courant_ids + self.entrant_ids:
            situation = emp.with_context(ctx).get_situation()
            if not situation:
                raise Warning(
                    _('Please specify a situation for the employee [%s] at [%s]') % (emp.name, self.date_to))
        return True

    @api.multi
    def process_last(self):
        self = self.with_context({'active_test': False, })
        self.check_intermediate()
        output = StringIO()
        output.write(self.construct_b00() + '\n')
        output.write(self.construct_b01() + '\n')
        b02 = self.construct_b02()
        for line in b02:
            output.write(line + '\n')
        b03 = self.construct_b03(b02=b02)
        output.write(b03 + '\n')
        b04 = self.construct_b04()
        for line in b04:
            output.write(line + '\n')
        b05 = self.construct_b05(b04=b04)
        output.write(b05 + '\n')
        b06 = self.construct_b06(b03=get_b03(b03), b05=get_b05(b05))
        output.write(b06 + '\n')
        contents = output.getvalue()
        output.close()
        generated_data = base64.encodestring(contents)
        self.generated_file = generated_data

    @api.multi
    def update_data(self):
        company = self.company_ids[0].main_company_id
        ass = self.get_as()
        data = ass.get(A01)
        a02 = ass.get(A02)
        company_data = {
            'cnss': data.get('N_Num_Affilie').strip(),
            'zip': data.get('C_Code_Postal').strip(),
            'city': data.get('L_Ville').strip().title(),
            'street': data.get('L_Adresse').strip().title(),
        }
        if data.get('L_Activite'):
            company_data['activity'] = data.get(
                'L_Activite').strip().title()
        company.write(company_data)
        for line in a02:
            cnss = line.get('N_Num_Assure', False)
            if cnss:
                employee = self.env['hr.employee'].search(
                    [('cnss', '=', cnss)], limit=1)
                if not employee:
                    employee.create({
                        'nom': line.get('L_Nom_Prenom')[:30].strip().title(),
                        'prenom': line.get('L_Nom_Prenom')[30:].strip().title(),
                        'nbr_person_charged': int(line.get('N_Enfants', '0')),
                        'cnss': cnss,
                    })
        return self.goto_first()

    @api.multi
    def get_departments(self):
        if not self.departments_id:
            return False
        department_ids = [x.id for x in self.departments_id]
        department_ids = self.env['hr.department'].search(
            [('id', 'child_of', department_ids)]).mapped('id')
        return department_ids

    @api.multi
    def get_state(self):
        return self.state

    @api.multi
    def data_analyse(self):
        domain = [
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('company_id', 'in', self.company_ids.mapped('id')),
            ('salary_net', '>', 0),
            ('contract_id.cnss_ok', '=', True),
        ]
        department_ids = self.get_departments()
        if department_ids:
            domain.append(('department_id', 'in', department_ids),)
        if self.state != 'all':
            domain.append(('state', '=', self.state),)
        payslips = self.env['hr.payslip'].search(domain)
        payslips_courant_entrant_employee_ids = payslips.mapped('employee_id.id')
        a02 = self.get_as().get(A02)
        # List Num_Affiliation FROM System
        TAB_IN_FROM_SYSTEM = sorted(payslips.mapped('employee_id.cnss'))
        TAB_IN_FROM_FILE = sorted([x.get('N_Num_Assure').strip()
                                   for x in a02])
        NON_TROUVES = []
        all_employee_cnss = self.env['hr.employee'].with_context(
            {'active_test': False}).search([]).mapped('cnss')
        SORTANTS = list(set(TAB_IN_FROM_FILE) - set(TAB_IN_FROM_SYSTEM)) #OK
        COURANTS = list(set(TAB_IN_FROM_FILE) & set(TAB_IN_FROM_SYSTEM)) #OK
        ENTRANTS = list(set(TAB_IN_FROM_SYSTEM) - set(TAB_IN_FROM_FILE)) #OK mais ca va contenir les '000' et ''
        CNSS_NON_TROUVES = list(set(TAB_IN_FROM_FILE) - set(all_employee_cnss)) #OK
        # # CREATE A TEMP EMPLOYEES
        employee_temp_obj = self.env['hr.employee.temp']
        employee_temp_obj.search([]).unlink()
        for nt in CNSS_NON_TROUVES:
            assuree = self.get_assure(nt)
            nom = nt + ' - ' + \
                assuree.get('nom', '') + ' ' + assuree.get('prenom', '')
            temp_id = self.env['hr.employee.temp'].create({'name': nom},)
            NON_TROUVES.append(temp_id.id)
        # #######
        sortant_ids = self.env['hr.employee'].with_context(
            {'active_test': False}).search([('cnss', 'in', SORTANTS)]).mapped('id')
        courant_ids = self.env['hr.employee'].with_context(
            {'active_test': False}).search([('cnss', 'in', COURANTS)]).mapped('id')
        entrant_ids = self.env['hr.employee'].with_context(
            {'active_test': False}).search([('cnss', 'in', ENTRANTS),('id','in',payslips_courant_entrant_employee_ids)]).mapped('id')
        a_traiter_ids = sortant_ids + courant_ids + entrant_ids
        # ########
        vals = {
            'entrant_ids': [(6, 0, entrant_ids)],
            'sortant_ids': [(6, 0, sortant_ids)],
            'courant_ids': [(6, 0, courant_ids)],
            'erreur_ids': [(6, 0, NON_TROUVES)],
        }
        self.write(vals)
        return True

    def construct_b00(self):
        L_filler = SPACE.rjust(B00_L_filler, SPACE)
        L_Cat = 'B0'.rjust(B00_L_Cat, SPACE)
        N_Identif_Transfert = self.get_as().get(A00).get(
            'N_Identif_Transfert').rjust(B00_N_Identif_Transfert, SPACE)
        L_Type_Enreg = 'B00'
        line_b00 = None
        if not L_filler or not L_Cat or not N_Identif_Transfert or not L_Type_Enreg:
            raise Warning(_('Erreur lors de la construction de [B00]'))
        line_b00 = set_b00(
            L_Type_Enreg=L_Type_Enreg, N_Identif_Transfert=N_Identif_Transfert, L_Cat=L_Cat, L_filler=L_filler)
        if line_b00 and len(line_b00) == LINE_MAX:
            return line_b00
        else:
            raise Warning(_('Erreur lors de la construction de [B00]'))

    @api.multi
    def construct_b01(self):
        logger.info('Construct B01')
        a01 = self.get_as().get(A01)
        N_Num_Affilie = a01.get('N_Num_Affilie').rjust(
            B01_N_Num_Affilie, SPACE)
        L_Raison_Sociale = a01.get('L_Raison_Sociale').rjust(
            B01_L_Raison_Sociale, SPACE)
        L_Ville = a01.get('L_Ville').rjust(B01_L_Ville, SPACE)
        L_Adresse = a01.get('L_Adresse').rjust(B01_L_Adresse, SPACE)
        C_Code_Postal = a01.get('C_Code_Postal').rjust(
            B01_C_Code_Postal, SPACE)
        L_Activite = a01.get('L_Activite').rjust(B01_L_Activite, SPACE)
        L_Periode = a01.get('L_Periode').rjust(B01_L_Periode, SPACE)
        L_Type_Enreg = 'B01'.rjust(B01_L_Type_Enreg, SPACE)
        C_Code_Agence = a01.get('C_Code_Agence').rjust(
            B01_C_Code_Agence, SPACE)
        D_Date_Emission = a01.get('D_Date_Emission').rjust(
            B01_D_Date_Emission, SPACE)
        D_Date_Exig = a01.get('D_Date_Exig').rjust(B01_D_Date_Exig, SPACE)
        if not N_Num_Affilie or not L_Raison_Sociale or not L_Ville or not L_Adresse or not C_Code_Postal:
            raise Warning(_('Erreur lors de la construction de [B01]'))
        line_b01 = None
        line_b01 = set_b01(L_Type_Enreg=L_Type_Enreg, N_Num_Affilie=N_Num_Affilie, L_Periode=L_Periode, L_Raison_Sociale=L_Raison_Sociale, L_Activite=L_Activite,
                           L_Adresse=L_Adresse, L_Ville=L_Ville, C_Code_Postal=C_Code_Postal, C_Code_Agence=C_Code_Agence, D_Date_Emission=D_Date_Emission, D_Date_Exig=D_Date_Exig)
        if line_b01 and len(line_b01) == LINE_MAX:
            return line_b01
        else:
            raise Warning(_('Erreur lors de la construction de [B01]'))

    @api.multi
    def construct_b02(self):
        tab_b02 = []
        ass = self.get_as()
        a01 = ass.get(A01)
        a02 = ass.get(A02)
        employees = self.courant_ids + self.sortant_ids
        employees = employees.sorted(key=lambda r: r.cnss)
        compute_value = self.env['hr.dictionnary'].compute_value
        courants_cnss = self.get_courants_cnss()
        sortants_cnss = self.get_sortants_cnss()
        logger.info('Construct B02, Total : %s', len(a02))
        count = 0
        for assuree in a02:
            count += 1
            N_Num_Affilie = assuree.get('N_Num_Affilie').rjust(
                B02_N_Num_Affilie, SPACE)
            N_Num_Assure = assuree.get('N_Num_Assure').rjust(
                B02_N_Num_Assure, SPACE)
            employee_name = ' '.join([self.get_assure(N_Num_Assure).get(
                'prenom'), self.get_assure(N_Num_Assure).get('nom')])
            employee = self.env['hr.employee'].search(
                [('cnss', '=', assuree.get('N_Num_Assure'))])
            logger.info('Construct B02, Item : %s/%s, Employe : %s', count, len(a02), employee_name)
            if len(employee) > 1:
                raise Warning(
                    _('Employés [%s] ont la même immatriculation  CNSS [%s]') % (', '.join([x.name for x in employee]), N_Num_Assure,))
            if not employee:
                raise Warning(
                    _('Employee [%s] with CNSS [%s] not found in the system') % (employee_name, N_Num_Assure,))
            emp_ctx = employee.with_context(
                {'date': self.date_to, 'date_from': self.date_from, 'date_to': self.date_to, 'default': SPACE})
            situation = emp_ctx.get_situation().strip().upper()
            L_Type_Enreg = 'B02'.rjust(B02_L_Type_Enreg, SPACE)
            L_Periode = a01.get('L_Periode').rjust(B02_L_Periode, SPACE)
            L_filler = SPACE.rjust(B02_L_filler, SPACE)
            if N_Num_Assure not in (courants_cnss + sortants_cnss):
                raise Warning(
                    _('Employé [%s] avec CNSS [%s] doit etre Courant ou sortant') % (employee_name, N_Num_Assure,))
            nb_jours_declares = situation in ['SO', 'CS', 'MS'] and 0 or int(compute_value(
                code='NBR_JOURS',
                date_start=self.date_from,
                date_stop=self.date_to,
                employee_id=employee.id,
                department_ids=self.get_departments(),
                state=self.get_state(),
            ))
            nb_jours_declares = nb_jours_declares >= 26 and 26 or nb_jours_declares
            N_Jours_Declares = str(int(nb_jours_declares)).rjust(
                B02_N_Jours_Declares, ZERO)
            if N_Num_Assure in sortants_cnss and situation != 'SO':
                raise Warning(
                    _('Specifiez la situation de l\'employé [%s] comme sortant' % employee_name))
            situation = situation=='NON_RENSEIGNE' and '  ' or situation
            L_Situation = situation.rjust(B02_L_Situation, SPACE)
            situation_value = get_situation_code(L_Situation)
            allocation_familiale = int(compute_value(
                code='ALLOCATION_FAMILIALE',
                date_start=self.date_from,
                date_stop=self.date_to,
                employee_id=employee.id,
                department_ids=self.get_departments(),
                state=self.get_state(),
            ) * 100)
            N_AF_A_Payer = assuree.get('N_AF_A_Payer').rjust(
                B02_N_AF_A_Payer, ZERO)
            N_AF_A_Deduire = assuree.get('N_AF_A_Deduire').rjust(
                B02_N_AF_A_Deduire, ZERO)
            N_AF_Net_A_Payer = assuree.get('N_AF_Net_A_Payer').rjust(
                B02_N_AF_Net_A_Payer, ZERO)
            N_AF_A_Reverser = assuree.get('N_AF_Net_A_Payer', 0).rjust(
                B02_N_AF_A_Reverser, ZERO)
            salaire_brut = situation in ['SO', 'CS', 'MS'] and 0 or int(compute_value(
                code='BRUT_IMPOSABLE',
                date_start=self.date_from,
                date_stop=self.date_to,
                employee_id=employee.id,
                department_ids=self.get_departments(),
                state=self.get_state(),
            ) * 100)
            if salaire_brut == 0 and situation not in ['SO', 'CS', 'MS']:
                raise Warning(
                    _('L\'employe [%s] doit être marqué sortant car son salaire est nul' % employee_name))
            sp = self.env['hr.cotisation'].search([('code', 'in', ['MALADIE_MATERNITE','PENSION'])  ], limit=1).plafond_salariale
            sp = int(sp * 100)
            salaire_plaf = salaire_brut > sp and sp or salaire_brut
            N_Salaire_Reel = str(salaire_brut).rjust(B02_N_Salaire_Reel, ZERO)
            N_Salaire_Plaf = str(salaire_plaf).rjust(B02_N_Salaire_Plaf, ZERO)
            L_Nom_Prenom = assuree.get('L_Nom_Prenom').rjust(
                B02_L_Nom_Prenom, SPACE)
            N_Num_Assure = assuree.get('N_Num_Assure')
            nbr_enfants = int(compute_value(
                code='NBR_ALLOCATION_FAMILIALE',
                date_start=self.date_from,
                date_stop=self.date_to,
                employee_id=employee.id,
                department_ids=self.get_departments(),
                state=self.get_state(),
            ))
            N_Enfants = str(nbr_enfants).rjust(B02_N_Enfants, ZERO)
            ctr = long(N_Num_Assure) + long(N_AF_A_Reverser) + long(N_Jours_Declares) + \
                long(N_Salaire_Reel) + long(N_Salaire_Plaf) + \
                long(situation_value)
            S_Ctr = str(ctr).rjust(B02_S_Ctr, ZERO)
            if not L_Type_Enreg or not L_Periode or not N_Jours_Declares or not N_AF_A_Payer or not N_AF_A_Payer or not N_AF_A_Deduire or not L_Situation:
                raise Warning(
                    _('Erreur lors de la construction de [B02] pour l\'employe [%s]' % employee_name))
            line_b02 = None
            line_b02 = set_b02(L_Type_Enreg=L_Type_Enreg, N_Num_Affilie=N_Num_Affilie, L_Periode=L_Periode, N_Num_Assure=N_Num_Assure, L_Nom_Prenom=L_Nom_Prenom, N_Enfants=N_Enfants, N_AF_A_Payer=N_AF_A_Payer, N_AF_A_Deduire=N_AF_A_Deduire,
                               N_AF_Net_A_Payer=N_AF_Net_A_Payer, N_AF_A_Reverser=N_AF_A_Reverser, N_Jours_Declares=N_Jours_Declares, N_Salaire_Reel=N_Salaire_Reel, N_Salaire_Plaf=N_Salaire_Plaf, L_Situation=L_Situation, S_Ctr=S_Ctr, L_filler=L_filler)
            if line_b02 and len(line_b02) == LINE_MAX:
                tab_b02.append(line_b02)
            else:
                raise Warning(
                    _('Erreur lors de la construction de [B02] pour l\'employe [%s]' % employee_name))
        return tab_b02

    @api.multi
    def construct_b03(self, b02):
        L_Type_Enreg = 'B03'
        L_Type_Enreg = L_Type_Enreg.rjust(B03_L_Type_Enreg, SPACE)
        a01 = self.get_as().get(A01)
        N_Num_Affilie = a01.get('N_Num_Affilie').rjust(
            B03_N_Num_Affilie, SPACE)
        L_Periode = a01.get('L_Periode').rjust(B03_L_Periode, SPACE)
        N_Nbr_Salaries = str(len(b02)).rjust(B03_N_Nbr_Salaries, ZERO)
        L_filler = SPACE.rjust(B03_L_filler, SPACE)
        N_T_Enfants = 0
        N_T_AF_A_Payer = 0
        N_T_AF_A_Deduire = 0
        N_T_AF_Net_A_Payer = 0
        N_T_Num_Imma = 0
        N_T_AF_A_Reverser = 0
        N_T_Jours_Declares = 0
        N_T_Salaire_Reel = 0
        N_T_Salaire_Plaf = 0
        N_T_Ctr = 0
        logger.info('Construct B03')
        for line_str in b02:
            line = get_b02(line_str)
            N_T_Enfants += long(line.get('N_Enfants'))
            N_T_AF_A_Payer += long(line.get('N_AF_A_Payer'))
            N_T_AF_A_Deduire += long(line.get('N_AF_A_Deduire'))
            N_T_AF_Net_A_Payer += long(line.get('N_AF_Net_A_Payer'))
            N_T_Num_Imma += long(line.get('N_Num_Assure'))
            N_T_AF_A_Reverser += long(line.get('N_AF_A_Reverser'))
            N_T_Jours_Declares += long(line.get('N_Jours_Declares'))
            N_T_Salaire_Reel += long(line.get('N_Salaire_Reel'))
            N_T_Salaire_Plaf += long(line.get('N_Salaire_Plaf'))
            N_T_Ctr += long(line.get('S_Ctr'))
        N_T_Enfants = str(N_T_Enfants).rjust(B03_N_T_Enfants, ZERO)
        N_T_AF_A_Payer = str(N_T_AF_A_Payer).rjust(B03_N_T_AF_A_Payer, ZERO)
        N_T_AF_A_Deduire = str(N_T_AF_A_Deduire).rjust(
            B03_N_T_AF_A_Deduire, ZERO)
        N_T_AF_Net_A_Payer = str(N_T_AF_Net_A_Payer).rjust(
            B03_N_T_AF_Net_A_Payer, ZERO)
        N_T_Num_Imma = str(N_T_Num_Imma).rjust(B03_N_T_Num_Imma, ZERO)
        N_T_AF_A_Reverser = str(N_T_AF_A_Reverser).rjust(
            B03_N_T_AF_A_Reverser, ZERO)
        N_T_Jours_Declares = str(N_T_Jours_Declares).rjust(
            B03_N_T_Jours_Declares, ZERO)
        N_T_Salaire_Reel = str(N_T_Salaire_Reel).rjust(
            B03_N_T_Salaire_Reel, ZERO)
        N_T_Salaire_Plaf = str(N_T_Salaire_Plaf).rjust(
            B03_N_T_Salaire_Plaf, ZERO)
        N_T_Ctr = str(N_T_Ctr).rjust(B03_N_T_Ctr, ZERO)
        if not L_Type_Enreg or not N_Num_Affilie or not L_Periode or not N_Nbr_Salaries or not L_filler:
            raise Warning(_('Erreur lors de la construction de [B03]'))
        line_b03 = None
        line_b03 = set_b03(L_Type_Enreg=L_Type_Enreg, N_Num_Affilie=N_Num_Affilie, L_Periode=L_Periode, N_Nbr_Salaries=N_Nbr_Salaries, N_T_Enfants=N_T_Enfants, N_T_AF_A_Payer=N_T_AF_A_Payer, N_T_AF_A_Deduire=N_T_AF_A_Deduire,
                           N_T_AF_Net_A_Payer=N_T_AF_Net_A_Payer, N_T_Num_Imma=N_T_Num_Imma, N_T_AF_A_Reverser=N_T_AF_A_Reverser, N_T_Jours_Declares=N_T_Jours_Declares, N_T_Salaire_Reel=N_T_Salaire_Reel, N_T_Salaire_Plaf=N_T_Salaire_Plaf, N_T_Ctr=N_T_Ctr, L_filler=L_filler)
        if line_b03 and len(line_b03) == LINE_MAX:
            return line_b03
        else:
            raise Warning(_('Erreur lors de la construction de [B03]'))
        return True

    @api.multi
    def construct_b04(self):
        compute_value = self.env['hr.dictionnary'].compute_value
        b04_tab = []
        L_Type_Enreg = 'B04'.rjust(B04_L_Type_Enreg, SPACE)
        a01 = self.get_as().get(A01)
        N_Num_Affilie = a01.get('N_Num_Affilie').rjust(
            B04_N_Num_Affilie, SPACE)
        L_Periode = a01.get('L_Periode').rjust(B04_L_Periode, SPACE)
        L_filler = SPACE.rjust(B04_L_filler, SPACE)
        logger.info('Construct B04, Total : %s', len(self.entrant_ids))
        if not self.entrant_ids:
            N_Num_Assure = SPACE.rjust(B04_N_Num_Assure, SPACE)
            L_Nom_Prenom = SPACE.rjust(B04_L_Nom_Prenom, SPACE)
            L_Num_CIN = SPACE.ljust(B04_L_Num_CIN, SPACE)
            N_Nbr_Jours = ZERO.rjust(B04_N_Nbr_Jours, ZERO)
            N_Sal_Reel = ZERO.rjust(B04_N_Sal_Reel, ZERO)
            N_Sal_Plaf = ZERO.rjust(B04_N_Sal_Plaf, ZERO)
            S_Ctr = ZERO.rjust(B04_S_Ctr, ZERO)
            L_filler = SPACE.rjust(B04_L_filler, SPACE)
            line_b04 = set_b04(L_Type_Enreg=L_Type_Enreg, N_Num_Affilie=N_Num_Affilie, L_Periode=L_Periode, N_Num_Assure=N_Num_Assure, L_Nom_Prenom=L_Nom_Prenom,
                               L_Num_CIN=L_Num_CIN, N_Nbr_Jours=N_Nbr_Jours, N_Sal_Reel=N_Sal_Reel, N_Sal_Plaf=N_Sal_Plaf, S_Ctr=S_Ctr, L_filler=L_filler)
            if line_b04 and len(line_b04) == LINE_MAX:
                b04_tab.append(line_b04)
                return b04_tab
            else:
                raise Warning(_('Erreur lors de la construction de [B04]'))
        count = 0
        for entrant in self.entrant_ids.sorted(key=lambda r: r.cnss):
            count += 1
            logger.info('Construct B04, Item : %s/%s, Employe : %s', count, len(self.entrant_ids), entrant.name)
            if not entrant.cnss and not entrant.cin:
                raise Warning(
                    _('Il faut fournir CNSS ou CIN pour l\'employe [%s]') % entrant.name)
            nom = entrant.nom.strip().upper()
            prenom = entrant.prenom.strip().upper()
            num_assure = entrant.cnss or '0' * 9
            if len(num_assure) !=9 :
                raise Warning(
                    _('Veuillez vérifier l\'immatriculation CNSS de l\'employe [%s]') % entrant.name)
            N_Num_Assure = num_assure.rjust(B04_N_Num_Assure, SPACE)
            L_Nom_Prenom = nom.ljust(30, SPACE) + prenom.ljust(30, SPACE)
            L_Num_CIN = (entrant.cin or '').strip().replace(' ','').upper().ljust(
                B04_L_Num_CIN, SPACE)
            emp_ctx = entrant.with_context({
                'date': self.date_to,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'default': SPACE,
                'force_one': True,
            })
            situation = emp_ctx.get_situation().strip().upper()
            # FIXME remove first test warning on b01, b02, etc
            salaire_brut = situation in ['SO', 'CS', 'MS'] and 0 or int(compute_value(
                code='BRUT_IMPOSABLE',
                date_start=self.date_from,
                date_stop=self.date_to,
                employee_id=entrant.id,
                department_ids=self.get_departments(),
                state=self.get_state(),
            ) * 100)
            if salaire_brut == 0 and situation not in ['SO', 'CS', 'MS']:
                raise Warning(
                    _('L\'employé [%s] ne doit pas être parmis les entrants car le salaire est nul') % entrant.name)
            sp = self.env['hr.cotisation'].search([('code', 'in', ['MALADIE_MATERNITE','PENSION'])  ], limit=1).plafond_salariale
            sp = int(sp * 100)
            salaire_plaf = salaire_brut > sp and sp or salaire_brut
            nb_jours_declares = situation in ['SO', 'CS', 'MS'] and 0 or int(compute_value(
                code='NBR_JOURS',
                date_start=self.date_from,
                date_stop=self.date_to,
                employee_id=entrant.id,
                department_ids=self.get_departments(),
                state=self.get_state(),
            ))
            nb_jours_declares = nb_jours_declares >= 26 and 26 or nb_jours_declares
            N_Nbr_Jours = str(nb_jours_declares).rjust(B04_N_Nbr_Jours, ZERO)
            N_Sal_Reel = str(salaire_brut).rjust(B04_N_Sal_Reel, ZERO)
            N_Sal_Plaf = str(salaire_plaf).rjust(B04_N_Sal_Plaf, ZERO)
            # BEGIN OCCASIONNEL
            slips = emp_ctx.get_slips()
            slip = slips and slips[0] or False
            if slip and slip.contract_id.type_id.type != 'permanent':
                N_Num_Assure = '9'.rjust(B04_N_Num_Assure, '9')
                N_Nbr_Jours = ZERO.rjust(B04_N_Nbr_Jours, ZERO)
            # END OCCASIONNEL
            total_h = long(N_Num_Assure) + long(N_Nbr_Jours) + \
                long(N_Sal_Reel) + long(N_Sal_Plaf)
            S_Ctr = str(total_h).rjust(B04_S_Ctr, ZERO)
            if not L_Type_Enreg or not L_Nom_Prenom or not N_Nbr_Jours or not N_Sal_Reel or not N_Sal_Plaf:
                raise Warning(_('Erreur lors de la construction de [B04]'))
            line_b04 = None
            line_b04 = set_b04(L_Type_Enreg=L_Type_Enreg, N_Num_Affilie=N_Num_Affilie, L_Periode=L_Periode, N_Num_Assure=N_Num_Assure, L_Nom_Prenom=L_Nom_Prenom,
                               L_Num_CIN=L_Num_CIN, N_Nbr_Jours=N_Nbr_Jours, N_Sal_Reel=N_Sal_Reel, N_Sal_Plaf=N_Sal_Plaf, S_Ctr=S_Ctr, L_filler=L_filler)
            if line_b04 and len(line_b04) == LINE_MAX:
                b04_tab.append(line_b04)
            else:
                raise Warning(_('Erreur lors de la construction de [B04]'))
        return b04_tab

    @api.multi
    def construct_b05(self, b04):
        L_Type_Enreg = 'B05'
        a01 = self.get_as().get(A01)
        N_Num_Affilie = a01.get('N_Num_Affilie')
        L_Periode = a01.get('L_Periode')
        nb_entrant = len(self.entrant_ids)
        N_Nbr_Salaries = str(nb_entrant).rjust(B05_N_Nbr_Salaries, ZERO)
        N_T_Num_Imma = 0
        N_T_Jours_Declares = 0
        N_T_Salaire_Reel = 0
        N_T_Salaire_Plaf = 0
        N_T_Ctr = 0
        L_filler = SPACE.rjust(B05_L_filler, SPACE)
        logger.info('Construct B05')
        for line_str in b04:
            line = get_b04(line_str)
            try:
                N_T_Num_Imma += long(line.get('N_Num_Assure'))
            except:
                pass
            N_T_Jours_Declares += long(line.get('N_Nbr_Jours'))
            N_T_Salaire_Reel += long(line.get('N_Sal_Reel'))
            N_T_Salaire_Plaf += long(line.get('N_Sal_Plaf'))
            N_T_Ctr += long(line.get('S_Ctr'))
        N_T_Num_Imma = str(N_T_Num_Imma).rjust(B05_N_T_Num_Imma, ZERO)
        N_T_Jours_Declares = str(N_T_Jours_Declares).rjust(
            B05_N_T_Jours_Declares, ZERO)
        N_T_Salaire_Reel = str(N_T_Salaire_Reel).rjust(
            B05_N_T_Salaire_Reel, ZERO)
        N_T_Salaire_Plaf = str(N_T_Salaire_Plaf).rjust(
            B05_N_T_Salaire_Plaf, ZERO)
        N_T_Ctr = str(N_T_Ctr).rjust(B03_N_T_Ctr, ZERO)
        if not L_Type_Enreg or not N_Num_Affilie or not L_Periode or not N_T_Num_Imma or not N_T_Jours_Declares:
            raise Warning(_('Erreur lors de la construction de [B05]'))
        line_b05 = None
        line_b05 = set_b05(L_Type_Enreg=L_Type_Enreg, N_Num_Affilie=N_Num_Affilie, L_Periode=L_Periode, N_Nbr_Salaries=N_Nbr_Salaries, N_T_Num_Imma=N_T_Num_Imma,
                           N_T_Jours_Declares=N_T_Jours_Declares, N_T_Salaire_Reel=N_T_Salaire_Reel, N_T_Salaire_Plaf=N_T_Salaire_Plaf, N_T_Ctr=N_T_Ctr, L_filler=L_filler)
        if line_b05 and len(line_b05) == LINE_MAX:
            return line_b05
        else:
            raise Warning(_('Erreur lors de la construction de [B05]'))
        return True

    @api.multi
    def construct_b06(self, b03, b05):
        L_Type_Enreg = 'B06'.rjust(B06_L_Type_Enreg, SPACE)
        a01 = self.get_as().get(A01)
        logger.info('Construct B06')
        N_Num_Affilie = a01.get('N_Num_Affilie').rjust(
            B06_N_Num_Affilie, SPACE)
        L_Periode = a01.get('L_Periode').rjust(B06_L_Periode, SPACE)
        N_Nbr_Salaries = str(int(b03.get('N_Nbr_Salaries'))+int(b05.get('N_Nbr_Salaries'))).rjust(B06_N_Nbr_Salaries, ZERO)
        N_T_Num_Imma = 0
        N_T_Jours_Declares = 0
        N_T_Salaire_Reel = 0
        N_T_Salaire_Plaf = 0
        N_T_Ctr = 0
        L_filler = SPACE.rjust(B06_L_filler, SPACE)
        # BEGIN CUMUL
        N_T_Num_Imma += long(b03.get('N_T_Num_Imma')) + \
            long(b05.get('N_T_Num_Imma'))
        N_T_Jours_Declares += long(b03.get('N_T_Jours_Declares')
                                   ) + long(b05.get('N_T_Jours_Declares'))
        N_T_Salaire_Reel += long(b03.get('N_T_Salaire_Reel')
                                 ) + long(b05.get('N_T_Salaire_Reel'))
        N_T_Salaire_Plaf += long(b03.get('N_T_Salaire_Plaf')
                                 ) + long(b05.get('N_T_Salaire_Plaf'))
        N_T_Ctr += long(b03.get('N_T_Ctr')) + long(b05.get('N_T_Ctr'))
        # END CUMUL
        N_T_Num_Imma = str(N_T_Num_Imma).rjust(B06_N_T_Num_Imma, ZERO)
        N_T_Jours_Declares = str(N_T_Jours_Declares).rjust(
            B06_N_T_Jours_Declares, ZERO)
        N_T_Salaire_Reel = str(N_T_Salaire_Reel).rjust(
            B06_N_T_Salaire_Reel, ZERO)
        N_T_Salaire_Plaf = str(N_T_Salaire_Plaf).rjust(
            B06_N_T_Salaire_Plaf, ZERO)
        N_T_Ctr = str(N_T_Ctr).rjust(B06_N_T_Ctr, ZERO)
        if not L_Type_Enreg or not N_Num_Affilie or not L_Periode or not N_T_Num_Imma or not N_T_Jours_Declares:
            raise Warning(_('Erreur lors de la construction de [B06]'))
        line_b06 = None
        line_b06 = set_b06(L_Type_Enreg=L_Type_Enreg, N_Num_Affilie=N_Num_Affilie, L_Periode=L_Periode, N_Nbr_Salaries=N_Nbr_Salaries, N_T_Num_Imma=N_T_Num_Imma,
                           N_T_Jours_Declares=N_T_Jours_Declares, N_T_Salaire_Reel=N_T_Salaire_Reel, N_T_Salaire_Plaf=N_T_Salaire_Plaf, N_T_Ctr=N_T_Ctr, L_filler=L_filler)
        if line_b06 and len(line_b06) == LINE_MAX:
            return line_b06
        else:
            raise Warning(_('Erreur lors de la construction de [B06]'))
        return True


class hr_employee_temp(models.TransientModel):
    _name = 'hr.employee.temp'
    _description = u'Employés'

    name = fields.Char(string=u'Nom', size=64,)
