# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.http import request
from odoo.exceptions import ValidationError


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, company):
        """
        Override to configure payroll accounting data as well as accounting data.
        """
        res = super()._load(company)
        if self == self.env.ref('l10n_be.l10nbe_chart_template'):
            self._configure_payroll_account_data(company)
        return res

    def _configure_payroll_account_data(self, companies):
        accounts_codes = [
            '453000',  # Withholding taxes, IP Deduction
            '454000',  # ONSS (Employee, Employer, Miscellaneous)
            '455000',  # Due amount (net), Meal Vouchers
            '620200',  # Remuneration, Representation Fees; Private Car
            '621000',  # ONSS Employer (debit)
            '643000',  # IP
        ]
        belgian_structures = self.env['hr.payroll.structure'].search([('country_id.code', '=', "BE")])
        for company in companies:
            self = self.with_company(company)

            accounts = {}
            for code in accounts_codes:
                account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '%s%%' % code)], limit=1)
                if not account:
                    raise ValidationError(_('No existing account for code %s', code))
                accounts[code] = account

            journal = self.env['account.journal'].search([
                ('code', '=', 'SLR'),
                ('name', '=', 'Salaries'),
                ('company_id', '=', company.id)])

            if journal:
                if not journal.default_account_id:
                    journal.default_account_id = accounts['620200'].id
            else:
                journal = self.env['account.journal'].create({
                    'name': 'Salaries',
                    'code': 'SLR',
                    'type': 'general',
                    'company_id': company.id,
                    'default_account_id': accounts['620200'].id,
                })

                self.env['ir.property']._set_multi(
                    "journal_id",
                    "hr.payroll.structure",
                    {structure.id: journal for structure in belgian_structures},
                )

            # ================================================ #
            #              CP200: 13th month                   #
            # ================================================ #
            salary_rule_domain = [
                ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month').id),
                ('code', '=', 'BASIC')
            ]
            self.env['hr.salary.rule'].search(salary_rule_domain).write({'account_credit': accounts['455000'].id})

            self.env.ref('l10n_be_hr_payroll.cp200_employees_thirteen_month_onss_rule').write({
                'account_credit': accounts['454000'].id
            })

            self.env.ref('l10n_be_hr_payroll.cp200_employees_thirteen_month_p_p').write({
                'account_credit': accounts['453000'].id
            })

            self.env.ref('l10n_be_hr_payroll.cp200_employees_thirteen_month_mis_ex_onss').write({
                'account_debit': accounts['454000'].id  # Note: this is a credit, but the amount is negative
            })

            self.env['hr.salary.rule'].search([
                ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month').id),
                ('code', '=', 'NET')
            ]).write({
                'account_credit': accounts['455000'].id
            })

            # ================================================ #
            #              CP200: Double Holidays              #
            # ================================================ #
            self.env.ref('l10n_be_hr_payroll.cp200_employees_double_holiday_onss_rule').write({
                'account_credit': accounts['454000'].id
            })

            self.env.ref('l10n_be_hr_payroll.cp200_employees_double_holiday_pay_p_p').write({
                'account_credit': accounts['453000'].id
            })

            self.env['hr.salary.rule'].search([
                ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id),
                ('code', '=', 'NET')
            ]).write({
                'account_credit': accounts['455000'].id
            })

            # ================================================ #
            #         CP200: Employees Monthly Pay             #
            # ================================================ #

            # Remunerations
            self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_remuneration').write({
                'account_debit': accounts['620200'].id
            })

            # IP
            self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_ip').write({
                'account_debit': accounts['643000'].id,
            })

            # ONSS (Onss - employment bonus)
            self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_onss_total').write({
                'account_credit': accounts['454000'].id,
            })

            # Private car reimbursement
            self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_private_car').write({
                'account_debit': accounts['620200'].id,
            })

            # Total withholding taxes
            self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_withholding_taxes_total').write({
                'account_credit': accounts['453000'].id,
            })

            # Special Social Cotisation (MISC ONSS)
            self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_mis_ex_onss').write({
                'account_debit': accounts['454000'].id,  # Note: this is a credit, but the amount is negative
            })

            # Representation Fees
            self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_representation_fees').write({
                'account_debit': accounts['620200'].id,
            })

            # IP Deduction
            self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_ip_deduction').write({
                'account_debit': accounts['453000'].id,  # Note: This is a credit, but the amount is negative
            })

            # Meal vouchers
            self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_ch_worker').write({
                'account_debit': accounts['455000'].id,  # Note: this is a credit, but the amount is negative
            })

            # Owed Remunerations (NET)
            self.env['hr.salary.rule'].search([
                ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id),
                ('code', '=', 'NET')
            ]).write({
                'account_credit': accounts['455000'].id
            })

            # ONSS Employer
            self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_onss_employer').write({
                'account_debit': accounts['621000'].id,
                'account_credit': accounts['454000'].id,
            })

            # ================================================ #
            #              CP200: Termination Fees             #
            # ================================================ #

            # Remuneration
            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_fees_remuneration').write({
                'account_debit': accounts['620200'].id
            })

            # ONSS (Onss - employment bonus)
            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_fees_onss_total').write({
                'account_credit': accounts['454000'].id,
            })

            # Total withholding taxes
            self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_withholding_taxes_total').write({
                'account_credit': accounts['453000'].id,
            })

            # Owed Remunerations (NET)
            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_fees_withholding_taxes_total').write({
                'account_credit': accounts['455000'].id
            })

            # ONSS Employer
            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_fees_termination_ONSS').write({
                'account_debit': accounts['621000'].id,
                'account_credit': accounts['454000'].id,
            })

            # ================================================ #
            #              CP200: Termination Holidays N       #
            # ================================================ #

            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n_total_n').write({
                'account_credit': accounts['455000'].id,
            })

            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n_rules_onss_termination').write({
                'account_credit': accounts['454000'].id,
            })

            self.env.ref(
                'l10n_be_hr_payroll.cp200_employees_termination_n_rules_special_contribution_termination').write({
                'account_credit': accounts['454000'].id,
            })

            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n_rules_professional_tax_termination').write({
                'account_credit': accounts['453000'].id,
            })

            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n_pay_net_termination').write({
                'account_debit': accounts['455000'].id,
            })

            # ================================================ #
            #        CP200: Termination Holidays N-1           #
            # ================================================ #

            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n1_total_n').write({
                'account_credit': accounts['455000'].id,
            })

            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n1_rules_onss_termination').write({
                'account_credit': accounts['454000'].id,
            })

            self.env.ref(
                'l10n_be_hr_payroll.cp200_employees_termination_n1_rules_special_contribution_termination').write({
                'account_credit': accounts['454000'].id,
            })
            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n1_rules_professional_tax_termination').write({
                'account_credit': accounts['453000'].id,
            })
            self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n1_pay_net_termination').write({
                'account_debit': accounts['455000'].id,
            })

    def _configure_additional_structures(self, accounts, journal):
        # Could be overridden to add a specific structure without having to
        # recompute the accounts and the journal.
        return
