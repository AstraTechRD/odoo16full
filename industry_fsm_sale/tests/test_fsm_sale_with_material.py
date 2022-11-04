# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command
from odoo.addons.industry_fsm_sale.tests.common import TestFsmFlowCommon


# This test class has to be tested at install since the flow is modified in industry_fsm_stock
# where the SO gets confirmed as soon as a product is added in an FSM task which causes the
# tests of this class to fail
class TestFsmSaleWithMaterial(TestFsmFlowCommon):

    # If the test has to be run at install, it cannot inherit indirectly from accounttestinvoicingcommon.
    # So we have to setup the test data again here.
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_revenue = cls.env['account.account'].create([{'code': '1014040', 'name': 'A', 'account_type': 'income'}])
        cls.account_expense = cls.env['account.account'].create([{'code': '101600', 'name': 'C', 'account_type': 'expense'}])
        cls.tax_sale_a = cls.env['account.tax'].create({
            'name': "tax_sale_a",
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'amount': 10.0,
        })
        cls.tax_purchase_a = cls.env['account.tax'].create({
            'name': "tax_purchase_a",
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'amount': 10.0,
        })
        cls.product_a = cls.env['product.product'].create({
            'name': 'product_a',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'property_account_income_id': cls.account_revenue.id,
            'property_account_expense_id': cls.account_expense.id,
            'taxes_id': [(6, 0, cls.tax_sale_a.ids)],
            'supplier_taxes_id': [(6, 0, cls.tax_purchase_a.ids)],
        })

    def test_change_product_selection(self):
        self.task.write({'partner_id': self.partner_1.id})
        product = self.service_product_ordered.with_context({'fsm_task_id': self.task.id})
        product.set_fsm_quantity(5)

        so = self.task.sale_order_id
        sol01 = so.order_line[-1]
        sol01.sequence = 10
        self.assertEqual(sol01.product_uom_qty, 5)

        # Manually add a line for the same product
        sol02 = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': product.id,
            'product_uom_qty': 3,
            'sequence': 20,
            'task_id': self.task.id
        })
        product.sudo()._compute_fsm_quantity()
        self.assertEqual(sol02.product_uom_qty, 3)
        self.assertEqual(product.fsm_quantity, 8)

        product.set_fsm_quantity(2)
        product.sudo()._compute_fsm_quantity()
        self.assertEqual(product.fsm_quantity, 2)
        self.assertEqual(sol01.product_uom_qty, 0)
        self.assertEqual(sol02.product_uom_qty, 2)

    def test_fsm_sale_pricelist(self):
        self.assertFalse(self.task.material_line_product_count, "No product should be linked to a new task")
        self.assertFalse(self.task.material_line_total_price)
        product = self.product_a.with_context({"fsm_task_id": self.task.id})
        self.task.write({'partner_id': self.partner_1.id})
        pricelist = self.env['product.pricelist'].create({
            'name': 'Sale pricelist',
            'discount_policy': 'with_discount',
            'item_ids': [(0, 0, {
                'compute_price': 'formula',
                'base': 'list_price',  # based on public price
                'price_discount': 10,
                'min_quantity': 2,
                'product_id': product.id,
                'applied_on': '0_product_variant',
            })]
        })
        self.assertFalse(self.task.sale_order_id)
        self.task._fsm_ensure_sale_order()
        self.assertTrue(self.task.sale_order_id)
        self.assertEqual(self.task.sale_order_id.state, 'draft')
        self.task.sale_order_id.action_confirm()
        self.assertEqual(self.task.sale_order_id.state, 'sale')
        self.task.sale_order_id.pricelist_id = pricelist

        self.assertEqual(product.fsm_quantity, 0)
        expected_product_count = 1
        product.fsm_add_quantity()
        self.assertEqual(product.fsm_quantity, expected_product_count)
        self.assertEqual(self.task.material_line_product_count, expected_product_count)

        order_line = self.task.sale_order_id.order_line.filtered(lambda l: l.product_id == product)
        self.assertEqual(order_line.price_subtotal, order_line.untaxed_amount_to_invoice)
        self.assertEqual(order_line.product_uom_qty, expected_product_count)
        self.assertEqual(order_line.price_unit, product.list_price)

        product.fsm_add_quantity()
        expected_product_count += 1
        self.assertEqual(product.fsm_quantity, expected_product_count)
        self.assertEqual(order_line.product_uom_qty, expected_product_count)
        self.assertEqual(order_line.price_subtotal, order_line.untaxed_amount_to_invoice)
        self.assertEqual(self.task.material_line_product_count, expected_product_count)

    def test_invoicing_flow(self):
        self.service_product_ordered.write({
            'detailed_type': 'service',
            'service_policy': 'ordered_prepaid',
        })
        self.service_product_delivered.write({
            'detailed_type': 'service',
            'service_policy': 'delivered_timesheet',
        })

        self.fsm_project.write({
            'timesheet_product_id': self.service_product_delivered.id,
        })

        self.task.write({
            'partner_id': self.partner_1,
        })

        self.assertFalse(self.task.sale_order_id)
        self.assertFalse(self.task.sale_line_id)
        self.assertFalse(self.task.task_to_invoice)
        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).set_fsm_quantity(1.0)
        self.assertEqual(self.task.sale_order_id.state, 'draft')
        self.assertEqual(len(self.task.sale_order_id.order_line), 1)

        first_order_line = self.task.sale_order_id.order_line
        self.assertEqual(first_order_line.product_uom_qty, 1.0)
        self.assertFalse(self.task.task_to_invoice)
        self.assertFalse(self.task.display_create_invoice_primary)
        self.assertFalse(self.task.sale_line_id)

        self.task.sale_order_id.write({
            'order_line': [
                Command.create({
                    'product_id': self.service_timesheet.id,
                    'product_uom_qty': 1.0,
                    'name': '/',
                }),
            ]
        })

        self.task.sale_order_id.action_confirm()
        self.assertEqual(len(self.task.sale_order_id.order_line), 2)
        service_timesheet_order_line = self.task.sale_order_id.order_line.filtered(lambda order_line: order_line.product_id == self.service_timesheet)
        self.task.write({
            'timesheet_ids': [
                Command.create({
                    'name': '/',
                    'unit_amount': 0.5,
                    'employee_id': self.employee_user2.id,
                    'project_id': self.task.project_id.id,
                }),
                Command.create({
                    'name': '/',
                    'unit_amount': 0.5,
                    'employee_id': self.employee_user2.id,
                    'project_id': self.task.project_id.id,
                }),
                Command.create({
                    'name': '/',
                    'unit_amount': 1.0,
                    'so_line': service_timesheet_order_line.id,
                    'is_so_line_edited': True,
                    'employee_id': self.employee_user2.id,
                    'project_id': self.task.project_id.id,
                }),
            ]
        })

        self.task.action_fsm_validate()
        self.assertEqual(len(self.task.timesheet_ids.so_line), 2)
        self.assertEqual(self.task.sale_order_id.order_line.mapped('qty_delivered'), [1.0] * 3)
        self.assertEqual(self.task.sale_line_id.product_id, self.service_product_delivered)
        self.assertEqual(self.task.sale_order_id.state, 'sale')
        self.assertEqual(len(self.task.sale_order_id.order_line), 3)
        second_order_line = self.task.sale_line_id
        self.assertEqual(second_order_line.project_id, self.fsm_project)
        self.assertEqual(second_order_line.task_id, self.task)
        self.assertTrue(second_order_line.is_service)
        self.assertEqual(second_order_line.qty_delivered_method, 'timesheet')

        self.assertTrue(self.task.task_to_invoice)
        self.assertTrue(self.task.display_create_invoice_primary)
        self.task.sale_order_id._create_invoices()
        self.assertEqual(self.task.invoice_count, 1)
        self.assertFalse(self.task.display_create_invoice_primary)

        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertTrue(self.task.display_create_invoice_primary)
        self.task.sale_order_id._create_invoices()
        self.assertEqual(self.task.invoice_count, 2)
        self.assertFalse(self.task.display_create_invoice_primary)
