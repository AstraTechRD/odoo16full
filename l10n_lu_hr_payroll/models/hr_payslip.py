# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrEmployee(models.Model):
    _inherit = 'hr.payslip'

    def _get_base_local_dict(self):
        res = super()._get_base_local_dict()
        res.update({
            'compute_lux_tax': compute_lux_tax,
        })
        return res

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_lu_hr_payroll', [
                'data/hr_salary_rule_category_data.xml',
                'data/hr_payroll_structure_type_data.xml',
                'data/hr_payroll_structure_data.xml',
                'data/hr_rule_parameters_data.xml',
                'data/hr_salary_rule_data.xml',
            ])]

def compute_lux_tax(payslip, categories, worked_days, inputs):
    # Source: https://impotsdirects.public.lu/fr/baremes.html#Ex
    def _find_rate(x, rates):
        for low, high, rate, adjustment in rates:
            if low <= x <= high:
                return rate, adjustment
        return 0, 0

    employee = payslip.dict.employee_id
    taxable_amount = categories.TAXABLE
    # Round to the lower 5 euros multiple
    taxable_amount -= taxable_amount % 5

    tax_amount = 0.0

    if employee.l10n_lu_tax_classification:
        rates = payslip.rule_parameter('l10n_lu_withholding_taxes_%s' % (employee.l10n_lu_tax_classification))
        threshold, threshold_adjustment = payslip.rule_parameter('l10n_lu_withholding_taxes_threshhold_%s'  % (employee.l10n_lu_tax_classification))
    else:
        return 0.0

    rate, adjustment = _find_rate(taxable_amount, rates)
    tax_amount = taxable_amount * rate - adjustment
    tax_amount -= tax_amount % 0.10
    if taxable_amount <= threshold:
        tax_amount *= 1.07
    else:
        tax_amount += tax_amount * 0.09 - threshold_adjustment
    tax_amount -= tax_amount % 0.10

    if tax_amount < 1.00:
        return 0.0
    return - tax_amount
