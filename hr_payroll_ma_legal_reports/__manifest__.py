# -*- coding: utf-8 -*-

{
    'name': 'États Paie légaux Maroc',
    'version': '12.0',
    'category': 'HR',
    'complexity': "normal",
    'description': """
            Etats legaux Maroc : Journal de paie, Bulletin de paie, Bordereau de virement, Etat CNSS, Bordereau paiement CNSS""",
    'author': 'KARIZMA CONSEIL',
    'website': 'https://karizma-conseil.com',
    'images': [],
    'depends': ['hr_payroll_ma'],
    'data': [
             'views/custom_bulletin_form_view.xml',
             'views/custom_payroll_parametres_view.xml',
             'report/reports_header_view.xml',
             'report/reports_view.xml',
             'report/journal_paie.xml',
             'report/bordereau_virement.xml',
             'report/etat_cnss.xml',
             'report/etat_igr.xml',
             'report/bordereau_paiement_cnss.xml',
            ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
}

