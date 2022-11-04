# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests
from .common import TestInterCompanyRulesCommon


@odoo.tests.tagged('post_install','-at_install')
class TestInterCompanyInvoice(TestInterCompanyRulesCommon):

    def test_00_inter_company_invoice_flow(self):
        """ Test inter company invoice flow """

        # Enable auto generate invoice in company.
        (self.company_a + self.company_b).write({
            'rule_type': 'invoice_and_refund'
        })
        self.env.ref('base.EUR').active = True

        # Create customer invoice for company A. (No need to call onchange as all the needed values are specified)
        self.res_users_company_a.company_ids = [(4, self.company_b.id)]
        customer_invoice = self.env['account.move'].with_user(self.res_users_company_a).create({
            'move_type': 'out_invoice',
            'partner_id': self.company_b.partner_id.id,
            'currency_id': self.env.ref('base.EUR').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_consultant.id,
                'price_unit': 450.0,
                'quantity': 1.0,
                'name': 'test'
            })]
        })

        # Check account invoice state should be draft.
        self.assertEqual(customer_invoice.state, 'draft', 'Initially customer invoice should be in the "Draft" state')

        # Validate invoice
        customer_invoice.with_user(self.res_users_company_a).action_post()

        # Check Invoice status should be open after validate.
        self.assertEqual(customer_invoice.state, 'posted', 'Invoice should be in Open state.')

        # I check that the vendor bill is created with proper data.
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)

        self.assertTrue(supplier_invoice.invoice_line_ids[0].quantity == 1, "Quantity in invoice line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].product_id.id == self.product_consultant.id, "Product in line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].price_unit == 450, "Unit Price in invoice line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].account_id.company_id.id == self.company_b.id, "Applied account in created invoice line is not relevant to company.")
        self.assertTrue(supplier_invoice.state == "draft", "invoice should be in draft state.")
        self.assertEqual(supplier_invoice.amount_total, 517.5, "Total amount is incorrect.")
        self.assertTrue(supplier_invoice.company_id.id == self.company_b.id, "Applied company in created invoice is incorrect.")
