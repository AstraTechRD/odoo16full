# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Luxembourg - Accounting Reports',
    'icon': '/l10n_lu/static/description/icon.png',
    'version': '1.0',
    'description': """
Accounting reports for Luxembourg
=================================
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_lu', 'account_asset', 'account_reports', 'account_saft'],
    'data': [
        'data/account_financial_html_report_pl.xml',
        'data/account_financial_html_report_pl_abr.xml',
        'data/account_financial_html_report_bs.xml',
        'data/account_financial_html_report_bs_abr.xml',
        'data/account.report.line.csv',
        'data/tax_report.xml',
        'data/ir_cron_data.xml',
        'data/saft_report.xml',
        'data/ec_sales_list_report.xml',
        'views/account_ec_sales_xml_template.xml',
        'views/electronic_report_template.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/l10n_lu_stored_sales_report_views.xml',
        'views/l10n_lu_yearly_tax_report_manual_views.xml',
        'wizard/l10n_lu_generate_accounts_report.xml',
        'wizard/l10n_lu_generate_sales_report.xml',
        'security/ir.model.access.csv',
        'security/l10n_lu_yearly_tax_report_manual_security.xml',
    ],
    'demo': ['demo/demo_company.xml'],
    'auto_install': ['l10n_lu', 'account_reports'],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'l10n_lu_reports/static/src/scss/tax_fields_views.scss',
        ],
    },
}
