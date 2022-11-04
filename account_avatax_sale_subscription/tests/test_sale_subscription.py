from odoo.tests.common import tagged
from odoo.addons.account_avatax.tests.common import TestAccountAvataxCommon
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


@tagged("-at_install", "post_install")
class TestSaleSubscriptionAvalara(TestAccountAvataxCommon, TestSubscriptionCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner = cls.user_portal.partner_id
        partner.with_company(cls.fp_avatax.company_id).property_account_position_id = cls.fp_avatax
        partner.country_id = cls.env.ref('base.us')
        partner.zip = '94134'
        partner.state_id = cls.env.ref('base.state_us_5') # California

    def test_01_subscription_avatax_called(self):
        self.env.ref('product.product_category_all').avatax_category_id = self.env.ref('account_avatax.D0000000')
        self.subscription.action_confirm()

        with self._capture_request({'lines': [], 'summary': []}) as capture:
            invoices = self.subscription.with_context(auto_commit=False)._create_recurring_invoice(automatic=True)

        self.assertEqual(
            capture.val and capture.val['json']['referenceCode'],
            invoices[0].name,
            'Should have queried avatax for the right taxes on the new invoice.'
        )

    def test_02_subscription_do_payment(self):
        invoice_values = self.subscription._prepare_invoice()
        new_invoice = self.env["account.move"].create(invoice_values)

        payment_method = self.env['payment.token'].create({
            'payment_details': 'Jimmy McNulty',
            'partner_id': self.subscription.partner_id.id,
            'provider_id': self.provider.id,
            'provider_ref': 'Omar Little'
        })

        with self._capture_request({'lines': [], 'summary': []}) as capture:
            self.subscription._do_payment(payment_method, new_invoice)

        self.assertEqual(
            capture.val and capture.val['json']['referenceCode'],
            new_invoice.name,
            'Should have queried avatax before initiating the payment transaction.'
        )
