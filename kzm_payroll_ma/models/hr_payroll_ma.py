# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime, time
from . import convertion


# Classe : Paie
class HrPayrollMa(models.Model):
    _name = "hr.payroll_ma"
    _description = 'Saisie des bulletins'
    _order = "number"

    def _get_journal(self):
        params = self.env['hr.payroll_ma.parametres']
        company_id = self.env['res.users'].browse(self.env.uid).company_id
        parametres = params.search([('company_id', '=', company_id.id)], limit=1)
        journal_id = parametres.journal_id
        # journal_id = self.env.ref('account.salary_journal')
        return journal_id.id

    name = fields.Char(string='Description', required=True)
    number = fields.Char(string=u'Code', readonly=True)
    date_start = fields.Date(string=u'Date début')
    date_end = fields.Date(string=u'Date fin')
    date_salary = fields.Date(string='Date', states={'open': [('readonly', True)], 'close': [('readonly', True)]})
    company_id = fields.Many2one('res.company', string=u'Société', default=lambda self: self.env.user.company_id, copy=False)
    period_id = fields.Many2one('date.range', string=u'Période', domain=[('type_id.fiscal_period', '=', True)],
                                required=True, states={'draft': [('readonly', False)]})
    bulletin_line_ids = fields.One2many('hr.payroll_ma.bulletin', 'id_payroll_ma',
                                        string='Bulletins',  states={'draft': [('readonly', False)]})
    move_id = fields.Many2one('account.move', string=u'Pièce comptable',
                              readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', default=_get_journal,
                                 required=True,  states={'draft': [('readonly', False)]})
    state = fields.Selection(selection=(
            ('draft', 'Brouillon'),
            ('confirmed', u'Confirmé'),
            ('paid', u'Payé'),
            ('cancelled', u'Annulé')
             ), string='Statut', readonly=True, default='draft')
    total_net = fields.Float(string='Total net', compute='get_total_net', digits=(16, 2))

    @api.model
    def create(self, vals):
        vals['number'] = self.env['ir.sequence'].next_by_code('hr.payroll_ma')
        result = super(HrPayrollMa, self).create(vals)
        return result

    @api.constrains('period_id')
    def _check_unicity_periode(self):
        payroll_ids = self.env['hr.payroll_ma'].search([('period_id', '=', self.period_id.id)])
        if len(payroll_ids) > 1:
            raise ValidationError(u'On ne peut pas avoir deux paies pour la même période !')

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(u"Suppression impossible")
            rec.bulletin_line_ids.unlink()
            payroll_id = super(HrPayrollMa, self).unlink()
            return payroll_id

    @api.multi
    def get_total_net(self):
        for rec in self:
            net = 0
            for line in rec.bulletin_line_ids:
                net += line.salaire_net_a_payer
            rec.total_net = net

    @api.onchange('company_id', 'period_id')
    def onchange_period_id(self):
        if self.company_id and self.period_id:
            self.name = 'Paie ' + self.company_id.name + u' de la période ' + self.period_id.name
            self.date_start = self.period_id.date_start
            self.date_end = self.period_id.date_end

    @api.multi
    def draft_cb(self):
        for rec in self:
            if rec.move_id:
                raise ValidationError(u"Veuillez d'abord supprimer les écritures comptables associés")
            rec.state = 'draft'

    @api.multi
    def confirm_cb(self):
        for rec in self:
            rec.action_move_create()
            rec.state = 'confirmed'
            for bulletin in rec.bulletin_line_ids:
                bulletin.name = self.env['ir.sequence'].next_by_code('hr.payroll_ma.bulletin')

    @api.multi
    def cancel_cb(self):
        for rec in self:
            rec.state = 'cancelled'

    @api.multi
    def generate_employees(self):
        for rec in self:
            employee_obj = self.env['hr.employee']
            obj_contract = self.env['hr.contract']
            employees = employee_obj.search([('active', '=', True),
                                             ('date', '<=', rec.date_end),
                                             ('company_id', '=', rec.company_id.id),
                                             ])
            if rec.state == 'draft':
                sql = '''
                DELETE from hr_payroll_ma_bulletin where id_payroll_ma = %s
                    '''
                self.env.cr.execute(sql, (rec.id,))

            for employee in employees:
                contract = obj_contract.search([('employee_id', '=', employee.id),
                                                ('state', 'in', ('draft', 'open')),
                                                ('actif', '=', True)], order='date_start', limit=1)

                absences = '''  select sum(number_of_days)
                                from    hr_holidays h
                                left join hr_holidays_status s on (h.holiday_status_id=s.id)
                                where date_from >= '%s' and date_to <= '%s'
                                and employee_id = %s
                                and state = 'validate'
                                and s.payed=False''' % (rec.period_id.date_start, rec.period_id.date_end, employee.id)
                self.env.cr.execute(absences)
                res = self.env.cr.fetchone()
                if res[0] is None:
                    days = 0
                else:
                    days = res[0]

                # absences = '''  select sum(number_of_days)
                #                 from    hr_leave h
                #                 left join hr_leave_type s on (h.holiday_status_id=s.id)
                #                 where date_from >= '%s' and date_to <= '%s'
                #                 and employee_id = %s
                #                 and state = 'validate'
                #                 and s.unpaid=True''' % (rec.period_id.date_start, rec.period_id.date_end, employee.id)
                # self.env.cr.execute(absences)
                # res = self.env.cr.fetchone()
                # if res[0] is None:
                #     days = 0
                # else:
                #     days = res[0]

                if contract:
                    line = {
                            'employee_id': employee.id,
                            'employee_contract_id': contract.id,
                            'working_days': contract.working_days_per_month + days,
                            'normal_hours': contract.monthly_hour_number,
                            'hour_base': contract.hour_salary,
                            'salaire_base': contract.wage,
                            'id_payroll_ma': rec.id,
                            'period_id': rec.period_id.id,
                            'date_start': rec.date_start,
                            'date_end': rec.date_end,
                            'date_salary':rec.date_salary

                            }
                    self.env['hr.payroll_ma.bulletin'].create(line)
        return True

    @api.multi
    def compute_all_lines(self):
        for rec in self:
            for bulletin in rec.bulletin_line_ids:
                bulletin.compute_all_lines()
        return True

    # Generation des écriture comptable
    @api.multi
    def action_move_create(self):
        for rec in self:
            params = self.env['hr.payroll_ma.parametres']
            dictionnaire = params.search([('company_id', '=', rec.company_id.id)],limit=1)
            date = rec.date_salary or datetime.now().date()
            journal = rec.journal_id
            move_lines = []
            bulletins = self.env['hr.payroll_ma.bulletin'].search([('id_payroll_ma', '=', rec.id)])
            # Cotisations
            operateur = 'in'
            ids = tuple(bulletins.ids)
            if len(bulletins) == 1:
                operateur = '='
                ids = bulletins.id
            sql = """SELECT l.name as name ,
                            sum(subtotal_employee) as subtotal_employee,
                            sum(subtotal_employer) as subtotal_employer,
                            l.credit_account_id,
                            l.debit_account_id
                            FROM    hr_payroll_ma_bulletin_line l
                            where   l.type = 'cotisation' and id_bulletin %s %s
                            group by l.name, l.credit_account_id, l.debit_account_id
                  """ % (operateur, ids )
            self.env.cr.execute(sql)
            data = self.env.cr.dictfetchall()
            msg = u"Merci d'ajouter les comptes crédit/débit pour les Cotisations, Paramètres et Rubriques"
            for line in data:
                if not line['credit_account_id'] or not line['debit_account_id']:
                    raise ValidationError(msg)
                if line['subtotal_employee']:
                    move_line_credit = {
                                         'account_id': line['credit_account_id'],
                                         'journal_id': journal.id,
                                         'date': date,
                                         'name': (line['name'] or '\\') + ' Salarial',
                                         'credit': line['subtotal_employee'],
                                         'debit': 0,
                                         'state': 'valid'
                                         }
                    move_lines.append((0, 0, move_line_credit))

                if line['subtotal_employer']:
                    move_line_debit = {
                                     'account_id': line['debit_account_id'],
                                     'journal_id': journal.id,
                                     'date': date,
                                     'name': (line['name'] or '\\') + ' Patronal',
                                     'debit': line['subtotal_employer'],
                                     'credit': 0,
                                     'state': 'valid'
                                     }
                    move_line_credit = {
                                     'account_id': line['credit_account_id'],
                                     'journal_id': journal.id,
                                     'date': date,
                                     'name': (line['name'] or '\\') + ' Patronal',
                                     'debit': 0,
                                     'credit': line['subtotal_employer'],
                                     'state': 'valid'
                                     }
                    move_lines.append((0, 0, move_line_debit))
                    move_lines.append((0, 0, move_line_credit))

            # Rubriques
            sql = """
                    SELECT  l.name as name, 
                            sum(subtotal_employee) as subtotal_employee,
                            sum(subtotal_employer) as subtotal_employer,
                            l.credit_account_id,
                            l.debit_account_id
                    FROM    hr_payroll_ma_bulletin_line l
                    where   l.type = 'brute' and id_bulletin %s %s
                            and l.credit_account_id is not null 
                            and l.debit_account_id is not null
                    group by l.name, l.credit_account_id, l.debit_account_id
                    """ % (operateur, ids )
            self.env.cr.execute(sql)
            data_rub = self.env.cr.dictfetchall()
            for line in data_rub:
                if not line['debit_account_id']:
                    raise ValidationError(msg)
                move_line_debit_rubrique = {
                                         'account_id': line['debit_account_id'],
                                         # 'analytic_account_id': dictionnaire['analytic_account_id'][0],
                                         'journal_id': journal.id,
                                         'date': date,
                                         'name': line['name'] or '\\',
                                         'debit':  line['subtotal_employee'],
                                         'credit': 0,
                                         'state': 'valid'
                                         }
                move_lines.append((0, 0, move_line_debit_rubrique))
                # Rubriques deduction
            sql = """
                SELECT  l.name as name,
                sum(subtotal_employee) as subtotal_employee,
                sum(subtotal_employer) as subtotal_employer,
                l.credit_account_id,
                l.debit_account_id
                FROM hr_payroll_ma_bulletin_line l
                where l.type = 'retenu' and id_bulletin %s %s
                and l.credit_account_id is not null
                and l.debit_account_id is not null
                group by l.name, l.credit_account_id, l.debit_account_id
                """ % (operateur, ids )
            self.env.cr.execute(sql)
            data_rub = self.env.cr.dictfetchall()
            for line in data_rub:
                if not line['credit_account_id']:
                    raise ValidationError(msg)
                move_line_credit_rubrique = {
                        'account_id': line['credit_account_id'],
                        # 'analytic_account_id': dictionnaire['analytic_account_id'][0],
                        'journal_id': journal.id,
                        'date': date,
                        'name': line['name'] or '\\',
                        'debit': 0,
                        'credit': line['subtotal_employee'],
                        'state': 'valid'
                    }
                move_lines.append((0, 0, move_line_credit_rubrique))

            # Salaire brute
            sql = '''
                    SELECT  sum(subtotal_employee) as subtotal_employee,
                            sum(subtotal_employer) as subtotal_employer,
                            l.credit_account_id,
                            l.debit_account_id
                    FROM    hr_payroll_ma_bulletin_line l
                    where   l.type = 'brute' and id_bulletin %s %s 
                            and l.credit_account_id is null 
                            and l.debit_account_id is null
                    group   by l.credit_account_id, l.debit_account_id
                    ''' % (operateur, ids )

            self.env.cr.execute(sql)
            data_paie = self.env.cr.dictfetchall()
            for line in data_paie:
                if not dictionnaire.salary_debit_account_id:
                    raise ValidationError(msg)
                move_line_debit_brute = {
                                         'account_id': dictionnaire.salary_debit_account_id.id,
                                         # 'analytic_account_id': dictionnaire['analytic_account_id'][0],
                                         'journal_id': journal.id,
                                         'date': date,
                                         'name': 'Salaire brute',
                                         'debit':  line['subtotal_employee'],
                                         'credit': 0,
                                         'state': 'valid'
                                         }
                move_lines.append((0, 0, move_line_debit_brute))

            # salaire_net_a_payer, arrondi
            sql = '''
                    SELECT  sum(salaire_brute) as salaire_brute,
                            sum(salaire_net_a_payer) as salaire_net_a_payer,
                            sum(arrondi) as arrondi,
                            sum(deduction) as deduction
                    FROM    hr_payroll_ma_bulletin b
                            LEFT JOIN hr_payroll_ma pm ON pm.id=b.id_payroll_ma
                    where   b.id_payroll_ma = %s
                    ''' % (rec.id,)
            self.env.cr.execute(sql)
            data = self.env.cr.dictfetchall()
            data = data[0]
            if not dictionnaire.salary_debit_account_id or not dictionnaire.salary_credit_account_id:
                raise ValidationError(msg)
            move_line_arrondi = {
                                         'account_id': dictionnaire.salary_debit_account_id.id,
                                         # 'analytic_account_id': dictionnaire['analytic_account_id'][0],
                                         'journal_id': journal.id,
                                         'date': date,
                                         'name': 'Arrondi',
                                         'debit':  data['arrondi'],
                                         'credit': 0,
                                         'state': 'valid'
                                         }
            move_line_credit = {
                                         'account_id': dictionnaire.salary_credit_account_id.id,
                                         'journal_id': journal.id,
                                         'date': date,
                                         'name': 'Salaire net a payer',
                                         'credit': data['salaire_net_a_payer'],
                                         'debit': 0,
                                         'state': 'valid'
                                         }
            move_lines.append((0, 0, move_line_arrondi))
            move_lines.append((0, 0, move_line_credit))

            credit = 0
            debit = 0
            for e in move_lines:
                credit += e[2]['credit']
                debit += e[2]['debit']
            if credit < debit:
                diff = debit - credit
                move_line_arrondi = {
                                         'account_id': dictionnaire.salary_debit_account_id.id,
                                         # 'analytic_account_id': dictionnaire['analytic_account_id'][0],
                                         'journal_id': journal.id,
                                         'date': date,
                                         'name': 'Arrondi',
                                         'credit':  round(diff, 2),
                                         'debit': 0,
                                         'state': 'valid'
                                         }
                move_lines.append((0, 0, move_line_arrondi))
            else:
                diff = credit - debit
                move_line_arrondi = {
                                         'account_id': dictionnaire.salary_debit_account_id.id,
                                         # 'analytic_account_id': dictionnaire['analytic_account_id'][0],
                                         'journal_id': journal.id,
                                         'date': date,
                                         'name': 'Arrondi',
                                         'debit':  round(diff, 2),
                                         'credit': 0,
                                         'state': 'valid'
                                         }
                move_lines.append((0, 0, move_line_arrondi))

            move = {
                    'ref': rec.number,
                    'journal_id': journal.id,
                    'date': date,
                    'state': 'draft',
                    'name': rec.name or '\\',
                    'line_ids': move_lines}
            move_id = self.env['account.move'].create(move)
            rec.move_id = move_id
            return True


# Classe : Bulletin de paie
class hrPayrollMaBulletin(models.Model):
    _name = "hr.payroll_ma.bulletin"
    _description = 'bulletin'
    _order = "name"

    @api.multi
    @api.depends('salaire_net_a_payer')
    def _get_amount_text(self):
        for rec in self:
            devise = 'DH'
            rec.salaire_net_a_payer_text = convertion.trad(rec.salaire_net_a_payer, devise).upper()

    name = fields.Char(string=u'Code', readonly=True)
    date_start = fields.Date(string=u'Date début')
    date_end = fields.Date(string='Date fin')
    date_salary = fields.Date(string='Date salaire')
    employee_id = fields.Many2one('hr.employee', string=u'Employé', required=True)
    period_id = fields.Many2one('date.range', domain="[('type_id.fiscal_period','=',True)]", string=u'Période')
    salary_line_ids = fields.One2many('hr.payroll_ma.bulletin.line', 'id_bulletin', string='Lignes de salaire', readonly=True)
    employee_contract_id = fields.Many2one('hr.contract', string=u'Contrat de travail', required=True)
    id_payroll_ma = fields.Many2one('hr.payroll_ma', string=u'Réf Paie', ondelete='cascade')
    salaire_base = fields.Float(string='Salaire de base')
    taux_journalier = fields.Float(string='Taux journalier')
    normal_hours = fields.Float(string=u'Heures travaillées durant le mois')
    hour_base = fields.Float(string=u'Salaire horaire')
    comment = fields.Text(string=u'Informations complémentaires')
    salaire = fields.Float(string='Salaire de Base', readonly=True, digits=(16, 2))
    salaire_brute = fields.Float(string='Salaire brut', readonly=True, digits=(16, 2))
    salaire_brute_imposable = fields.Float(string='Salaire brut imposable', readonly=True, digits=(16, 2))
    salaire_net = fields.Float(string=u'Salaire Net', readonly=True, digits=(16, 2))
    salaire_net_a_payer = fields.Float(string=u'Salaire Net à payer', readonly=True, digits=(16, 2))
    indemnites_frais_pro = fields.Float(string=u'Indemnités versées à titre de frais professionnels', readonly=True, digits=(16, 2))
    salaire_net_a_payer_text = fields.Char(compute='_get_amount_text', string='Montant en lettres', store=True)
    salaire_net_imposable = fields.Float(string=u'Salaire Net Imposable', readonly=True, digits=(16, 2))
    cotisations_employee = fields.Float(string=u'Cotisations Employé', readonly=True, digits=(16, 2))
    cotisations_employer = fields.Float(string='Cotisations Employeur', readonly=True, digits=(16, 2))
    igr = fields.Float(string=u'Impot sur le revenu', readonly=True, digits=(16, 2))
    prime = fields.Float(string='Primes', readonly=True, digits=(16, 2))
    indemnite = fields.Float(string=u'Indemnités', readonly=True, digits=(16, 2))
    avantage = fields.Float(string='Avantages', readonly=True, digits=(16, 2))
    exoneration = fields.Float(string=u'Exonérations', readonly=True, digits=(16, 2))
    deduction = fields.Float(string=u'Déductions', readonly=True, digits=(16, 2))
    working_days = fields.Float(string=u'Jours travaillés', digits=(16, 2))
    prime_anciennete = fields.Float(string=u'Prime ancienneté', digits=(16, 2))
    frais_pro = fields.Float(string='Frais professionnels', digits=(16, 2))
    personnes = fields.Integer(string='Personnes')
    absence = fields.Float(string='Absences', digits=(16, 2))
    arrondi = fields.Float(string='Arrondi', digits=(16, 2))
    logement = fields.Float(string='Logement', digits=(16, 2))

    # Ajout des champs de cumul
    cumul_normal_hours = fields.Float(compute='get_cumuls', string=u'Cumul des HT', digits=(16, 2))
    cumul_work_days = fields.Float(compute='get_cumuls', string=u'Cumul des JT', digits=(16, 2))
    cumul_sbi = fields.Float(compute='get_cumuls', string='Cumul SBI', digits=(16, 2))
    cumul_base = fields.Float(compute='get_cumuls', string='Cumul base', digits=(16, 2))
    cumul_sb = fields.Float(compute='get_cumuls', string='Cumul SB', digits=(16, 2))
    cumul_sni = fields.Float(compute='get_cumuls', string='Cumul SNI', digits=(16, 2))
    cumul_sni_n_1 = fields.Float(compute='get_cumuls_n_1', string=u'Cumul SNI N-1', digits=(16, 2))
    cumul_igr = fields.Float(compute='get_cumuls', string='Cumul IR', digits=(16, 2))
    cumul_igr_n_1 = fields.Float(compute='get_cumuls_n_1', string='Cumul IR N-1', digits=(16, 2))
    cumul_ee_cotis = fields.Float(compute='get_cumuls', string=u'Cumul Cotis employé', digits=(16, 2))
    cumul_er_cotis = fields.Float(compute='get_cumuls', string='Cumul Cotis employeur', digits=(16, 2))
    cumul_fp = fields.Float(compute='get_cumuls', string='Cumul frais professionnels', digits=(16, 2))
    cumul_avn = fields.Float(compute='get_cumuls', string=u'Cumul Avtg en nature', digits=(16, 2))
    cumul_exo = fields.Float(compute='get_cumuls', string=u'Cumul exonéré', digits=(16, 2))
    cumul_indemnites_fp = fields.Float(compute='get_cumuls', string='Cumul Indemn. frais professionnels')
    cumul_avantages = fields.Float(compute='get_cumuls', string='Cumul Avantages')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id,
                                 string='Société', readonly=True, copy=False)

    @api.onchange('period_id')
    def onchange_period_id(self):
        self.date_start = self.period_id.date_start
        self.date_end = self.period_id.date_end

    @api.multi
    def get_bulletin_cumuls(self, mois, annee, employe):
        ligne_bul_paie = self.env['hr.payroll_ma.bulletin.line']
        acct_period = self.env['date.range']
        bul = self.env['hr.payroll_ma.bulletin']
        cumuls = {}
        for res in self:
            v_period = str(mois).rjust(2, '0') + "/" + str(annee)
            period = acct_period.search([('name', '=', v_period)])
            bulletin = bul.search([('period_id', '=', period.id), ('employee_id', '=', employe)])

            if bulletin:
                bul = bulletin[0]
                cumuls['normal_hours'] = bul.normal_hours
                cumuls['working_days'] = bul.working_days
                cumuls['salaire_base'] = bul.salaire_base
                cumuls['salaire_brut_imposable'] = bul.salaire_brute_imposable
                cumuls['salaire_brut'] = bul.salaire_brute
                cumuls['salaire_net_imposable'] = bul.salaire_net_imposable
                cumuls['igr'] = bul.igr
                cumuls['cotisations_employee'] = bul.cotisations_employee
                cumuls['cotisations_employer'] = bul.cotisations_employer
                cumuls['indemnites_frais_pro'] = bul.indemnites_frais_pro
                cumuls['exonerations'] = bul.exoneration
                cumuls['avn'] = bul.indemnite
                cumuls['avantages'] = bul.avantage
                if bul.frais_pro < 2500:
                    cumuls['fp'] = bul.frais_pro
                else:
                    cumuls['fp'] = 2500.0
        return cumuls

    @api.multi
    def get_cumuls(self):
        for res in self:
            periode = res.period_id.name.split('/')
            mois = periode[0]
            annee = periode[1]

            somme_nh = 0.0
            somme_wd = 0.0
            somme_sbi = 0.0
            somme_base = 0.0
            somme_sb = 0.0
            somme_sni = 0.0
            somme_igr = 0.0
            somme_cot_ee = 0.0
            somme_cot_er = 0.0
            somme_fp = 0.0
            somme_avn = 0.0
            somme_ind_fp = 0.0
            somme_avantages = 0.0
            somme_exo = 0.0
            for j in range(1, int(mois) + 1, 1):
                valeur_mois = res.get_bulletin_cumuls(j, annee, res.employee_id.id)
                if valeur_mois:
                    somme_base += valeur_mois['salaire_base']
                    somme_nh += valeur_mois['normal_hours']
                    somme_wd += valeur_mois['working_days']
                    somme_sbi += valeur_mois['salaire_brut_imposable']
                    somme_sb += valeur_mois['salaire_brut']
                    somme_sni += valeur_mois['salaire_net_imposable']
                    somme_igr += valeur_mois['igr']
                    somme_cot_ee += valeur_mois['cotisations_employee']
                    somme_cot_er += valeur_mois['cotisations_employer']
                    somme_fp += valeur_mois['fp']
                    somme_avn += valeur_mois['avn']
                    somme_ind_fp += valeur_mois['indemnites_frais_pro']
                    somme_exo += valeur_mois['exonerations']
                    somme_avantages += valeur_mois['avantages']

            res.cumul_normal_hours = somme_nh
            res.cumul_work_days = somme_wd
            res.cumul_sbi = somme_sbi
            res.cumul_base = somme_base
            res.cumul_sb = somme_sb
            res.cumul_sni = somme_sni
            res.cumul_igr = somme_igr
            res.cumul_ee_cotis = somme_cot_ee
            res.cumul_er_cotis = somme_cot_er
            res.cumul_fp = somme_fp
            res.cumul_avn = somme_avn
            res.cumul_indemnites_fp = somme_ind_fp
            res.cumul_exo = somme_exo
            res.cumul_avantages = somme_avantages
        return True

    @api.multi
    def get_cumuls_n_1(self):
        for res in self:
            periode = res.period_id.name.split('/')
            mois = periode[0]
            annee = periode[1]
            somme_sni = 0.0
            somme_igr = 0.0
            for j in range(1, int(mois), 1):
                valeur_mois = res.get_bulletin_cumuls(j, annee, res.employee_id.id)
                if valeur_mois:
                    somme_sni += valeur_mois['salaire_net_imposable']
                    somme_igr += valeur_mois['igr']
                res.cumul_sni_n_1 = somme_sni
                res.cumul_igr_n_1 = somme_igr

    @api.model
    def _name_get_default(self):
        return self.env['ir.sequence'].next_by_code('hr.payroll_ma.bulletin')

    @api.onchange('employee_contract_id')
    def onchange_contract_id(self):
        contract = self.employee_contract_id
        if contract:
            self.salaire_base = contract.wage
            self.hour_base = contract.hour_salary
            self.normal_hours = contract.monthly_hour_number
            self.employee_id = contract.employee_id.id

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.env.context.get('period_id'):
            self.period_id = self.env.context.get('period_id')
        if self.env.context.get('date_start'):
            self.date_start = self.env.context.get('date_start')
        if self.env.context.get('date_end'):
            self.date_end = self.env.context.get('date_end')
        if not self.period_id:
            raise ValidationError(u"Vous devez d'abord spécifier une période !")
        if self.period_id and self.employee_id:
            if not self.employee_id.contract_id:
                return True
            else:
                sql = '''select sum(number_of_days) 
                        from    hr_leave h
                                left join hr_leave_type s on (h.holiday_status_id=s.id)
                        where date_from >= '%s' and date_to <= '%s'
                              and employee_id = %s
                              and state = 'validate'
                              and s.unpaid=True''' % (self.period_id.date_start, self.period_id.date_end, self.employee_id.id)
                self.env.cr.execute(sql)
                res = self.env.cr.fetchone()
                if res[0] is None:
                    days = 0
                else:
                    days = res[0]
                self.employee_contract_id = self.employee_id.contract_id.id
                self.salaire_base = self.employee_id.contract_id.wage
                self.hour_base = self.employee_id.contract_id.hour_salary
                self.normal_hours = self.employee_id.contract_id.monthly_hour_number
                self.working_days = 26 - abs(days)
                self.period_id = self.period_id.id

    def get_parametere(self):
        params = self.env['hr.payroll_ma.parametres']
        ids_params = params.search([('company_id', '=', self.company_id.id)], limit=1)
        return ids_params

    # Fonction pour la calcul de IR
    @api.multi
    def get_ir(self, sbi, cotisations, logement):
        for rec in self:
            taux = 0
            somme = 0
            salaire_net_imposable = 0
            bulletin = rec
            coef = 0

            dictionnaire = rec.get_parametere()
            if not bulletin.employee_contract_id.ir:
                res = {
                        'salaire_net_imposable': salaire_net_imposable,
                        'taux': 0,
                        'ir_net': 0,
                        'credit_account_id': dictionnaire.credit_account_id.id,
                        'frais_pro': 0,
                        'personnes': 0
                       }
            else:
                base = 0
                if rec.normal_hours:
                    base = rec.normal_hours / 8
                elif rec.working_days:
                    base = rec.working_days

                # Salaire Net Imposable
                fraispro = sbi * dictionnaire.fraispro / 100
                plafond = (dictionnaire.plafond * base) / 26
                if fraispro < plafond:
                    salaire_net_imposable = sbi - fraispro - cotisations
                else:
                    salaire_net_imposable = sbi - plafond - cotisations

                # logement
                salaire_logement = salaire_net_imposable * 10 / 100
                if logement > salaire_logement:
                    logement = salaire_logement
                salaire_net_imposable = salaire_net_imposable - logement
                rec.salaire_net_imposable = salaire_net_imposable
                rec.get_cumuls()
                count_days = rec.cumul_work_days
                count_hours = rec.cumul_normal_hours

                if bulletin.employee_contract_id.type == 'mensuel' and count_days:
                    coef = 312 / count_days
                elif bulletin.employee_contract_id.type == 'horaire' and count_hours:
                    coef = 191 * 12 / count_hours

                new_cumul_net_imp = bulletin.cumul_sni
                cumul_coef = new_cumul_net_imp * coef

                # IR Brut
                ir_bareme = self.env['hr.payroll_ma.ir']
                ir_bareme_list = ir_bareme.search([])

                for tranche in ir_bareme_list:
                    if (cumul_coef >= tranche.debuttranche) and (cumul_coef < tranche.fintranche):
                        taux = tranche.taux
                        somme = coef and (tranche.somme / coef) or 0.0

                ir_cumul_brut = ((new_cumul_net_imp) * taux / 100) - somme

                ir_brute = ir_cumul_brut - rec.cumul_igr_n_1

                # IR Net
                personnes = bulletin.employee_id.chargefam
                if (ir_brute - (personnes * dictionnaire.charge)) < 0:
                    ir_net = 0
                else:
                    ir_net = ir_brute - (personnes * dictionnaire.charge)

                res = {
                    'salaire_net_imposable': salaire_net_imposable,
                    'taux': taux,
                    'ir_net': ir_net,
                    'credit_account_id': dictionnaire.credit_account_id.id,
                    'frais_pro': fraispro,
                    'personnes': personnes
                    }
        return res

    def calc_seniority(self, date_embauche, date_paie):
        # date_embauche = str(date_embauche).split('-')
        # date_paie = str(date_paie).split('-')
        seniority_date = datetime.strptime(date_embauche, '%Y-%m-%d')
        date_paie = datetime.strptime(date_paie, '%Y-%m-%d')
        years = date_paie.year - seniority_date.year
        if date_paie.month < seniority_date.month or (
                date_paie.month == seniority_date.month and date_paie.day < seniority_date.day):
            years -= 1

        annees_anciennete = years
        objet_anciennete = self.env['hr.payroll_ma.anciennete']
        liste = objet_anciennete.search([])
        if years > 0:
            for tranche in liste:
                if (years >= tranche.debuttranche) and (years < tranche.fintranche):
                    return tranche.taux
        else:
            return 0

    @api.multi
    def compute_all_lines(self):
        for rec in self:
            dictionnaire = self.get_parametere()
            id_bulletin = rec.id
            bulletin = rec
            if not bulletin.period_id:
                rec.period_id = bulletin.id_payroll_ma.period_id.id

            sql = ''' DELETE from hr_payroll_ma_bulletin_line where id_bulletin = %s '''
            self.env.cr.execute(sql, (id_bulletin,))

            salaire_base = bulletin.salaire_base
            normal_hours = bulletin.normal_hours
            hour_base = bulletin.hour_base
            working_days = bulletin.working_days

            salaire_base_worked = 0
            salaire_brute = 0
            salaire_brute_imposable = 0
            salaire_net = 0
            salaire_net_imposable = 0
            cotisations_employee = 0
            cotisations_employer = 0
            prime = 0
            indemnite = 0
            avantage = 0
            exoneration = 0
            prime_anciennete = 0
            deduction = 0
            logement = bulletin.employee_id.logement
            frais_pro = 0
            personne = 0
            absence = 0
            arrondi = 0

            # Salaire de base
            if salaire_base:
                absence += salaire_base - (salaire_base * (bulletin.working_days / 26))
                salaire_base_line = {
                    'name': 'Salaire de base',
                    'id_bulletin': id_bulletin,
                    'type': 'brute',
                    'base': round(salaire_base, 2),
                    'rate_employee': round((bulletin.working_days / 26) * 100, 2),
                    'subtotal_employee': round(salaire_base * (bulletin.working_days / 26), 2),
                    'deductible': False,
                   }
                salaire_base_worked += salaire_base * (bulletin.working_days / 26)
                self.env['hr.payroll_ma.bulletin.line'].create(salaire_base_line)

            elif hour_base:
                normale_hours_line = {
                    'name': 'Heures normales',
                    'id_bulletin': id_bulletin,
                    'type': 'brute',
                    'base': normal_hours,
                    'rate_employee': hour_base,
                    'subtotal_employee': normal_hours * hour_base,
                    'deductible': False,
                    }
                salaire_base_worked += hour_base * round(normal_hours, 2)
                self.env['hr.payroll_ma.bulletin.line'].create(normale_hours_line)
            # Rubriques majoration
            sql = '''
                SELECT  l.montant,l.taux,r.name,r.categorie,r.type,r.formule,r.afficher,r.sequence,r.imposable,
                        r.plafond,r.ir,r.anciennete,r.absence,r.id,r.conge,r.credit_account_id, r.debit_account_id, r.is_hourly
                FROM    hr_payroll_ma_ligne_rubrique l
                        LEFT JOIN hr_payroll_ma_rubrique r on (l.rubrique_id=r.id)
                WHERE
                        l.id_contract=%s 
                        AND (l.permanent=True OR l.date_start <= %s and l.date_stop >= %s)
            order by r.sequence
            '''
            self.env.cr.execute(sql, (bulletin.employee_contract_id.id,
                                      bulletin.period_id.date_start, bulletin.period_id.date_start,
                                      ))
            rubriques = self.env.cr.dictfetchall()
            ir = salaire_base_worked
            anciennete = 0
            for rubrique in rubriques:
                if rubrique['categorie'] == 'majoration':
                    # actualisation montant jours chômés payés & jours congés payés
                    taux = rubrique['taux']
                    montant = rubrique['montant']
                    # Rubriques par heure: Heures sup
                    if rubrique['is_hourly']:
                        if bulletin.employee_contract_id.hour_salary > 0:
                            taux_horaire = bulletin.employee_contract_id.hour_salary
                        elif bulletin.employee_contract_id.monthly_hour_number > 0:
                            taux_horaire = bulletin.salaire_base / bulletin.employee_contract_id.monthly_hour_number or 1
                        else:
                            taux_horaire = bulletin.salaire_base / 191

                        # Montant=Nb heure
                        # Taux: Par exemple: Heures sup 25%:  25%--125%
                        montant = montant * taux_horaire * taux / 100

                    if rubrique['conge']:
                        taux = rubrique['taux']
                        montant = 0
                    if rubrique['absence'] and not rubrique['conge']:
                        taux = bulletin.working_days / 26
                        montant = rubrique['montant'] * taux
                        taux = taux * 100
                        absence += rubrique['montant'] - montant
                    if rubrique['anciennete'] and not rubrique['conge']:
                        anciennete += montant
                    # IR
                    if rubrique['ir'] and not rubrique['conge']:
                        if rubrique['plafond'] == 0:
                            ir += montant
                        elif montant <= rubrique['plafond']:
                            ir += montant
                        elif montant > rubrique['plafond']:
                            if rubrique['plafond']:
                                ir += montant - rubrique['plafond']
                            else:
                                ir += montant
                    # Cotisations
                    if not rubrique['imposable'] and not rubrique['conge']:
                        if rubrique['plafond'] == 0:
                            exoneration += montant
                        elif montant <= rubrique['plafond']:
                            exoneration += montant
                        elif montant > rubrique['plafond']:
                            exoneration += rubrique['plafond']

                    if rubrique['type'] == 'prime' and not rubrique['conge']:
                            prime += montant
                    elif rubrique['type'] == 'indemnite' and not rubrique['conge']:
                            indemnite += montant
                    elif rubrique['type'] == 'avantage' and not rubrique['conge']:
                            avantage += montant
                    majoration_line = {
                        'name': rubrique['name'],
                        'id_bulletin': id_bulletin,
                        'type': 'brute',
                        'base': rubrique['montant'],
                        'rate_employee': taux,
                        'subtotal_employee': montant,
                        'deductible': False,
                        'afficher': rubrique['afficher'],
                        # 'rubrique_id': rubrique['id'],
                        'credit_account_id': rubrique['credit_account_id'] or False,
                        'debit_account_id': rubrique['debit_account_id'] or False
                        }
                    self.env['hr.payroll_ma.bulletin.line'].create(majoration_line)


            #Ancienneté

            taux_anciennete = self.calc_seniority(self.employee_id.date, self.date_end) / 100
            prime_anciennete = (salaire_base_worked + anciennete) * taux_anciennete
            if taux_anciennete:
                anciennete_line = {
                    'name': 'Prime anciennete',
                    'id_bulletin': id_bulletin,
                    'type': 'brute',
                    'base': (salaire_base_worked + anciennete),
                    'rate_employee': taux_anciennete,
                    'subtotal_employee': prime_anciennete,
                    'deductible': False,
                    }
                self.env['hr.payroll_ma.bulletin.line'].create(anciennete_line)
            #Cotisations
            salaire_brute = salaire_base_worked + prime + indemnite + avantage + prime_anciennete
            salaire_brute_imposable = salaire_brute-exoneration
            cotisations = bulletin.employee_contract_id.cotisation.cotisation_ids
            base = 0
            if bulletin.employee_id.affilie:
                for cot in cotisations:
                    if cot.plafonee and salaire_brute_imposable >= cot.plafond:
                        base = cot.plafond
                    else:
                        base = salaire_brute_imposable
                    cotisation_line = {
                        'name': cot.name,
                        'id_bulletin': id_bulletin,
                        'type': 'cotisation',
                        'base': base,
                        'rate_employee': cot.tauxsalarial,
                        'rate_employer': cot.tauxpatronal,
                        'subtotal_employee': base*cot.tauxsalarial/100,
                        'subtotal_employer': base*cot.tauxpatronal/100,
                        'credit_account_id': cot.credit_account_id.id,
                        'debit_account_id': cot.debit_account_id.id,
                        'deductible': True,
                    }
                    cotisations_employee += base*cot.tauxsalarial/100
                    cotisations_employer += base*cot.tauxpatronal/100
                    self.env['hr.payroll_ma.bulletin.line'].create(cotisation_line)

            # Impot sur le revenu
            res = rec.get_ir(ir+prime_anciennete, cotisations_employee, logement)
            if not res['ir_net'] == 0:
                ir_line = {
                    'name': 'Impot sur le revenu',
                    'id_bulletin': id_bulletin,
                    'type': 'cotisation',
                    'base': res['salaire_net_imposable'],
                    'rate_employee': res['taux'],
                    'subtotal_employee': res['ir_net'],
                    'credit_account_id': res['credit_account_id'],
                    'debit_account_id': res['credit_account_id'],
                    'deductible': True,
                        }
                self.env['hr.payroll_ma.bulletin.line'].create(ir_line)

            # Rubriques Deduction add compte #Nait
            for rubrique in rubriques:
                if rubrique['categorie'] == 'deduction':
                        deduction += rubrique['montant']
                        deduction_line = {
                            'name': rubrique['name'],
                            'id_bulletin': id_bulletin,
                            'type': 'retenu',
                            'base': rubrique['montant'],
                            'rate_employee': 100,
                            'subtotal_employee': rubrique['montant'],
                            'deductible': True,
                            'afficher': rubrique['afficher'],
                            'credit_account_id': rubrique['credit_account_id'] or False,
                            'debit_account_id': rubrique['debit_account_id'] or False
                       }
                        self.env['hr.payroll_ma.bulletin.line'].create(deduction_line)
            salaire_net = salaire_brute - res['ir_net'] - cotisations_employee

            salaire_net_a_payer = salaire_brute - deduction - res['ir_net'] - cotisations_employee

            # Arrondi
            if dictionnaire['arrondi']:
                arrondi = 1-(round(salaire_net_a_payer, 2)-int(salaire_net_a_payer))
                if arrondi != 1:
                    diff = salaire_net_a_payer-int(salaire_net_a_payer)
                    arrondi = 1-(salaire_net_a_payer-int(salaire_net_a_payer))

                    if diff < 0.5:
                        arrondi = diff*-1
                    else:
                        arrondi = 1-diff

                    arrondi = 1-(salaire_net_a_payer-int(salaire_net_a_payer))

                    salaire_net_a_payer += arrondi
                    arrondi_line = {
                        'name': 'Arrondi',
                        'id_bulletin': id_bulletin,
                        'type': 'retenu',
                        'base': arrondi,
                        'rate_employee': 100,
                        'subtotal_employee': arrondi,
                        'deductible': True,
                               }
                    self.env['hr.payroll_ma.bulletin.line'].create(arrondi_line)
                else:
                    arrondi = 0

            rec.salaire = salaire_base
            rec.salaire_brute = salaire_brute
            rec.salaire_brute_imposable = salaire_brute_imposable
            rec.salaire_net = salaire_net
            rec.salaire_net_a_payer = salaire_net_a_payer
            # rec.salaire_net_imposable = res['salaire_net_imposable']
            rec.cotisations_employee = cotisations_employee
            rec.cotisations_employer = cotisations_employer
            rec.igr = res['ir_net']
            rec.prime = prime
            rec.indemnite = indemnite
            rec.avantage = avantage
            rec.deduction = deduction
            rec.prime_anciennete = prime_anciennete
            rec.exoneration = exoneration
            rec.absence = absence
            rec.frais_pro = res['frais_pro']
            rec.personnes = res['personnes']
            rec.arrondi = arrondi
            rec.logement = bulletin.employee_id.logement


# Rubrique
class HrRubrique(models.Model):
    _name = "hr.payroll_ma.rubrique"
    _description = "rubrique"

    name = fields.Char(string='Nom', required="True")
    code = fields.Char(string='Code', required=False, readonly=False)
    categorie = fields.Selection(selection=(('majoration', 'Majoration'),
                                            ('deduction', 'Deduction')), string=u'Catégorie', default='majoration')
    sequence = fields.Integer('Sequence', help=u"Ordre d'affichage dans le bulletin de paie", default=1)
    type = fields.Selection(selection=(('prime', 'Prime'),
                                       ('indemnite', u'Indemnité'),
                                       ('avantage', 'Avantage')), string='Type', default='prime')
    plafond = fields.Float(string=u'Plafond exonéré', default=0.0)
    formule = fields.Char(string='Formule', required=False, help='''
                    Pour les rubriques de type majoration, on utilise les variables suivantes :
                    salaire_base : Salaire de base
                    hour_base : Salaire horaire
                    normal_hours : Les heures normales
                    working_days : Jours travaillés (imposable)
        ''')
    imposable = fields.Boolean(string='Imposable', default=False)
    afficher = fields.Boolean(string='Afficher', help='Afficher cette rubrique sur le bulletin de paie', default=True)
    ir = fields.Boolean(string='IR', required=False)
    anciennete = fields.Boolean(string=u'Ancienneté')
    absence = fields.Boolean(string='Absence')
    conge = fields.Boolean(string=u'Congé')
    note = fields.Text(string='Commentaire')
    credit_account_id = fields.Many2one('account.account', string=u'Compte de crédit')
    debit_account_id = fields.Many2one('account.account', string=u'Compte de débit')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id,
                                 string='Société', readonly=True, copy=False)
    is_hourly = fields.Boolean(u'Par Heure?', default=False)
    pourcentage = fields.Float(u'Pourcentage')

    heures_sup = fields.Selection((('25', '25%'), ('50', '50%'),
                                   ('100', '100%')), string='Valeur heures sup')
    jrs_conge_paye = fields.Boolean('Jour congé payé?')


# Classe : Ligne rubrique
class HrLigneRubrique(models.Model):
    _name = "hr.payroll_ma.ligne_rubrique"
    _description = "Ligne Rubrique"
    _order = 'date_start'

    @api.multi
    def _sel_rubrique(self, cr, uid, context=None):
        for rec in self:
            obj = self.env['hr.payroll_ma.rubrique']
            res = obj.search([])
            res = [(r.id, r.name) for r in res]
            return res

    rubrique_id = fields.Many2one('hr.payroll_ma.rubrique', string='Rubrique', selection=_sel_rubrique)
    id_contract = fields.Many2one('hr.contract', string=u'Contrat', ondelete='cascade')
    montant = fields.Float(string='Montant')
    taux = fields.Float(string='Taux')
    period_id = fields.Many2one('date.range', domain="[('type_id.fiscal_period','=',True)]", string=u'Période')
    permanent = fields.Boolean(string='Rubrique Permanente')
    date_start = fields.Date(string=u'Date début')
    date_stop = fields.Date(string='Date fin')
    note = fields.Text(string='Commentaire')

    @api.multi
    @api.constrains('date_stop')
    def _check_date(self):
        for obj in self:
            if obj.date_start > obj.date_stop:
                raise ValidationError(u'La Date début doit être inférieur à la date de fin')
            return True

    @api.multi
    @api.onchange('rubrique_id')
    def onchange_rubrique_id(self):
        for rec in self:
            if rec.rubrique_id.is_hourly:
                rec.taux = rec.rubrique_id.pourcentage

    @api.onchange('period_id')
    def onchange_period_id(self):
        self.date_start = self.period_id.date_start
        self.date_stop = self.period_id.date_end


class HrPayrollMaBulletinLine(models.Model):
    _name = "hr.payroll_ma.bulletin.line"
    _description = "Ligne de salaire"

    name = fields.Char(string='Description', required=True)
    id_bulletin = fields.Many2one('hr.payroll_ma.bulletin', string='Bulletin', ondelete='cascade')
    type = fields.Selection(selection=(('other', 'Autre'),
                                       ('retenu', 'Retenue'),
                                       ('cotisation', 'Cotisation'),
                                       ('brute', 'Salaire brut')), string='Type')
    credit_account_id = fields.Many2one('account.account', string=u'Compte crédit')
    debit_account_id = fields.Many2one('account.account', string=u'Compte Débit')
    base = fields.Float(string='Base', required=True, digits=(16, 2))
    subtotal_employee = fields.Float(string=u'Montant Employé', digits=(16, 2))
    subtotal_employer = fields.Float(string='Montant Employeur', digits=(16, 2))
    rate_employee = fields.Float(string=u'Taux Employé', digits=(16, 2))
    rate_employer = fields.Float(string='Taux Employeur', digits=(16, 2))
    note = fields.Text(string='Notes')
    deductible = fields.Boolean(string=u'Déductible', default=False)
    afficher = fields.Boolean(string='Afficher', default=True)
    # rubrique_id = fields.Many2one('hr.payroll_ma.rubrique', string='Rubrique')
