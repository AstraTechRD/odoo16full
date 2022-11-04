# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_sepa_direct_debit.tests.common import SepaDirectDebitCommon


@tagged('post_install', '-at_install')
class TestSepaDirectDebit(SepaDirectDebitCommon):

    def test_transactions_are_confirmed_as_soon_as_mandate_is_valid(self):
        token = self._create_token(provider_ref=self.mandate.name, sdd_mandate_id=self.mandate.id)
        tx = self._create_transaction(flow='direct', token_id=token.id)

        tx._send_payment_request()
        self.assertEqual(tx.state, 'done', "SEPA transactions should be immediately confirmed.")
