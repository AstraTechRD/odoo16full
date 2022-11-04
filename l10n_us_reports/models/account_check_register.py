# -*- coding: utf-8 -*-
from odoo import models, api, _


class USReportCustomHandler(models.AbstractModel):
    '''Check Register is an accounting report usually part of the general ledger, used to record
    financial transactions in cash.
    '''
    _name = 'l10n_us.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'US Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        return self.env['account.general.ledger.report.handler']._dynamic_lines_generator(report, options, all_column_groups_expression_totals)

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        report._init_options_journals(options, previous_options=previous_options, additional_journals_domain=[('type', 'in', ('bank', 'cash', 'general'))])
