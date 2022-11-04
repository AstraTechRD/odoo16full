# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IndividualAccountReport(models.AbstractModel):
    _name = 'report.l10n_be_hr_payroll.report_individual_account'
    _description = 'Individual Account Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {'report_data': data}
