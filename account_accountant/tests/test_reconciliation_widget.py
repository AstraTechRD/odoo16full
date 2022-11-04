import logging
import odoo.tests
import time
from odoo.addons.account.tests.common import TestAccountReconciliationCommon
from odoo import fields

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('post_install', '-at_install')
class TestReconciliationWidget(TestAccountReconciliationCommon):

    def test_reconciliation_process_move_lines_with_mixed_currencies(self):
        # Delete any old rate - to make sure that we use the ones we need.
        old_rates = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.currency_usd_id)])
        old_rates.unlink()

        self.env['res.currency.rate'].create({
            'currency_id': self.currency_usd_id,
            'name': time.strftime('%Y') + '-01-01',
            'rate': 2,
        })

        move_product = self.env['account.move'].create({
            'ref': 'move product',
        })
        move_product_lines = self.env['account.move.line'].create([
            {
                'name': 'line product',
                'move_id': move_product.id,
                'account_id': self.env['account.account'].search([
                    ('account_type', '=', 'income'),
                    ('company_id', '=', self.company.id)
                ], limit=1).id,
                'debit': 20,
                'credit': 0,
            },
            {
                'name': 'line receivable',
                'move_id': move_product.id,
                'account_id': self.account_rcv.id,
                'debit': 0,
                'credit': 20,
            }
        ])
        move_product.action_post()

        move_payment = self.env['account.move'].create({
            'ref': 'move payment',
        })
        liquidity_account = self.env['account.account'].search([
            ('account_type', '=', 'asset_cash'),
            ('company_id', '=', self.company.id)], limit=1)
        move_payment_lines = self.env['account.move.line'].create([
            {
                'name': 'line product',
                'move_id': move_payment.id,
                'account_id': liquidity_account.id,
                'debit': 10.0,
                'credit': 0,
                'amount_currency': 20,
                'currency_id': self.currency_usd_id,
            },
            {
                'name': 'line product',
                'move_id': move_payment.id,
                'account_id': self.account_rcv.id,
                'debit': 0,
                'credit': 10.0,
                'amount_currency': -20,
                'currency_id': self.currency_usd_id,
            }
        ])
        move_payment.action_post()

        # We are reconciling a move line in currency A with a move line in currency B and putting
        # the rest in a writeoff, this test ensure that the debit/credit value of the writeoff is
        # correctly computed in company currency.
        self.env['account.reconciliation.widget'].process_move_lines([{
            'id': False,
            'type': False,
            'mv_line_ids': [move_payment_lines[1].id, move_product_lines[1].id],
            'new_mv_line_dicts': [{
                'account_id': liquidity_account.id,
                'analytic_distribution': False,
                'credit': 0,
                'date': time.strftime('%Y') + '-01-01',
                'debit': 15.0,
                'journal_id': self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.company.id)], limit=1).id,
                'name': 'writeoff',
            }],
        }])

        writeoff_line = self.env['account.move.line'].search([('name', '=', 'writeoff'), ('company_id', '=', self.company.id)])
        self.assertEqual(writeoff_line.credit, 15.0)

    def test_writeoff_single_entry(self):
        """ Test writeoff are grouped by journal and date in common journal entries"""
        today = fields.Date.today().strftime('%Y-07-15')
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-21',
            'date': '2019-01-21',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.tax_purchase_a.ids)],
            })]
        })
        invoice.action_post()

        payment = self.env['account.payment'].create({
            'date': invoice.date,
            'partner_id': self.partner_a.id,
            'amount': 1161.5,
            'payment_type': 'inbound',
            'partner_type': 'customer',
        })
        payment.action_post()

        # Create a write-off for the residual amount.
        account = self.company_data['default_account_receivable']
        lines = (invoice + payment.move_id).line_ids.filtered(lambda line: line.account_id == account)

        self.env['account.reconciliation.widget'].process_move_lines([{
            'type': 'other',
            'mv_line_ids': lines.ids,
            'new_mv_line_dicts': [
                {
                    'name': 'TEST',
                    'journal_id': self.company_data['default_journal_misc'].id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'balance': 10,
                    'date': today,
                    'tax_ids': [(6, 0, self.tax_purchase_a.ids)],
                },
                {
                    'name': 'TEST TAX',
                    'journal_id': self.company_data['default_journal_misc'].id,
                    'account_id': self.company_data['default_account_tax_sale'].id,
                    'date': today,
                    'balance': 1.5,
                    'tax_base_amount': -10,
                    'tax_repartition_line_id': self.tax_purchase_a.invoice_repartition_line_ids.filtered('account_id').id
                }
            ]}])

        self.assertTrue(all(line.reconciled for line in lines))

        write_off = lines.full_reconcile_id.reconciled_line_ids.move_id - lines.move_id

        self.assertEqual(len(write_off), 1, "It should create only a single journal entry")

        self.assertRecordValues(write_off.line_ids.sorted('balance'), [
            {
                'partner_id': self.partner_a.id,
                'debit': 0.0,
                'credit': 10,
            },
            {
                'partner_id': self.partner_a.id,
                'debit': 0.0,
                'credit': 1.5,
            },
            {
                'partner_id': self.partner_a.id,
                'debit': 1.5,
                'credit': 0.0,
            },
            {
                'partner_id': self.partner_a.id,
                'debit': 10,
                'credit': 0.0,
            },
        ])

    def test_prepare_writeoff_moves_multi_currency(self):
        for invoice_type, payment_type, partner_type in (
            ('out_invoice', 'inbound', 'customer'),
            ('in_invoice', 'outbound', 'supplier'),
        ):
            # Create an invoice at rate 1:2.
            invoice = self.env['account.move'].create({
                'move_type': invoice_type,
                'partner_id': self.partner_a.id,
                'currency_id': self.currency_data['currency'].id,
                'invoice_date': '2019-01-21',
                'date': '2019-01-21',
                'invoice_line_ids': [(0, 0, {
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'tax_ids': [],
                })]
            })
            invoice.action_post()

            # Create a payment at rate 1:2.
            payment = self.env['account.payment'].create({
                'date': invoice.date,
                'partner_id': self.partner_a.id,
                'amount': 800.0,
                'currency_id': self.currency_data['currency'].id,
                'payment_type': payment_type,
                'partner_type': partner_type,
            })
            payment.action_post()

            # Create a write-off for the residual amount.
            account = invoice.line_ids\
                .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')).account_id
            lines = (invoice + payment.move_id).line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
            write_off_vals = self.env['account.reconciliation.widget']._prepare_writeoff_moves(lines, {
                'journal_id': self.company_data['default_journal_misc'].id,
                'account_id': self.company_data['default_account_revenue'].id,
            })
            write_off = self.env['account.move'].create(write_off_vals)
            write_off.action_post()

            self.assertRecordValues(write_off.line_ids.sorted('balance'), [
                {
                    'partner_id': self.partner_a.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -200.0,
                },
                {
                    'partner_id': self.partner_a.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                },
            ])

            # Reconcile.
            all_lines = (invoice + payment.move_id + write_off).line_ids.filtered(lambda line: line.account_id == account)
            all_lines.reconcile()

            for line in all_lines:
                self.assertTrue(line.reconciled)

    def test_with_reconciliation_model(self):
        bank_fees = self.env['account.reconcile.model'].create({
            'name': 'Bank Fees',
            'line_ids': [(0, 0, {
                'account_id': self.company_data['default_account_expense'].id,
                'journal_id': self.company_data['default_journal_misc'].id,
                'amount_type': 'fixed',
                'amount_string': '50',
            })],
        })

        customer = self.partner_a

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': customer.id,
            'invoice_date': '2021-05-12',
            'date': '2021-05-12',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [],
            })],
        })
        invoice.action_post()
        inv_receivable = invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')

        payment = self.env['account.payment'].create({
            'partner_id': customer.id,
            'amount': 600,
        })
        payment.action_post()
        payment_receivable = payment.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')

        self.env['account.reconciliation.widget'].process_move_lines([{
            'id': None,
            'type': None,
            'mv_line_ids': (inv_receivable + payment_receivable).ids,
            'new_mv_line_dicts': [{
                'name': 'SuperLabel',
                'balance': -bank_fees.line_ids.amount,
                'analytic_distribution': False,
                'account_id': bank_fees.line_ids.account_id.id,
                'journal_id': bank_fees.line_ids.journal_id.id,
                'reconcile_model_id': bank_fees.id}
            ]
        }])

        self.assertEqual(invoice.amount_residual, 350)
