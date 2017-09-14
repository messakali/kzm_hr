# encoding: utf-8

{
    'name': 'Paie marocaine - Les bases',
    'version': '4.0.0',
    'author': 'Karizma Conseil',
    'website': "http://www.karizma.ma",
    'category': 'Paie marocaine',
    'summary': 'Contrats, Cotisations, congés, heures supplémentaires',
    'description' : """
Paie marocaine - Les bases de la paie
=====================================

    """,
    'images': [],
    'depends': ['report_xlsx','kzm_base', 'hr_payroll_account', 'hr_timesheet_sheet', 'document', 'hr_attendance', 'account_fiscal_year','web_domain_field'],
    'data': [
        'views/l10n_ma_hr_payroll.xml',
        'security/groups.xml',
        'security/hr.xml',
        'security/employee.xml',
        'security/interfaces.xml',
        'security/rule.xml',
        'security/ir.model.access.csv',
        'workflow/rubrique_wkf.xml',
        'workflow/avance_wkf.xml',
        'workflow/avantage_wkf.xml',
#         'workflow/expense_wkf.xml',
        'workflow/saisie_wkf.xml',
        'workflow/payslip_wkf.xml',
        'workflow/voucher_wkf.xml',
        'workflow/common_report_wkf.xml',
        'workflow/holidays_wkf.xml',
        'workflow/account_wkf.xml',
        'data/cron.xml',
        'data/precision.xml',
        'data/scale.xml',
        'data/employee.xml',
        'data/contract_base.xml',
        'data/contract.xml',
        'data/partners.xml',
        'data/contribution.xml',
        'data/category.xml',
        'data/rule_salary.xml',
        'data/rule_prime.xml',
        'data/rule_brut.xml',
        'data/rule_deduction.xml',
        'data/rule_net.xml',
        'data/cotisation.xml',
        'data/working_hours.xml',
        'data/holidays_public.xml',
        'data/holidays.xml',
        'data/structure.xml',
        'data/sequence.xml',
        'data/avance.xml',
        'data/rubrique.xml',
        'data/avantage.xml',
        'data/dictionnary.xml',
        'data/drive.xml',
        'data/saisie.xml',
        'data/product.xml',
        'data/common_report.xml',
        'data/title.xml',
        'data/job.xml',
        'data/department.xml',
        'data/company.xml',
        'views/board.xml',
        'views/main.xml',
        'views/contract_base.xml',
        'views/contract.xml',
        'views/scale.xml',
        'views/cotisation.xml',
        'views/holidays_public.xml',
        'views/attendance.xml',
        'views/mass_attendance.xml',
        'views/holidays.xml',
        'views/company.xml',
        'views/rule.xml',
        'views/payslip.xml',
        'views/run.xml',
        'views/axe.xml',
        'views/contribution.xml',
        'views/rubrique.xml',
        'views/rubrique_line.xml',
        'views/avance.xml',
        'views/avance_line.xml',
        'views/avantage.xml',
        'views/avantage_line.xml',
        'views/requests.xml',
        'views/dictionnary.xml',
        'views/expense.xml',
        'views/timesheet.xml',
        'views/rule_category.xml',
        'views/commune.xml',
        'views/statistics.xml',
        'views/rotation.xml',
        'views/product.xml',
        'views/structure.xml',
        'views/job.xml',
        'views/saisie.xml',
        'views/saisie_line.xml',
        'views/qualification.xml',
        'views/task.xml',
        'views/voucher_order.xml',
        'views/common_report.xml',
        'views/title.xml',
        'views/accounting.xml',
        'views/kilometrage.xml',
        'views/mission.xml',
        'views/employee.xml',
        'wizard/run.xml',
        'wizard/rubrique_run.xml',
        'wizard/avance_run.xml',
        'wizard/avantage_run.xml',
        'wizard/salary_ledger.xml',
        'wizard/salary_declaration.xml',
        'wizard/contract.xml',
        'wizard/export_import_csv.xml',
        'wizard/rotation.xml',
        'wizard/payslip.xml',
        'wizard/register.xml',
        'wizard/cotisation.xml',
        'report/report_salary_ledger.xml',
        'report/report_salary_declaration.xml',
        'report/report_cnss_declaration.xml',
        'report/report_anciennete.xml',
        'report/report_paye_journal.xml',
        'report/report_ir_declaration.xml',
        'report/report_cimr_declaration.xml',
        'report/report_cs_declaration.xml',
        'report/report_voucher_order.xml',
        'report/report_slip.xml',
        'report/report_contract.xml',
        'report/report_register.xml',
        'report/report_mutuelle_declaration.xml',
        'report/report_cotisation.xml',
        'report/report.xml',
    ],
    "qweb": [

    ],
    'demo': [

    ],
    'test': [

    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
