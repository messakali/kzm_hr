# -*- coding: utf-8 -*-

from odoo.osv import osv
from odoo.tools.translate import _

import time
import logging
_logger = logging.getLogger(__name__)

class hr_payslip_employees(osv.osv_memory):
    _inherit = 'hr.payslip.employees'

    def compute_sheet(self):
        start_time = time.time()
        emp_pool = self.env['hr.employee']
        contract_pool = self.env['hr.contract']
        slip_pool = self.env['hr.payslip']
        run_pool = self.env['hr.payslip.run']
        slip_ids = []
        data = self[0]
        run_data = {}
        if self._context and self._context.get('active_id', False):
            run_data = run_pool.browse([self._context['active_id']]).read([
                                     'date_start', 'date_end', 'credit_note'])[0]
        from_date = run_data.get('date_start', False)
        to_date = run_data.get('date_end', False)
        print from_date
        print to_date
        credit_note = run_data.get('credit_note', False)
        if not data['employee_ids']:
            raise osv.except_osv(
                _("Avertissment!"), _("Veuillez sélectionner des employés pour générer les bulletins de paie."))
        for emp in data['employee_ids']:
            slip_data = slip_pool.onchange_employee_id(
                from_date, to_date, emp.id, contract_id=False)
            contract = contract_pool.browse(
                slip_data['value'].get('contract_id', False))
            res = {
                'employee_id': emp.id,
                'name': slip_data['value'].get('name', False),
                'struct_id': slip_data['value'].get('struct_id', False),
                'contract_id': contract.id,
                'payslip_run_id': self._context.get('active_id', False),
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids', False)],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids', False)],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': credit_note,
                'company_id': slip_data['value'].get('company_id', False),
                'journal_id': contract.journal_id.id,
                'voucher_mode': contract.voucher_mode,
                'marital': slip_data['value'].get('marital', False),
                'wife_situation': slip_data['value'].get('wife_situation', False),
                'children': slip_data['value'].get('children', False),
                'department_id': slip_data['value'].get('department_id', False),
                'job_id': slip_data['value'].get('job_id', False),
                'hire_date': slip_data['value'].get('hire_date', False),
                'otherid': slip_data['value'].get('otherid', ''),
                'address_home': slip_data['value'].get('address_home', ''),
                'cnss_ok': slip_data['value'].get('cnss_ok', False),
                'cimr_ok': slip_data['value'].get('cimr_ok', False),
            }
            slip_ids.append(slip_pool.create(res))
        for slip in slip_ids:
            print slip
            slip.compute_sheet()
        _logger.info('Meter payslip_run compute_sheet '.upper() + "%s -> nbr: %s" % (time.time() - start_time, len(data['employee_ids']), ))
        return {'type': 'ir.actions.act_window_close'}
