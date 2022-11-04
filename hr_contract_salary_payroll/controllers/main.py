# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time

from odoo import _
from odoo.addons.hr_contract_salary.controllers import main
from odoo.http import route, request
from odoo.tools.float_utils import float_compare


class HrContractSalary(main.HrContractSalary):

    def _get_new_contract_values(self, contract, employee, advantages):
        contract_vals = super()._get_new_contract_values(contract, employee, advantages)
        if contract.wage_type == 'hourly':
            contract_vals['hourly_wage'] = contract.hourly_wage
        return contract_vals

    def _generate_payslip(self, new_contract):
        return request.env['hr.payslip'].sudo().create({
            'employee_id': new_contract.employee_id.id,
            'contract_id': new_contract.id,
            'struct_id': new_contract.structure_type_id.default_struct_id.id,
            'company_id': new_contract.employee_id.company_id.id,
            'name': 'Payslip Simulation',
            'date_from': request.env['hr.payslip'].default_get(['date_from'])['date_from'],
        })

    def _get_payslip_line_values(self, payslip, codes):
        return payslip._get_line_values(codes)

    def _get_compute_results(self, new_contract):
        result = super()._get_compute_results(new_contract)

        # generate a payslip corresponding to only this contract
        payslip = self._generate_payslip(new_contract)

        # For hourly wage contracts generate the worked_days_line_ids manually
        if new_contract.wage_type == 'hourly':
            work_days_data = new_contract.employee_id._get_work_days_data_batch(
                datetime.combine(payslip.date_from, time.min), datetime.combine(payslip.date_to, time.max),
                compute_leaves=False, calendar=new_contract.resource_calendar_id,
            )[new_contract.employee_id.id]
            payslip.worked_days_line_ids = request.env['hr.payslip.worked_days'].with_context(salary_simulation=True).sudo().create({
                'payslip_id': payslip.id,
                'work_entry_type_id': new_contract._get_default_work_entry_type().id,
                'number_of_days': work_days_data.get('days', 0),
                'number_of_hours': work_days_data.get('hours', 0),
            })

        payslip.with_context(
            salary_simulation=True,
            origin_contract_id=new_contract.env.context['origin_contract_id'],
            lang=None
        ).compute_sheet()

        result['payslip_lines'] = [(
            line.name,
            abs(round(line.total, 2)),
            line.code,
            'no_sign' if line.code in ['BASIC', 'SALARY', 'GROSS', 'NET'] else float_compare(line.total, 0, precision_digits=2)
        ) for line in payslip.line_ids.filtered(lambda l: l.appears_on_payslip)]
        # Allowed company ids might not be filled or request.env.user.company_ids might be wrong
        # since we are in route context, force the company to make sure we load everything
        resume_lines = request.env['hr.contract.salary.resume'].sudo().with_company(new_contract.company_id).search([
            '|',
            ('structure_type_id', '=', False),
            ('structure_type_id', '=', new_contract.structure_type_id.id),
            ('value_type', 'in', ['payslip', 'monthly_total'])])
        monthly_total = 0
        monthly_total_lines = resume_lines.filtered(lambda l: l.value_type == 'monthly_total')

        # new categories could be introduced at this step
        # recreate resume_categories
        resume_categories = request.env['hr.contract.salary.resume'].sudo().with_company(new_contract.company_id).search([
            '|', '&', '|',
                    ('structure_type_id', '=', False),
                    ('structure_type_id', '=', new_contract.structure_type_id.id),
                ('value_type', 'in', ['fixed', 'contract', 'monthly_total', 'sum']),
            ('id', 'in', resume_lines.ids)]).category_id
        result['resume_categories'] = [c.name for c in sorted(resume_categories, key=lambda x: x.sequence)]

        all_codes = (resume_lines - monthly_total_lines).mapped('code')
        line_values = self._get_payslip_line_values(payslip, all_codes) if all_codes else False

        for resume_line in resume_lines - monthly_total_lines:
            value = round(line_values[resume_line.code][payslip.id]['total'], 2)
            resume_explanation = False
            if resume_line.code == 'GROSS' and new_contract.wage_type == 'hourly':
                resume_explanation = _('This is the gross calculated for the current month with a total of %s hours.', work_days_data.get('hours', 0))
            result['resume_lines_mapped'][resume_line.category_id.name][resume_line.code] = (resume_line.name, value, new_contract.company_id.currency_id.symbol, resume_explanation)
            if resume_line.impacts_monthly_total:
                monthly_total += value / 12.0 if resume_line.category_id.periodicity == 'yearly' else value

        for resume_line in monthly_total_lines:
            super_line = result['resume_lines_mapped'][resume_line.category_id.name][resume_line.code]
            new_value = (super_line[0], round(super_line[1] + float(monthly_total), 2), super_line[2], False)
            result['resume_lines_mapped'][resume_line.category_id.name][resume_line.code] = new_value
        return result
