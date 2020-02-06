# -*- coding: utf-8 -*-

{
    "name": "Gestion de la paie marocaine sous Odoo",
    "version": "11.0",
    "author": "KARIZMA CONSEIL",
    "website": "https://karizma-conseil.com",
    "category": "HR",
    "depends": ["base", "hr", "hr_contract","account", 'kzm_hr_contract_type'],
    "description": u"""Gestion de la paie marocaine sous Odoo""",
    "data": [
        "data/rubriques.xml",
        "data/employee_data.xml",
        "security/hr_payroll_ma_security.xml",
        "security/ir.model.access.csv",
        "wizards/hours_import.xml",
        "wizards/import_rub.xml",
        "views/config.xml",
        "views/hr_view.xml",
        "views/hr_payroll_ma_view.xml",
        "views/hr_payroll_ma_sequence.xml",
        "views/hr_payroll_ma_data.xml",
        "views/res_config_setting.xml",
        "report/reports_view.xml",
        "report/bulletin_paie.xml",
        ],
    'installable' : True,
}