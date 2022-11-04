# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo import tools

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class AccountTestFecImport(AccountTestInvoicingCommon):
    """ Main test class for Account FEC import testing """

    # ----------------------------------------
    # 1:: Files repo
    # ----------------------------------------

    test_content = """
        JournalCode\tJournalLib\tEcritureNum\tEcritureDate\tCompteNum\tCompteLib\tCompAuxNum\tCompAuxLib\tPieceRef\tPieceDate\tEcritureLib\tDebit\tCredit\tEcritureLet\tDateLet\tValidDate\tMontantdevise\tIdevise
        ACH\tACHATS\tACH000001\t20180808\t62270000\tFRAIS D'ACTES ET CONTENTIEUX\t\t\t1\t20180808\tACOMPTE FORMALITES ENTREPRISE\t500,00\t0,00\t\t\t20190725\t\t
        ACH\tACHATS\tACH000001\t20180808\t44566000\tTVA SUR AUTRES BIEN ET SERVICE\t\t\t1\t20180808\tACOMPTE FORMALITES ENTREPRISE\t100,00\t0,00\tAA\t\t20190725\t\t
        ACH\tACHATS\tACH000001\t20180808\t45500000\tCPT COURANTS DE L ASSOCIE\t\t\t1\t20180808\tACOMPTE FORMALITES ENTREPRISE\t0,00\t600,00\t\t\t20190725\t\t
        ACH\tACHATS\tACH000002\t20180808\t61320000\tLOCATIONS PARTNER 01\t\t\t2\t20180808\tDOMICILIATION\t300,00\t0,00\t\t\t20190725\t\t
        ACH\tACHATS\tACH000002\t20180808\t44566000\tTVA SUR AUTRES BIEN ET SERVICE\t\t\t2\t20180808\tDOMICILIATION\t60,00\t0,00\tAA\t\t20190725\t\t
        ACH\tACHATS\tACH000002\t20180808\t45500000\tCPT COURANTS DE L ASSOCIE\t\t\t2\t20180808\tDOMICILIATION\t0,00\t360,00\t\t\t20190725\t\t
        ACH\tACHATS\tACH000003\t20180910\t61320000\tLOCATIONS PARTNER 01\t\t\t3\t20180910\tPARTNER 01\t41,50\t0,00\t\t\t20190725\t\t
        ACH\tACHATS\tACH000003\t20180910\t44566000\tTVA SUR AUTRES BIEN ET SERVICE\t\t\t3\t20180910\tPARTNER 01\t8,30\t0,00\tAA\t\t20190725\t\t
        ACH\tACHATS\tACH000003\t20180910\t40100000\tFOURNISSEURS DIVERS\tPARTNER01\tPARTNER 01\t3\t20180910\tPARTNER 01\t0,00\t49,80\tAA\t\t20190725\t\t
    """

    # ----------------------------------------
    # 2:: Test class body
    # ----------------------------------------

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_fr.l10n_fr_pcg_chart_template'):
        """ Setup all the prerequisite entities for the CSV import tests to run """

        super().setUpClass(chart_template_ref=chart_template_ref)

        # Company -------------------------------------
        cls.company = cls.company_data['company']
        cls.company_export = cls.company_data_2['company']
        cls.company_export.vat = 'FR15437982937'
        cls.company.account_fiscal_country_id = cls.env.ref('base.fr')

        # Wizard --------------------------------------
        cls.wizard = cls.env['account.fec.import.wizard'].create({'company_id': cls.company.id})
        cls._attach_file_to_wizard(cls, cls.test_content, cls.wizard)

        # Export records for import test --------------
        cls.moves = cls.env['account.move'].with_company(cls.company_export).create([{
            'company_id': cls.company_export.id,
            'name': 'INV/001/123456',
            'date': datetime.date(2010, 1, 1),
            'invoice_date': datetime.date(2010, 1, 1),
            'move_type': 'entry',
            'partner_id': cls.partner_a.id,
            'journal_id': cls.company_data_2['default_journal_sale'].id,
            'line_ids': [(0, 0, {
                'company_id': cls.company_export.id,
                'name': 'line-1',
                'account_id': cls.company_data_2['default_account_receivable'].id,
                'fec_matching_number': '1',
                'credit': 0.0,
                'debit': 100.30
            }), (0, 0, {
                'company_id': cls.company_export.id,
                'name': 'line-2',
                'account_id': cls.company_data_2['default_account_tax_sale'].id,
                'fec_matching_number': '2',
                'credit': 100.30,
                'debit': 0.0
            })],
        }, {
            'company_id': cls.company_export.id,
            'name': 'INV/001/123457',
            'move_type': 'entry',
            'date': datetime.date(2010, 1, 1),
            'invoice_date': datetime.date(2010, 1, 1),
            'partner_id': cls.partner_b.id,
            'journal_id': cls.company_data_2['default_journal_purchase'].id,
            'line_ids': [(0, 0, {
                'company_id': cls.company_export.id,
                'name': 'line-3',
                'account_id': cls.company_data_2['default_account_payable'].id,
                'fec_matching_number': '3',
                'credit': 65.15,
                'debit': 0.0,
            }), (0, 0, {
                'company_id': cls.company_export.id,
                'name': 'line-4',
                'account_id': cls.company_data_2['default_account_expense'].id,
                'fec_matching_number': '4',
                'credit': 0.0,
                'debit': 65.15,
            })],
        }])

        # Export Wizard ----------------------------------------
        cls.export_wizard = cls.env['account.fr.fec'].create([{
            'date_from': datetime.date(1990, 1, 1),
            'date_to': datetime.date.today(),
            'test_file': True,
            'export_type': 'nonofficial'
        }])

        # Imbalanced moves test content -----------------------

        # Start by splitting the content in matrices
        matrix = [line.lstrip().split('\t') for line in cls.test_content.lstrip().split('\n') if line.lstrip()]

        # To balance by day, change the move names to 9 different ones,
        # so that its name cannot be used as grouping key
        for idx, line in enumerate(matrix[1:]):
            line[2] = "move_%s" % idx

        def join_matrix(matrix):
            return "\n".join(["\t".join(line) for line in matrix])

        cls.test_content_imbalanced_day = join_matrix(matrix)

        # To balance by month, change the move date of 2 move lines out of 3 of the same original move
        # to another day, so that the day cannot be used as grouping key
        for line in matrix[3:6]:
            line[3] = "20180809"
        cls.test_content_imbalanced_month = join_matrix(matrix)

        # To make them unbalanceable, make one line belong to another month than any other line
        # so that the month cannot be used as grouping key
        matrix[6][3] = "20181010"
        cls.test_content_imbalanced_none = join_matrix(matrix)

    def _attach_file_to_wizard(self, content, wizard=None):
        """ Create an attachment and bind it to the wizard and its log """
        content = '\n'.join([line.strip(' ') for line in content.split('\n') if line])
        if wizard:
            wizard.attachment_id = base64.b64encode(content.encode('utf-8'))

    # ----------------------------------------
    # 3:: Test methods
    # ----------------------------------------

    def test_import_fec_accounts(self):
        """ Test that the account are correctly imported from the FEC file """

        self.wizard._import_files(['account.account'])

        account_codes = ('401000', '445660', '622700')
        domain = [('company_id', '=', self.company.id), ('code', 'in', account_codes)]
        accounts = self.env['account.account'].search(domain, order='code')

        expected_values = [{
            'name': 'FOURNISSEURS DIVERS',
            'account_type': 'liability_payable',
            'reconcile': True
        }, {
            'name': 'TVA déductible sur autres biens et services',
            'account_type': 'asset_current',
            'reconcile': False,
        }, {
            'name': 'Frais d\'actes et de contentieux',
            'account_type': 'expense',
            'reconcile': False,
        }, ]
        self.assertRecordValues(accounts, expected_values)

    def test_import_fec_journals(self):
        """ Test that the journals are correctly imported from the FEC file """

        self.wizard._import_files(['account.account', 'account.journal'])

        journal_codes = ('ACH', )
        domain = [('company_id', '=', self.company.id), ('code', 'in', journal_codes)]
        journals = self.env['account.journal'].search(domain, order='code')

        expected_values = [{'name': 'FEC-ACHATS', 'type': 'general'}]
        self.assertRecordValues(journals, expected_values)

    def test_import_fec_partners(self):
        """ Test that the partners are correctly imported from the FEC file """

        self.wizard._import_files(['account.account', 'account.journal', 'res.partner'])

        partner_refs = ('PARTNER01', )
        domain = [('company_id', '=', self.company.id), ('ref', 'in', partner_refs)]
        partners = self.env['res.partner'].search(domain, order='ref')

        expected_values = [{'name': 'PARTNER 01'}]
        self.assertRecordValues(partners, expected_values)

    def test_import_fec_moves(self):
        """ Test that the moves are correctly imported from the FEC file """

        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

        move_names = ('ACH000001', 'ACH000002', 'ACH000003')
        domain = [('company_id', '=', self.company.id), ('name', 'in', move_names)]
        moves = self.env['account.move'].search(domain, order='name')

        journal = self.env['account.journal'].with_context(active_test=False).search([('code', '=', 'ACH')])
        expected_values = [{
            'name': move_names[0],
            'journal_id': journal.id,
            'date': datetime.date(2018, 8, 8),
            'move_type': 'entry',
            'ref': '1'
        }, {
            'name': move_names[1],
            'journal_id': journal.id,
            'date': datetime.date(2018, 8, 8),
            'move_type': 'entry',
            'ref': '2'
        }, {
            'name': move_names[2],
            'journal_id': journal.id,
            'date': datetime.date(2018, 9, 10),
            'move_type': 'entry',
            'ref': '3'
        }]
        self.assertRecordValues(moves, expected_values)

        self.assertEqual(1, len(moves[2].line_ids.filtered(lambda x: x.partner_id.name == 'PARTNER 01')))

    def test_import_fec_move_lines(self):
        """ Test that the move_lines are correctly imported from the FEC file """

        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

        move_names = ('ACH000001', 'ACH000002', 'ACH000003')
        domain = [('company_id', '=', self.company.id), ('move_name', 'in', move_names)]
        move_lines = self.env['account.move.line'].search(domain, order='move_name, id')
        columns = ['name', 'credit', 'debit', 'fec_matching_number']
        lines = [
            ('ACOMPTE FORMALITES ENTREPRISE', 0.00, 500.00, False),
            ('ACOMPTE FORMALITES ENTREPRISE', 0.00, 100.00, 'AA'),
            ('ACOMPTE FORMALITES ENTREPRISE', 600.00, 0.00, False),
            ('DOMICILIATION', 0.00, 300.00, False),
            ('DOMICILIATION', 0.00, 60.00, 'AA'),
            ('DOMICILIATION', 360.00, 0.00, False),
            ('PARTNER 01', 0.00, 41.50, False),
            ('PARTNER 01', 0.00, 8.30, 'AA'),
            ('PARTNER 01', 49.80, 0.00, 'AA'),
        ]
        expected_values = [dict(zip(columns, line)) for line in lines]
        self.assertRecordValues(move_lines, expected_values)

    def test_import_fec_demo_file(self):
        """ Test that the demo FEC file is correctly imported """

        # Attach the demo file
        with tools.file_open('l10n_fr_fec_import/demo/123459254FEC20190430.txt', mode='rb') as test_file:
            content = test_file.read().decode('latin-1')
            self._attach_file_to_wizard(content, self.wizard)

        # Import the file
        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

        # Verify move_lines presence
        move_names = ('ACH000001', 'ACH000002', 'ACH000003')
        domain = [('company_id', '=', self.company.id), ('move_name', 'in', move_names)]
        move_lines = self.env['account.move.line'].search(domain, order='move_name, id')
        self.assertEqual(9, len(move_lines))

        # Verify Reconciliation
        domain = [('company_id', '=', self.company.id), ('reconciled', '=', True)]
        move_lines = self.env['account.move.line'].search(domain)
        self.assertEqual(100, len(move_lines))

        # Verify Full Reconciliation
        domain = [('company_id', '=', self.company.id), ('full_reconcile_id', '!=', False)]
        move_lines = self.env['account.move.line'].search(domain)
        self.assertEqual(100, len(move_lines))

        # Verify Journal types
        domain = [('company_id', '=', self.company.id), ('name', '=', 'FEC-BQ 552')]
        journal = self.env['account.journal'].search(domain)
        self.assertEqual(journal.type, 'bank')

    def test_import_fec_export(self):
        """ Test that imports the results of a FEC export """

        # Generate the FEC content with the export wizard
        self.export_wizard.sudo().with_company(self.company_export).generate_fec()
        content = self.export_wizard.fec_data
        self.wizard.attachment_id = content

        # Import the exported FEC file in the test's main company
        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

        # Verify moves data
        new_moves = self.env['account.move'].search([
            ('company_id', '=', self.company_export.id),
            ('tax_closing_end_date', '=', False),  # exclude automatic tax closing  entries
        ], order="name")
        columns = ['company_id', 'name', 'journal_id', 'partner_id', 'date']
        moves_data = [
            (self.company_export.id, 'INV/001/123456', self.company_data_2['default_journal_sale'].id, self.partner_a.id, datetime.date(2010, 1, 1)),
            (self.company_export.id, 'INV/001/123457', self.company_data_2['default_journal_purchase'].id, self.partner_b.id, datetime.date(2010, 1, 1)),
        ]
        expected_values = [dict(zip(columns, move_data)) for move_data in moves_data]
        self.assertRecordValues(new_moves, expected_values)

        # Verify moves lines data
        columns = ['company_id', 'name', 'credit', 'debit', 'fec_matching_number', 'account_id']
        lines_data = [
            (self.company_export.id, 'line-1', 0.00, 100.30, '1', self.company_data_2['default_account_receivable'].id),
            (self.company_export.id, 'line-2', 100.30, 0.00, '2', self.company_data_2['default_account_tax_sale'].id),
            (self.company_export.id, 'line-3', 65.15, 0.00, '3', self.company_data_2['default_account_payable'].id),
            (self.company_export.id, 'line-4', 0.00, 65.15, '4', self.company_data_2['default_account_expense'].id),
        ]
        expected_values = [dict(zip(columns, line_data)) for line_data in lines_data]
        new_lines = new_moves.mapped("line_ids").sorted(key=lambda x: x.name)
        self.assertRecordValues(new_lines, expected_values)

    def test_balance_moves_by_day(self):
        """ Test that the imbalanced moves are correctly balanced with a grouping by day """

        self._attach_file_to_wizard(self.test_content_imbalanced_day, self.wizard)
        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

        domain = [('company_id', '=', self.company.id), ('move_name', 'in', ('ACH/20180808', 'ACH/20180910'))]
        move_lines = self.env['account.move.line'].search(domain, order='move_name,name')

        self.assertEqual(
            move_lines.mapped(lambda line: (line.move_name, line.name)),
            [
                ('ACH/20180808', 'ACOMPTE FORMALITES ENTREPRISE'),
                ('ACH/20180808', 'ACOMPTE FORMALITES ENTREPRISE'),
                ('ACH/20180808', 'ACOMPTE FORMALITES ENTREPRISE'),
                ('ACH/20180808', 'DOMICILIATION'),
                ('ACH/20180808', 'DOMICILIATION'),
                ('ACH/20180808', 'DOMICILIATION'),
                ('ACH/20180910', 'PARTNER 01'),
                ('ACH/20180910', 'PARTNER 01'),
                ('ACH/20180910', 'PARTNER 01'),
            ])

    def test_balance_moves_by_month(self):
        """ Test that the imbalanced moves are correctly balanced with a grouping by month """

        self._attach_file_to_wizard(self.test_content_imbalanced_month, self.wizard)
        self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])

        domain = [('company_id', '=', self.company.id), ('move_name', 'in', ('ACH/201808', 'ACH/201809'))]
        move_lines = self.env['account.move.line'].search(domain, order='move_name,name')
        self.assertEqual(
            move_lines.mapped(lambda line: (line.move_name, line.name)),
            [
                ('ACH/201808', 'ACOMPTE FORMALITES ENTREPRISE'),
                ('ACH/201808', 'ACOMPTE FORMALITES ENTREPRISE'),
                ('ACH/201808', 'ACOMPTE FORMALITES ENTREPRISE'),
                ('ACH/201808', 'DOMICILIATION'),
                ('ACH/201808', 'DOMICILIATION'),
                ('ACH/201808', 'DOMICILIATION'),
                ('ACH/201809', 'PARTNER 01'),
                ('ACH/201809', 'PARTNER 01'),
                ('ACH/201809', 'PARTNER 01'),
            ])

    def test_unbalanceable_moves(self):
        """ Test that the imbalanced moves raise as they cannot be balanced by day/month """

        self._attach_file_to_wizard(self.test_content_imbalanced_none, self.wizard)
        with self.assertRaises(UserError):
            self.wizard._import_files(['account.account', 'account.journal', 'res.partner', 'account.move'])
