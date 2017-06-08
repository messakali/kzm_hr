# encoding: utf-8

from odoo import  _

LEAVE = 'Leaves'
HS = 'hs'
RUBRIQUE = 'rubrique'
AVANCE = 'avance'
AVANTAGE = 'avantage'
EXPENSE_TO_PAY = 'expense_to_pay'  # Field in hr.saisie.line
EXPENSE_PAID = 'expense_paid'  # Field in hr.saisie.line
LEAVE_PAID = 'leave_paid'  # Field in hr.saisie.line
FIX_LEAVE_PAID = 'fix_leave_paid'  # Field in hr.saisie.line
CV = 'cv'  # Field in hr.saisie.line
KILOMETRAGE = 'kilometrage'  # Field in hr.saisie.line

KEYS = [LEAVE, HS, RUBRIQUE, AVANCE, AVANTAGE]

FIXED_DAYS = 'fixed_days'
FIXED_HOURS = 'fixed_hours'
WORKED_DAYS = 'worked_days'
WORKED_HOURS = 'worked_hours'
ATTENDED_DAYS = 'attended_days'
ATTENDED_HOURS = 'attended_hours'
TIMESHEET_DAYS = 'timesheet_days'
TIMESHEET_HOURS = 'timesheet_hours'

BASED_ON = {
    FIXED_DAYS: _('Salaire fixe (en jours)'),
    FIXED_HOURS: _('Salaire fixe (en heures)'),
    WORKED_DAYS: _('Jours travailles'),
    WORKED_HOURS: _('Heures travaillees'),
    ATTENDED_DAYS: _('Pointage journalier'),
    ATTENDED_HOURS: _('Pointage horaire'),
    TIMESHEET_HOURS: _('Feuille de temps (en jours)'),
    TIMESHEET_DAYS: _('Feuille de temps (en heures)'),
}

BASED_ON_SELECTION = [
    (FIXED_DAYS, BASED_ON[FIXED_DAYS]),
    (FIXED_HOURS, BASED_ON[FIXED_HOURS]),
    (WORKED_DAYS, BASED_ON[WORKED_DAYS]),
    (WORKED_HOURS, BASED_ON[WORKED_HOURS]),
    (ATTENDED_DAYS, BASED_ON[ATTENDED_DAYS]),
    (ATTENDED_HOURS, BASED_ON[ATTENDED_HOURS]),
    (TIMESHEET_DAYS, BASED_ON[TIMESHEET_DAYS]),
    (TIMESHEET_HOURS, BASED_ON[TIMESHEET_HOURS]),
]

SALAIRE_PAR_JOUR = 'SALAIRE_PAR_JOUR'
SALAIRE_PAR_HEURE = 'SALAIRE_PAR_HEURE'



NORMAL = 'normal'
ATTENDANCE = 'attendance'
ATTENDANCE_MAJ = 'ATTENDANCE'

ATTENDANCE_WITH_HOLIDAYS = 'ATTENDANCE_WITH_HOLIDAYS'
RESTE_CONGES_PAYES = 'RESTE_CONGES_PAYES'
CONGES_A_CONSOMMER = 'CONGES_A_CONSOMMER'
