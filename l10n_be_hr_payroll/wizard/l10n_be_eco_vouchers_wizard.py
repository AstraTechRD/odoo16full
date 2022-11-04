# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nBeEcoVouchersWizard(models.TransientModel):
    _name = 'l10n.be.eco.vouchers.wizard'
    _description = 'Eco-Vouchers Wizard'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    reference_year = fields.Integer(default=lambda self: fields.Date.today().year)
    reference_period = fields.Char(compute='_compute_reference_period')
    line_ids = fields.One2many(
        'l10n.be.eco.vouchers.line.wizard', 'wizard_id',
        compute='_compute_line_ids', store=True, readonly=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    @api.depends('reference_year')
    def _compute_reference_period(self):
        for wizard in self:
            wizard.reference_period = _('The reference period is from the 1st of June %s to the 31th of May %s', wizard.reference_year -1, wizard.reference_year)

    @api.depends('reference_year')
    def _compute_line_ids(self):
        # The following maximum amounts, determined on the basis of the weekly working time, are
        # granted to workers with a full reference period:

        # Weekly working time: Annual amount granted
        # - From a 4/5 th time: 250 €
        # - From a 3/5 th time: 200 €
        # - From a ½ time: 125 €
        # - Less than ½ time: 100 €
        amount_from_rate = [
            (50, 100),
            (60, 125),
            (80, 200),
            (101, 250),
        ]

        # In the event of a change in working time during the reference period, the calculation is
        # carried out on a pro rata basis for each period.

        # For example: A worker is employed part-time from 01/06 to 31/12 of the preceding year and
        # full-time from 01/01 to 31/05 of the year of payment.
        # The total amount to be granted is calculated as follows:
        # € 125 x 7/12 + € 250 x 5/12 = € 177.07
        unpaid_work_entry_types = self.env.ref(
            'l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary'
        ).unpaid_work_entry_type_ids.filtered(lambda wet: wet.code not in ['LEAVE210', 'LEAVE230', 'LEAVE250'])


        for wizard in self:
            date_from = date(wizard.reference_year - 1, 6, 1)
            date_to = date(wizard.reference_year, 5, 31)
            all_contracts = self.env['hr.employee']._get_all_contracts(date_from, date_to, ['open', 'close'])
            # Coming from out batch, restrict to out employees
            batch_specific = 'employee_ids' in self.env.context
            if batch_specific:
                all_contracts = all_contracts.filtered(lambda c: c.employee_id.id in self.env.context['employee_ids'])
            all_employees = all_contracts.mapped('employee_id')
            all_payslips = self.env['hr.payslip'].search([
                ('employee_id', 'in', all_employees.ids),
                ('company_id', '=', wizard.company_id.id),
                ('date_from', '>=', date_from + relativedelta(months=1)),
                ('date_to', '<=', date_to),
                ('state', 'in', ['done', 'paid', 'verify'] if batch_specific else ['done', 'paid'])
            ])
            # Remove out employees who already got their eco-vouchers during the year
            if not batch_specific:
                already_paid_payslips = all_payslips.filtered(
                    lambda p: 'ECOVOUCHERS' in p.input_line_ids.input_type_id.mapped('code'))
                already_paid_employees = already_paid_payslips.employee_id
                all_contracts = all_contracts.filtered(lambda c: c.employee_id not in already_paid_employees)
                all_employees -= already_paid_employees
                all_payslips = all_payslips.filtered(lambda p: p.employee_id not in already_paid_employees)

            employee_contracts = defaultdict(lambda: self.env['hr.contract'])
            for contract in all_contracts.filtered(lambda c: c.active and c.company_id == wizard.company_id):
                employee_contracts[contract.employee_id] |= contract

            result = [(5, 0, 0)]
            for employee in employee_contracts:
                occupations = employee_contracts[employee]._get_occupation_dates()
                # Contains a list of occupations dates (with the same work time rate)
                # [(hr.contract(4,), datetime.date(2021, 2, 1), datetime.date(2021, 12, 1))]
                # [(hr.contract(19, 20), datetime.date(2019, 1, 1), False)]
                total_amount = 0
                for contracts, occupation_from, occupation_to in occupations:
                    contract = contracts[0]
                    occupation_from = max(date_from, occupation_from)
                    if occupation_from.day < 7:
                        occupation_from = occupation_from + relativedelta(day=1)
                    occupation_to = min(date_to, occupation_to if occupation_to else date_to)
                    # So that 1/1/2020 to 28/02/2020 -> 2 months
                    occupation_to = occupation_to + relativedelta(days=1)
                    # Retrieve non assimilated absences
                    # In the event of an incomplete reference period, the amount to be granted is
                    # determined on the basis of actual and assimilated benefits. The following
                    # periods are assimilated:
                    # - The pre- and post-natal maternity leave,
                    # ‐ The first month of incapacity covered by a guaranteed salary as provided
                    #   for by the law of 03/07/1978 on employment contracts.
                    employee_payslips = all_payslips.filtered(
                        lambda p: p.employee_id == employee \
                                  and p.date_from >= occupation_from + relativedelta(day=1) \
                                  and p.date_to <= occupation_to + relativedelta(day=31))
                    employee_worked_days = employee_payslips.mapped('worked_days_line_ids').filtered(
                        lambda wd: wd.work_entry_type_id in unpaid_work_entry_types)
                    invalid_hours = sum(employee_worked_days.mapped('number_of_hours'))
                    hours_per_day = contract.resource_calendar_id.hours_per_day
                    invalid_days = math.ceil(invalid_hours / hours_per_day) if hours_per_day else 0
                    # Compute complete months
                    days = (occupation_to - occupation_from).days - invalid_days
                    work_time_rate = contract.resource_calendar_id.work_time_rate
                    for rate, amount in amount_from_rate:
                        if work_time_rate < rate:
                            total_amount += max(0, (days / 365.0) * amount)
                            break
                result.append((0, 0, {
                    'employee_id': employee.id,
                    'amount': min(250, total_amount),
                    'wizard_id': wizard.id,
                }))
            wizard.line_ids = result

    def action_export_xls(self):
        self.ensure_one()
        return {
            'name': 'Export Eco-Vouchers',
            'type': 'ir.actions.act_url',
            'url': '/export/ecovouchers/%s' % (self.id),
        }

    def generate_payslips(self):
        self.ensure_one()
        eco_voucher_type = self.env.ref('l10n_be_hr_payroll.cp200_employee_eco_vouchers')
        monthly_pay = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary')
        payslips = self.env['hr.payslip']
        for line in self.line_ids:
            payslip = self.env['hr.payslip'].search([
                ('employee_id', '=', line.employee_id.id),
                ('state', '=', 'verify'),
                ('struct_id', '=', monthly_pay.id),
            ], limit=1)
            if payslip:
                payslips |= payslip
                voucher_line = payslip.input_line_ids.filtered(lambda line: line.code == "ECOVOUCHERS")
                if voucher_line:
                    voucher_line[0].amount = line.amount
                else:
                    payslip.write({'input_line_ids': [(0, 0, {
                        'input_type_id': eco_voucher_type.id,
                        'amount': line.amount,
                    })]})
            else:
                payslip = self.env['hr.payslip'].create({
                    'name': _('Eco-Vouchers'),
                    'employee_id': line.employee_id.id,
                    'contract_id': line.employee_id.contract_id.id,
                    'struct_id': monthly_pay.id,
                    'worked_days_line_ids': [(5, 0, 0)],
                    'input_line_ids': [(0, 0, {
                        'input_type_id': eco_voucher_type.id,
                        'amount': line.amount,
                    })],
                    'payslip_run_id': self.env.context.get('batch_id', False),
                })
                payslips |= payslip
                payslip.with_context(no_paid_amount=True).compute_sheet()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll.action_view_hr_payslip_month_form")
        action.update({'domain': [('id', 'in', payslips.ids)]})
        return action

class L10nBeEcoVouchersLineWizard(models.TransientModel):
    _name = 'l10n.be.eco.vouchers.line.wizard'
    _description = 'Eco-Vouchers Wizard'

    wizard_id = fields.Many2one('l10n.be.eco.vouchers.wizard')
    employee_id = fields.Many2one('hr.employee', required=True)
    niss = fields.Char(string="NISS", related='employee_id.niss')
    amount = fields.Monetary()
    currency_id = fields.Many2one(related='wizard_id.currency_id')
