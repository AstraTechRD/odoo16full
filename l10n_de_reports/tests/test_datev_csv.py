# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import tagged
from odoo.tools import pycompat
import zipfile
from io import BytesIO
from odoo.addons.account.tests.common import AccountTestInvoicingCommon



@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDatevCSV(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref='l10n_de_skr03.l10n_de_chart_template')

        cls.account_3400 = cls.env['account.account'].search([
            ('code', '=', 3400),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)
        cls.account_4980 = cls.env['account.account'].search([
            ('code', '=', 4980),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)
        cls.account_1500 = cls.env['account.account'].search([
            ('code', '=', 1500),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)
        cls.tax_19 = cls.env['account.tax'].search([
            ('name', '=', '19% Vorsteuer'),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)
        cls.tax_7 = cls.env['account.tax'].search([
            ('name', '=', '7% Vorsteuer'),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)

    def test_datev_in_invoice(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report._get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                (0, None, {
                    'price_unit': 100,
                    'account_id': self.account_3400.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
                (0, None, {
                    'price_unit': 100,
                    'account_id': self.account_3400.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
                (0, None, {
                    'price_unit': 100,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()
        move.line_ids.flush_recordset()

        with zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r') as zf:
            csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.assertEqual(2, len(data), "csv should have 2 lines")
        self.assertIn(['238,00', 's', 'EUR', '34000000', str(move.partner_id.id + 700000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)
        self.assertIn(['119,00', 's', 'EUR', '49800000', str(move.partner_id.id + 700000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)

    def test_datev_out_invoice(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report._get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                (0, None, {
                    'price_unit': 100,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()
        move.line_ids.flush_recordset()

        with zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r') as zf:
            csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.assertEqual(1, len(data), "csv should have 1 line")
        self.assertIn(['119,00', 'h', 'EUR', '49800000', str(move.partner_id.id + 100000000),
                      self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)

    def test_datev_miscellaneous(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report._get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2020-12-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {
                    'debit': 100,
                    'credit': 0,
                    'partner_id': self.partner_a.id,
                    'account_id': self.account_4980.id,
                }),
                (0, 0, {
                    'debit': 0,
                    'credit': 100,
                    'partner_id': self.partner_a.id,
                    'account_id': self.account_3400.id,
                    'tax_ids': [],
                }),
            ]
        })
        move.action_post()
        move.line_ids.flush_recordset()

        with zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r') as zf:
            csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[9], x[10], x[13]] for x in reader][2:]
        self.assertEqual(1, len(data), "csv should have 1 lines")
        self.assertIn(['100,00', 'h', 'EUR', '34000000', '49800000', '112', move.name, move.name], data)

    def test_datev_out_invoice_payment(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report._get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                (0, None, {
                    'price_unit': 100,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()

        pay = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
            'payment_date': fields.Date.to_date('2020-12-03'),
        })._create_payments()

        self.env.flush_all()

        debit_account_code = str(self.env.company.account_journal_payment_debit_account_id.code).ljust(8, '0')

        with zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r') as zf:
            csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.assertEqual(2, len(data), "csv should have 2 lines")
        self.assertIn(['119,00', 'h', 'EUR', '49800000', str(move.partner_id.id + 100000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)
        self.assertIn(['119,00', 'h', 'EUR', str(move.partner_id.id + 100000000), debit_account_code, '', '312',
                       pay.name, pay.name], data)

    def test_datev_in_invoice_payment(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report._get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                (0, None, {
                    'price_unit': 100,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()

        pay = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
            'payment_date': fields.Date.to_date('2020-12-03'),
        })._create_payments()

        self.env.flush_all()

        credit_account_code = str(self.env.company.account_journal_payment_credit_account_id.code).ljust(8, '0')
        with zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r') as zf:
            csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.assertEqual(2, len(data), "csv should have 2 lines")
        self.assertIn(['119,00', 's', 'EUR', '49800000', str(move.partner_id.id + 700000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)
        self.assertIn(['119,00', 's', 'EUR', str(move.partner_id.id + 700000000), credit_account_code, '', '312',
                       pay.name, pay.name], data)

    def test_datev_bank_statement(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report._get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        statement = self.env['account.bank.statement'].create({
            'balance_end_real': 100.0,
            'line_ids': [
                (0, 0, {
                    'journal_id': self.company_data['default_journal_bank'].id,
                    'payment_ref': 'line1',
                    'amount': 100.0,
                    'date': '2020-01-01',
                }),
            ],
        })
        statement.line_ids.move_id.flush_recordset()

        suspense_account_code = str(self.env.company.account_journal_suspense_account_id.code).ljust(8, '0')
        bank_account_code = str(self.env.company.bank_journal_ids.default_account_id.code).ljust(8, '0')

        with zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r') as zf:
            csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[9], x[10], x[13]] for x in reader][2:]
        self.assertIn(['100,00', 'h', 'EUR', suspense_account_code, bank_account_code, '101',
                       statement.line_ids[0].name, statement.line_ids[0].name], data)

    def test_datev_out_invoice_paid(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report._get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [(0, 0, {
                'price_unit': 100.0,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [],
            })],
        })
        move.action_post()

        statement = self.env['account.bank.statement'].create({
            'balance_end_real': 100.0,
            'line_ids': [
                (0, 0, {
                    'journal_id': self.company_data['default_journal_bank'].id,
                    'payment_ref': 'line_1',
                    'amount': 100.0,
                    'partner_id': self.partner_a.id,
                    'date': '2020-01-01',
                }),
            ],
        })

        receivable_line = move.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=statement.line_ids.id).new({})
        wizard._action_add_new_amls(receivable_line, allow_partial=False)
        wizard.button_validate(async_action=False)

        bank_account_code = str(self.env.company.bank_journal_ids.default_account_id.code).ljust(8, '0')

        self.env.flush_all()
        file_dict = self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)
        with zipfile.ZipFile(BytesIO(file_dict['file_content']), 'r') as zf:
            csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[9], x[10], x[13]] for x in reader][2:]
        self.assertEqual(2, len(data), "csv should have 2 lines")
        self.assertIn(['100,00', 'h', 'EUR', str(self.company_data['default_account_revenue'].code).ljust(8, '0'),
                       str(100000000 + move.partner_id.id), '112', move.name, move.name], data)
        self.assertIn(['100,00', 'h', 'EUR', str(100000000 + move.partner_id.id), bank_account_code, '101',
                       statement.line_ids[0].name, statement.line_ids[0].name], data)

    def test_datev_out_invoice_with_negative_amounts(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report._get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                (0, None, {
                    'price_unit': 1000,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
                (0, None, {
                    'price_unit': -1000,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
                (0, None, {
                    'price_unit': 1000,
                    'quantity': -1,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
                (0, None, {
                    'price_unit': 2000,
                    'account_id': self.account_1500.id,
                    'tax_ids': [(6, 0, self.tax_7.ids)],
                }),
                (0, None, {
                    'price_unit': 3000,
                    'account_id': self.account_3400.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()
        move.line_ids.flush_recordset()

        with zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r') as zf:
            csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.assertEqual(3, len(data), "csv should have 3 line")
        self.assertIn(['1190,00', 's', 'EUR', '49800000', str(move.partner_id.id + 100000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)
        self.assertIn(['2140,00', 'h', 'EUR', '15000000', str(move.partner_id.id + 100000000),
                       self.tax_7.l10n_de_datev_code, '112', move.name, move.name], data)
        self.assertIn(['3570,00', 'h', 'EUR', '34000000', str(move.partner_id.id + 100000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)

    def test_datev_different_syst_param(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report._get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                (0, None, {
                    'price_unit': 100,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()
        move.line_ids.flush_recordset()

        self.env['ir.config_parameter'].sudo().set_param('l10n_de.datev_start_count', 2)
        self.env['ir.config_parameter'].sudo().set_param('l10n_de.datev_start_count_vendors', 800000)

        with zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r') as zf:
            csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.assertEqual(1, len(data), "csv should have 1 line")
        self.assertIn(['119,00', 'h', 'EUR', '49800', str(move.partner_id.id + 200000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)
