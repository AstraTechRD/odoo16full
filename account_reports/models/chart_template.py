# coding: utf-8
from odoo import models, fields


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):
        res = super(AccountChartTemplate, self)._load(company)

        # by default, anglo-saxon companies should have totals
        # displayed below sections in their reports
        company.totals_below_sections = company.anglo_saxon_accounting

        #set a default misc journal for the tax closure
        company.account_tax_periodicity_journal_id = company._get_default_misc_journal()

        company.account_tax_periodicity_reminder_day = 7
        # create the recurring entry
        company.with_company(company)._get_and_update_tax_closing_moves(fields.Date.today(), include_domestic=True)
        return res
