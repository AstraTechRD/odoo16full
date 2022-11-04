# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import file_open


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSodaFile(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.company.vat = 'BE0477472701'
        cls.misc_journal = cls.env['account.journal'].create({
            'name': 'Miscellaneous',
            'code': 'smis',
            'type': 'general',
        })
        cls.soda_file_path = 'l10n_be_soda/test_soda_file/soda_testing_file.xml'
        cls.attachment = False

    def test_soda_file_import(self):
        with file_open(self.soda_file_path, 'rb') as soda_file:
            result = self.misc_journal.create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'soda_testing_file.xml',
                'raw': soda_file.read(),
            }).ids)
            result_move = self.env['account.move'].search([('id', '=', result['res_id'])])
            self.assertEqual(len(result_move.line_ids), 3)
            self.assertRecordValues(result_move.line_ids, [
                {'debit': 0, 'credit': 4000.00, 'name': 'Withholding Taxes'},
                {'debit': 0, 'credit': 11655.10, 'name': 'Special remuneration'},
                {'debit': 15655.10, 'credit': 0, 'name': 'Remuneration'},
            ])
            self.assertRecordValues(result_move.line_ids.account_id, [{'code': '4530'}, {'code': '4550'}, {'code': '61800'}])
