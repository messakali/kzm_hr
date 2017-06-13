# -*- coding: utf-8 -*-

import time
from odoo import models
from odoo.report import report_sxw
import re
from odoo.tools.safe_eval import safe_eval as eval


class warning(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(warning, self).__init__(
            cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'rendred_template': self._get_formatted_template,
        })

    def _get_formatted_template(self, w):
        payload = w.template_id.template.strip()
        v = re.findall(r'(\$\{\s.+\s\})', payload)
        v += re.findall(r'(\$\{.+\})', payload)
        v += re.findall(r'(\$\{[\w\s.]+\})', payload)
        v = list(set(v))
        employee = w.employee_id
        contract_id = self.env['hr.contract'].search([
            ('employee_id', '=', employee.id), ('is_contract_valid_by_context', '=', w.action_date)])
        contract = contract_id and self.env['hr.contract'].browse(contract_id[0]) or False
        company = contract and contract.company_id or employee.company_id
        for element in v:
            localdict = {
                'object': w,
                'contract': contract,
                'employee': employee,
                'company': company,
            }
            try:
                m = eval(
                    element[2:-1].strip(), localdict, mode='eval', nocopy=True)
                payload = payload.replace(element, m)
            except:
                pass

        return payload


class report_warningqweb(models.AbstractModel):
    _name = 'report.l10n_ma_hr_payroll.report_warning'
    _inherit = 'report.abstract_report'
    _template = 'l10n_ma_hr_payroll.report_warning'
    _wrapped_report_class = warning
