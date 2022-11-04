# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestAllReportsGeneration(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        available_country_ids = cls.env['account.chart.template'].search([('country_id', '!=', False)]).country_id.ids
        if cls.env.ref('l10n_generic_coa.configurable_chart_template', raise_if_not_found=False):
            available_country_ids += [cls.env.ref('base.us').id, False]

        cls.reports = cls.env['account.report'].search([('country_id', 'in', available_country_ids)])
        # The consolidation report needs a consolidation.period to be open, which we won't have by default.
        # Therefore, instead of testing it here, wse skip it and add a dedicated test in the consolidation module.
        conso_report = cls.env.ref('account_consolidation.consolidated_balance_report', raise_if_not_found=False)
        if conso_report and conso_report in cls.reports:
            cls.reports -= conso_report
        # Reset the reports country_ids, so that we can open all of them with the current company without issues.
        cls.reports.country_id = False

        # Setup some generic data on the company that could be needed for some file export
        cls.env.company.partner_id.write({
            'vat': "VAT123456789",
            'email': "dummy@email.com",
            'phone': "01234567890",
        })

        # The consolidation report needs a consolidation.period to be open, which we won't have by default.
        # Therefore, we avoid testing it here, and instead add a dedicated test in the appropriate module.
        conso_report = cls.env.ref('account_consolidation.consolidated_balance_report', raise_if_not_found=False)
        if conso_report and conso_report in cls.reports:
            cls.reports -= conso_report

        # Make the reports always available, so that they don't clash with the comany's country
        cls.reports.availability_condition = 'always'

        # Some file exports require VAT, mail and/or phone to be set on the company. We set them all here, in case we need them.
        cls.env.company.partner_id.write({
            'vat': "VAT123456789",
            'email': "dummy@email.com",
            'phone': "01234567890",
        })

    def test_open_all_reports(self):
        # 'unfold_all' is forced on all reports (even if they don't support it), so that we really open it entirely
        self.reports.filter_unfold_all = True

        for report in self.reports:
            # 'report_id' key is forced so that we don't open a variant when calling a root report
            report.get_report_informations({'report_id': report.id, 'unfold_all': True})

    def test_generate_all_export_files(self):
        for report in self.reports:
            options = report._get_options({'report_id': report.id})

            for option_button in options['buttons']:
                with patch.object(type(self.env['ir.actions.report']), '_run_wkhtmltopdf', lambda *args, **kwargs: b"This is a pdf"):
                    function_params = [options]
                    if option_button.get('action_param'):
                        function_params.append(option_button['action_param'])

                    action = option_button['action']
                    if report.custom_handler_model_id and hasattr(self.env[report.custom_handler_model_name], action):
                        action_dict = getattr(self.env[report.custom_handler_model_name], action)(*function_params)
                    else:
                        action_dict = getattr(report, action)(*function_params)

                    if action_dict['type'] == 'ir_actions_account_report_download':
                        file_gen = action_dict['data']['file_generator']
                        if report.custom_handler_model_id and hasattr(self.env[report.custom_handler_model_name], file_gen):
                            file_gen_res = getattr(self.env[report.custom_handler_model_name], file_gen)(options)
                        else:
                            file_gen_res = getattr(report, file_gen)(options)

                        self.assertEqual(
                            set(file_gen_res.keys()), {'file_name', 'file_content', 'file_type'},
                            "File generator's result should always contain the same 3 keys."
                        )
