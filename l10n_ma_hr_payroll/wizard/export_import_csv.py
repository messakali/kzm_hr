# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import base64
import tempfile
import codecs
import os
import csv
import time
import logging
logger = logging.getLogger(__name__)
_logger = logger

from odoo.addons.kzm_base.controllers.tools import remove_accent as ra
from odoo.addons.kzm_base.controllers.tools import to_float as tf
from odoo.addons.l10n_ma_hr_payroll.models.variables import *


ID = u"Immatriculation".upper()
NOM = u"Nom".upper()
PRENOM = u"Prenom".upper()
TYPE = u"Base de salaire".upper()
TYPE_DE_CONTRAT = u"Type de contrat".upper()
SALAIRE_FIXE = u"Salaire fixe".upper()
NBR_HJN = u"Heures/Jours Normal".upper()
T_HJ = u"Taux horaire/Journalier".upper()
NOTIFICATIONS = u"Notifications".upper()
LEAVE_PAID = u"Heures/Jours feries PAYES".upper()
EXPENSE_TO_PAY = u"Notes de frais a payer".upper()
EXPENSE_PAID = u"Notes de frais payees".upper()

FIELD_EXPENSE_TO_PAY = 'expense_to_pay'  # Field in hr.saisie.line
FIELD_EXPENSE_PAID = 'expense_paid'  # Field in hr.saisie.line
FIELD_LEAVE_PAID = 'leave_paid'  # Field in hr.saisie.line

CV = u"Puissance fiscale".upper()
KILOMETRAGE = u"Kilometrage".upper()

class hr_saisie_export(models.TransientModel):
    _name = 'hr.saisie.export'
    _description = 'Export CSV'

    run_id = fields.Many2one(
        'hr.saisie.run', string=u'Lot',  required=True, domain=[('state', '=', 'csv')])
    file = fields.Binary(string=u'Fichier', readonly=True,)
    name = fields.Char(string=u'Nom de fichier', size=64, readonly=True, )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Terminé'),
    ], string=u'État', default='draft',)

    @api.multi
    def retour(self):
        self.ensure_one()
        self.state = 'draft'
        action = self.env.ref(
            'l10n_ma_hr_payroll.hr_saisie_export_wizard_action').read()[0]
        action['res_id'] = self.id
        return action

    @api.multi
    def exporter(self):
        start_time = time.time()
        self.ensure_one()
        if not self.run_id.line_ids:
            raise UserError(_('Aucune ligne trouvé dans le lot'))
        filename = self.run_id.name.replace(
            '/', '_').replace(' ', '_') + '.csv'
        tmp_file = tempfile.NamedTemporaryFile(
            prefix='tmp_paie_', suffix='.csv')
        file_path = tmp_file.name
        tmp_file.close()
        buffer = codecs.open(file_path, "w+", "utf-8")

        HEADERS = [ID, NOM, PRENOM, TYPE_DE_CONTRAT, TYPE, SALAIRE_FIXE, NBR_HJN, T_HJ, LEAVE_PAID]
        for status in self.env['hr.holidays.status'].search([('export_ok', '=', True)]):
            HEADERS.append(unicode(status.code))
        for rubrique in self.env['hr.rubrique'].search([('export_ok', '=', True)]):
            HEADERS.append(unicode(rubrique.code))
        for avantage in self.env['hr.avantage'].search([('export_ok', '=', True)]):
            HEADERS.append(unicode(avantage.code))
        for avance in self.env['hr.avance'].search([('export_ok', '=', True)]):
            HEADERS.append(unicode(avance.code))
        #HEADERS += [EXPENSE_PAID, EXPENSE_TO_PAY, NOTIFICATIONS]
        HEADERS += [KILOMETRAGE, CV, EXPENSE_TO_PAY, NOTIFICATIONS]
        init_tab = {}
        for key in HEADERS:
            init_tab.update({key: 0})
        buffer.write(";".join(['"' + x + '"' for x in HEADERS]))
        i = 0
        for line in self.run_id.line_ids:
            i += 1
            employee = line.employee_id
            contract = line.contract_id
            tab = init_tab.copy()
            tab.update({
                ID: employee.otherid or u'',
                NOM: employee.nom,
                PRENOM: employee.prenom,
                TYPE: BASED_ON.get(contract.based_on, 'Autre'),
                TYPE_DE_CONTRAT: contract.type_id.name,
                SALAIRE_FIXE: contract.fixed_salary and contract.salary_net_effectif or 0.0,
                NBR_HJN: line.normal,
                T_HJ: line.rate,
                NOTIFICATIONS: line.notes,
                EXPENSE_TO_PAY: line.expense_to_pay,
                EXPENSE_PAID: line.expense_paid,
                LEAVE_PAID: line.leave_paid,
                CV: line.cv,
                KILOMETRAGE: line.kilometrage,
            })
            for leave in line.leave_ids:
                tab.update({leave.type_id.code: leave.value})
            for hs in line.hs_ids:
                tab.update({hs.type_id.code: hs.value})
            for rubrique in line.rubrique_ids:
                tab.update({rubrique.type_id.code: rubrique.value})
            for avantage in line.avantage_ids:
                tab.update({avantage.type_id.code: avantage.value})
            for avance in line.avance_ids:
                tab.update({avance.type_id.code: avance.value})
            buffer.write("\n")
            buffer.write(
                ";".join(['"' + unicode(tab.get(x, '')) + '"' for x in HEADERS]))
        buffer.close()
        buffer = codecs.open(file_path, "r", "utf-8")
        contents = buffer.read().encode('utf-8')
        os.unlink(file_path)

        self.run_id.message_post(
            _('Exportation réussie de fichier : %s') % (filename,), attachments=[(filename, contents)])
        self.write({
            'file': base64.encodestring(contents),
            'name': filename,
            'state': 'done',
        })

        action = self.env.ref(
            'l10n_ma_hr_payroll.hr_saisie_export_wizard_action').read()[0]
        action['res_id'] = self.id
        _logger.info('Meter saisie_run export_csv '.upper() +
                     "%s -> nbr : %s" % (time.time() - start_time, str(i), ))
        return action


class hr_saisie_import(models.TransientModel):
    _name = 'hr.saisie.import'
    _description = 'Import CSV'

    run_id = fields.Many2one('hr.saisie.run', string=u'Lot', domain=[
                             ('state', '=', 'csv')], required=True, )
    file = fields.Binary(string=u'Fichier',  required=True,)
    name = fields.Char(string=u'Nom de fichier', size=64,)

    @api.multi
    def import_csv(self):
        start_time = time.time()
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.write(base64.decodestring(self.file))
        tmp_file.close()
        file_path = tmp_file.name
        data = open(tmp_file.name, "rU")
        delimiter = ";"
        reader = csv.DictReader(data, dialect='excel', delimiter=delimiter)
        logger.info("Start importing CSV file")
        run = self.run_id
        immatriculations = run.line_ids.mapped('employee_id.otherid')
        nbr = 0
        for i, row in enumerate(reader):
            nbr += 1
            tmp_join = ''.join([row.get(ID, '').strip(), row.get(NOM, '').strip(), row.get(PRENOM, '').strip()])
            if not tmp_join:
                continue
            otherid = row.get(ID, False)
            if not otherid:
                msg = _(
                    'Le fichier CSV doit contenir les matricules internes de tous les employés, Ligne [%s]' % str(i + 1))
                run.message_post(msg)
                raise Warning(msg)
            employee = self.env['hr.employee'].search(
                [('otherid', '=', otherid)], limit=1)
            if not employee:
                msg = _('Employé introuvable, Matricule [%s], Employé [%s - %s]') % (
                    otherid, row.get(NOM, ''), row.get(PRENOM, ''))
                run.message_post(msg)
                raise Warning(msg)
            contract = self.env['hr.contract'].search([
                ('is_contract_valid_by_context', 'in', (self.run_id.date_start, self.run_id.date_end)),
                ('company_id', '=', self.run_id.company_id.id),
                ('employee_id', '=', employee.id),
            ], limit=1, order="date_start desc")
            if not contract:
                msg = _('Aucun contrat trouvé pour l\'employé avec matricule [%s] et nom [%s]') % (
                    otherid, employee.name)
                run.message_post(msg)
                raise Warning(msg)

            line = self.env['hr.saisie.line'].search([
                ('employee_id', '=', employee.id),
                ('contract_id', '=', contract.id),
                ('run_id', '=', run.id),
            ])
            if not line:
                msg = _('Employé introuvable dans le lot avec matricule [%s] et nom [%s]') % (
                    otherid, employee.name)
                run.message_post(msg)
                raise Warning(msg)
            data_row_csv = {
                'normal': tf(row.get(NBR_HJN, '0')),
                'notes': row.get(NOTIFICATIONS, ''),
                'cv': row.get(CV, 0),
                'kilometrage': row.get(KILOMETRAGE, 0),
            }
            if row.get(EXPENSE_PAID, False):
                data_row_csv.update(
                    {FIELD_EXPENSE_PAID: tf(row.get(EXPENSE_PAID, '0'))})
            if row.get(EXPENSE_TO_PAY, False):
                data_row_csv.update(
                    {FIELD_EXPENSE_TO_PAY: tf(row.get(EXPENSE_TO_PAY, '0'))})
            if row.get(LEAVE_PAID, False):
                data_row_csv.update(
                    {FIELD_LEAVE_PAID: tf(row.get(LEAVE_PAID, '0'))})
            line.write(data_row_csv)
            for status in self.env['hr.holidays.status'].with_context({'active_test': False, }).search([('is_hs', '=', False)]):
                if status.code in row.keys():
                    value = tf(row.get(status.code))
                    exists = self.env['hr.saisie.leave'].with_context({'active_test': False, }).search([
                        ('type_id', '=', status.id),
                        ('saisie_id', '=', line.id),
                    ])
                    if exists:
                        exists.value = value
                    else:
                        if value > 0:
                            self.env['hr.saisie.leave'].create({
                                'saisie_id': line.id,
                                'type_id': status.id,
                                'value': value,
                            })
            for status in self.env['hr.holidays.status'].with_context({'active_test': False, }).search([('is_hs', '=', True)]):
                if status.code in row.keys():
                    value = tf(row.get(status.code))
                    exists = self.env['hr.saisie.hs'].with_context({'active_test': False, }).search([
                        ('type_id', '=', status.id),
                        ('saisie_id', '=', line.id),
                    ])
                    if exists:
                        exists.value = value
                    else:
                        if value > 0:
                            self.env['hr.saisie.hs'].create({
                                'saisie_id': line.id,
                                'type_id': status.id,
                                'value': value,
                            })

            for rubrique in self.env['hr.rubrique'].with_context({'active_test': False, }).search([('auto_compute','=',False)]):
                if rubrique.code in row.keys():
                    value = tf(row.get(rubrique.code))
                    rubrique_limit = self.env['hr.rubrique.limit'].with_context({'active_test': False, }).search([
                        ('company_id', '=', run.company_id.id),
                        ('rubrique_id', '=', rubrique.id),
                    ])
                    if rubrique_limit and (value < rubrique_limit.amount_from or value > rubrique_limit.amount_to):
                        raise Warning(_('La rubrique [%s] a une limite entre [%s et %s]') % (
                            rubrique.name, rubrique_limit.amount_from, rubrique_limit.amount_to,))
                    exists = self.env['hr.saisie.rubrique'].with_context({'active_test': False, }).search([
                        ('type_id', '=', rubrique.id),
                        ('saisie_id', '=', line.id),
                    ])
                    if exists:
                        exists.value = value
                    else:
                        if value > 0:
                            self.env['hr.saisie.rubrique'].create({
                                'saisie_id': line.id,
                                'type_id': rubrique.id,
                                'value': value,
                            })
            for avantage in self.env['hr.avantage'].with_context({'active_test': False, }).search([]):
                if avantage.code in row.keys():
                    value = tf(row.get(avantage.code))
                    avantage_limit = self.env['hr.avantage.limit'].with_context({'active_test': False, }).search([
                        ('company_id', '=', run.company_id.id),
                        ('avantage_id', '=', avantage.id),
                    ])
                    if avantage_limit and (value < avantage_limit.amount_from or value > avantage_limit.amount_to):
                        raise Warning(_('L\'avantage [%s] a une limite entre [%s et %s]') % (
                            avantage.name, avantage_limit.amount_from, avantage_limit.amount_to,))

                    exists = self.env['hr.saisie.avantage'].with_context({'active_test': False, }).search([
                        ('type_id', '=', avantage.id),
                        ('saisie_id', '=', line.id),
                    ])
                    if exists:
                        exists.value = value
                    else:
                        if value > 0:
                            self.env['hr.saisie.avantage'].create({
                                'saisie_id': line.id,
                                'type_id': avantage.id,
                                'value': value,
                            })
            for avance in self.env['hr.avance'].with_context({'active_test': False, }).search([
                ('interest_rate', '=', 0),
                ('csv_erase', '=', True),
            ]):
                if avance.code in row.keys():
                    value = tf(row.get(avance.code))
                    avance_limit = self.env['hr.avance.limit'].with_context({'active_test': False, }).search([
                        ('company_id', '=', run.company_id.id),
                        ('avance_id', '=', avance.id),
                    ])
                    if avance_limit and (value < avance_limit.amount_from or value > avance_limit.amount_to):
                        raise Warning(_('L\'avance [%s] a une limite entre [%s et %s]') % (
                            avance.name, avance_limit.amount_from, avance_limit.amount_to,))
                    exists = self.env['hr.saisie.avance'].with_context({'active_test': False, }).search([
                        ('type_id', '=', avance.id),
                        ('saisie_id', '=', line.id),
                    ])
                    if exists:
                        exists.value = value
                    else:
                        if value > 0:
                            self.env['hr.saisie.avance'].create({
                                'saisie_id': line.id,
                                'type_id': avance.id,
                                'value': value,
                            })
            if otherid in immatriculations:
                immatriculations.remove(otherid)
            line.check_data()
        os.unlink(tmp_file.name)
        if immatriculations:
            raise Warning(
                _('Employé qui a comme matricule [%s] est introuvable dans le fichier') % ' - '.join(immatriculations))
        logger.info("End importing CSV file")
        run.csv_lock = True
        msg = _('Fichier est bien importé, le lot est verouillé')
        run.message_post(
            msg, attachments=[(self.name, base64.decodestring(self.file),), ])
        _logger.info('Meter saisie_run import_csv '.upper() +
                     "%s -> nbr : %s" % (time.time() - start_time, str(nbr), ))
