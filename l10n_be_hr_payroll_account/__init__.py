# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo import api, SUPERUSER_ID


def _post_install_hook_configure_journals(cr, registry):
    """
        This method will create a salary journal for each company and allocate it to each Belgian structure.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env['res.company'].search([
        ('partner_id.country_id.code', '=', "BE"),
        ('chart_template_id', '!=', False)])
    for company in companies:
        env['account.chart.template']._configure_payroll_account_data(company)
