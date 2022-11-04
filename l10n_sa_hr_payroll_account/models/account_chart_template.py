# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError

from odoo import models, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def load_payroll_accounts(self):
        """
        Override to configure payroll accounting data as well as accounting data.
        """
        if self == self.env.ref('l10n_sa.sa_chart_template_standard'):
            sa_companies = self.env['res.company'].search([('partner_id.country_id.code', '=', 'SA'), ('chart_template_id', '=', self.env.ref('l10n_sa.sa_chart_template_standard').id)])
            self._configure_payroll_account_data_saudi(sa_companies)

    def _configure_payroll_account_data_saudi(self, companies):
        accounts_codes = [
            '201002',  # Payables
            '201016',  # Accrued Others
            '202001',  # End of Service Provision
            '400003',  # Basic Salary
            '400004',  # Housing Allowance
            '400005',  # Transportation Allowance
            '400008',  # End of Service Indemnity
            '400010',  # Life insurance
            '400012',  # Staff Other Allowances
        ]
        ksa_structures = self.env['hr.payroll.structure'].search([('country_id.code', '=', "SA")])
        for company in companies:
            self = self.with_company(company)

            accounts = {}
            for code in accounts_codes:
                account = self.env['account.account'].search(
                    [('company_id', '=', company.id), ('code', 'like', '%s%%' % code)], limit=1)
                if not account:
                    raise ValidationError(_('No existing account for code %s', code))
                accounts[code] = account

            journal = self.env['account.journal'].search([
                ('code', '=', 'MISC'),
                ('name', '=', 'Miscellaneous Operations'),
                ('company_id', '=', company.id)])

            if not journal:
                journal = self.env['account.journal'].create({
                    'name': 'Miscellaneous Operations',
                    'code': 'MISC',
                    'type': 'general',
                    'company_id': company.id,
                })

            self.env['ir.property']._set_multi(
                "journal_id",
                "hr.payroll.structure",
                {structure.id: journal.id for structure in ksa_structures},
            )

            # ================================================ #
            #          KSA Employee Payroll Structure          #
            # ================================================ #
            self.env.ref('l10n_sa_hr_payroll.ksa_saudi_social_insurance_contribution').write(
                {"account_debit": accounts['400010'].id, 'account_credit': accounts['201016'].id})
            for employee_type in ['saudi', 'expat']:
                salary_rule_domain_basic = [
                    ('struct_id', '=', self.env.ref('l10n_sa_hr_payroll.ksa_%s_employee_payroll_structure' % employee_type).id),
                    ('code', '=', 'BASIC')
                ]
                self.env['hr.salary.rule'].search(salary_rule_domain_basic, limit=1).write({'account_debit': accounts['400003'].id})
                self.env.ref('l10n_sa_hr_payroll.ksa_%s_housing_allowance_salary_rule' % employee_type).write(
                    {"account_debit": accounts['400004'].id})
                self.env.ref('l10n_sa_hr_payroll.ksa_%s_transportation_allowance_salary_rule' % employee_type).write(
                    {"account_debit": accounts['400005'].id})
                self.env.ref('l10n_sa_hr_payroll.ksa_%s_other_allowances_salary_rule' % employee_type).write(
                    {"account_debit": accounts['400012'].id})
                self.env.ref('l10n_sa_hr_payroll.ksa_%s_end_of_service_salary_rule' % employee_type).write(
                    {"account_debit": accounts['202001'].id})
                self.env.ref('l10n_sa_hr_payroll.ksa_%s_end_of_service_provision_salary_rule' % employee_type).write(
                    {"account_debit": accounts['400008'].id, "account_credit": accounts['202001'].id})
                self.env.ref('l10n_sa_hr_payroll.ksa_%s_overtime' % employee_type).write(
                    {"account_debit": accounts['400012'].id})
                self.env.ref('l10n_sa_hr_payroll.ksa_%s_unpaid_leave' % employee_type).write(
                    {"account_credit": accounts['400003'].id})
                salary_rule_domain_net = [
                    ('struct_id', '=', self.env.ref('l10n_sa_hr_payroll.ksa_%s_employee_payroll_structure' % employee_type).id),
                    ('code', '=', 'NET')
                ]
                self.env['hr.salary.rule'].search(salary_rule_domain_net, limit=1).write({'account_credit': accounts['201002'].id})
