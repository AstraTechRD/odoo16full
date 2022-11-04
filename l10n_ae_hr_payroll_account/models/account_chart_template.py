# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def load_payroll_accounts(self):
        """
        Override to configure payroll accounting data as well as accounting data.
        """
        if self == self.env.ref('l10n_ae.uae_chart_template_standard'):
            ae_companies = self.env['res.company'].search([('partner_id.country_id.code', '=', 'AE')])
            self._configure_payroll_account_data_uae(ae_companies)

    def _configure_payroll_account_data_uae(self, companies):
        accounts_codes = [
            '201002',  # Payables
            '202001',  # End of Service Provision
            '400003',  # Basic Salary
            '400004',  # Housing Allowance
            '400005',  # Transportation Allowance
            '400008',  # End of Service Indemnity
            '400012',  # Staff Other Allowances
        ]
        uae_structures = self.env['hr.payroll.structure'].search([('country_id.code', '=', "AE")])
        for company in companies:
            self = self.with_company(company)

            accounts = {}
            for code in accounts_codes:
                account = self.env['account.account'].search(
                    [('company_id', '=', company.id), ('code', 'like', '%s%%' % code)], limit=1)
                if not account:
                    # we don't have all the necessary accounts, cannot continue
                    # raise ValidationError(_('No existing account for code %s', code))
                    return
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
                {structure.id: journal.id for structure in uae_structures},
            )

            # ================================================ #
            #          UAE Employee Payroll Structure          #
            # ================================================ #

            salary_rule_domain_basic = [
                ('struct_id', '=', self.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure').id),
                ('code', '=', 'BASIC')
            ]
            self.env['hr.salary.rule'].search(salary_rule_domain_basic, limit=1).write({'account_debit': accounts['400003'].id})
            # self.env.ref('l10n_ae_hr_payroll.uae_basic_salary_rule').write({"account_debit": accounts['400003'].id})
            self.env.ref('l10n_ae_hr_payroll.uae_housing_allowance_salary_rule').write(
                {"account_debit": accounts['400004'].id})
            self.env.ref('l10n_ae_hr_payroll.uae_transportation_allowance_salary_rule').write(
                {"account_debit": accounts['400005'].id})
            self.env.ref('l10n_ae_hr_payroll.uae_other_allowances_salary_rule').write(
                {"account_debit": accounts['400012'].id})
            # self.env.ref('l10n_ae_hr_payroll.uae_net_salary_rule').write({"account_credit": accounts['201002'].id})
            self.env.ref('l10n_ae_hr_payroll.uae_end_of_service_salary_rule').write(
                {"account_debit": accounts['202001'].id})
            self.env.ref('l10n_ae_hr_payroll.uae_end_of_service_provision_salary_rule').write(
                {"account_debit": accounts['400008'].id, "account_credit": accounts['202001'].id})
            salary_rule_domain_net = [
                ('struct_id', '=', self.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure').id),
                ('code', '=', 'NET')
            ]
            self.env['hr.salary.rule'].search(salary_rule_domain_net, limit=1).write({'account_credit': accounts['201002'].id})
