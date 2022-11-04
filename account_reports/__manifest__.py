# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Accounting Reports',
    'summary': 'View and create reports',
    'category': 'Accounting/Accounting',
    'description': """
Accounting Reports
==================
    """,
    'depends': ['account_accountant'],
    'data': [
        'security/ir.model.access.csv',
        'views/report_templates.xml',
        'data/balance_sheet.xml',
        'data/cash_flow_report.xml',
        'data/executive_summary.xml',
        'data/profit_and_loss.xml',
        'data/aged_partner_balance.xml',
        'data/general_ledger.xml',
        'data/bank_reconciliation_report.xml',
        'data/trial_balance.xml',
        'data/sales_report.xml',
        'data/partner_ledger.xml',
        'data/multicurrency_revaluation_report.xml',
        'data/journal_report.xml',
        'data/generic_tax_report.xml',
        'views/account_report_view.xml',
        'data/account_report_actions.xml',
        'data/menuitems.xml',
        'data/mail_activity_type_data.xml',
        'views/res_company_views.xml',
        'views/partner_view.xml',
        'views/account_journal_dashboard_view.xml',
        'views/mail_activity_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/multicurrency_revaluation.xml',
        'wizard/report_export_wizard.xml',
        'wizard/fiscal_year.xml',
        'views/account_activity.xml',
        'views/account_account_views.xml',
        'views/account_tax_views.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
    'post_init_hook': 'set_periodicity_journal_on_companies',
    'assets': {
        'account_reports.assets_financial_report': [
            ('include', 'web._assets_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap'),
            'web/static/fonts/fonts.scss',
            'account_reports/static/src/scss/account_financial_report.scss',
            'account_reports/static/src/scss/account_report_print.scss',
        ],
        'web.assets_backend': [
            'account_reports/static/src/js/legacy_mail_activity.js',
            'account_reports/static/src/js/account_reports.js',
            'account_reports/static/src/js/action_manager_account_report_dl.js',
            'account_reports/static/src/scss/account_financial_report.scss',
            'account_reports/static/src/components/**/*.js',
            'account_reports/static/src/xml/**/*',
        ],
        'web.qunit_suite_tests': [
            'account_reports/static/tests/action_manager_account_report_dl_tests.js',
            'account_reports/static/tests/account_reports_tests.js',
        ],
        'web.assets_tests': [
            'account_reports/static/tests/tours/**/*',
        ],
    }
}
