# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.addons.account_avatax_sale.tests.test_avatax import TestAccountAvataxCommon
from odoo.addons.base.tests.common import HttpCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountAvataxSalePortal(TestAccountAvataxCommon, HttpCase):
    def _create_sale_order(self, partner):
        return self.env['sale.order'].create({
            'name': 'avatax test',
            'partner_id': partner.id,
            'fiscal_position_id': self.fp_avatax.id,
            'date_order': '2021-01-01',
            'order_line': [
                (0, 0, {
                    'product_id': self.product_user.id,
                    'tax_id': None,
                    'price_unit': self.product_user.list_price,
                }),
            ],
            'sale_order_option_ids': [
                (0, 0, {
                    'name': 'optional product',
                    'price_unit': 1,
                    'uom_id': self.env.ref('uom.product_uom_unit').id,
                    'product_id': self.env['product.product'].create({'name': 'optional product'}).id,
                }),
            ],
        })

    def test_01_portal_test_optional_products(self):
        """ Make sure that adding, deleting and changing the qty on optional products calls Avatax. """
        portal_partner = self.env['res.users'].sudo().search([('login', '=', 'portal')]).partner_id
        order = self._create_sale_order(portal_partner)

        # Moving the portal user to order.company_id still results in
        # request.env.company.id == 1 in the /my/quotes controller
        # when called through start_tour. To work around this disable
        # multi-company record rules just for this test.
        self.env.ref('sale.sale_order_comp_rule').active = False
        self.env.ref('sale.sale_order_line_comp_rule').active = False

        # must be sent to the user so he can see it
        order.action_quotation_sent()

        with self._capture_request({'lines': [], 'summary': []}), \
             patch('odoo.addons.account_avatax_sale.models.sale_order.SaleOrder.button_update_avatax') as mocked_button_update_avatax:
            self.start_tour('/', 'account_avatax_sale_optional_products', login='portal')
            mocked_button_update_avatax.assert_called()

            # There should be 4 calls:
            # 1/ when the quote is displayed via portal_order_page()
            # 2/ when the tour adds the optional product
            # 3/ when the tour increments the quantity on the optional product
            # 4/ when the tour deletes the optional product
            self.assertEqual(mocked_button_update_avatax.call_count, 4, 'Avatax was not called enough times during this tour.')
