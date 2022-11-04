# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError

from odoo import models, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, company):
        """
        Override to configure payroll accounting data as well as accounting data.
        """
        res = super()._load(company)
        if self == self.env.ref('l10n_lu.lu_2011_chart_1'):
            self._configure_payroll_account_luxembourg(company)
        return res

    def _load_payroll_accounts(self):
        if self == self.env.ref('l10n_lu.lu_2011_chart_1'):
            sa_companies = self.env['res.company'].search([
                ('partner_id.country_id.code', '=', 'LU'),
                ('chart_template_id', '=', self.env.ref('l10n_lu.lu_2011_chart_1').id)])
            self._configure_payroll_account_luxembourg(sa_companies)

    def _configure_payroll_account_luxembourg(self, companies):
        accounts_codes = [
            # YTI TODO: Configure accounts
        ]
        lu_structures = self.env['hr.payroll.structure'].search([('country_id.code', '=', "LU")])
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
                ('code', '=', 'SLR'),
                ('name', '=', 'Salaries'),
                ('company_id', '=', company.id)])

            if not journal:
                journal = self.env['account.journal'].create({
                    'name': 'Salaries',
                    'code': 'SLR',
                    'type': 'general',
                    'company_id': company.id,
                })

            self.env['ir.property']._set_multi(
                "journal_id",
                "hr.payroll.structure",
                {structure.id: journal.id for structure in lu_structures},
            )

            # ================================================ #
            #          LUX Employee Payroll Structure          #
            # ================================================ #

            # TODO: Setup Accounts
