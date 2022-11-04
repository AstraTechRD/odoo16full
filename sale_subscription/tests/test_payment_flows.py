# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged('post_install', '-at_install')
class TestSubscriptionPaymentFlows(PaymentHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })
        cls.user_with_so_access = cls.env['res.users'].create({
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
            'login': 'user_a_pouet',
            'password': 'user_a_pouet',  # may the min password length burn in hell
            'name': 'User A',
        })
        cls.user_without_so_access = cls.env['res.users'].create({
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
            'login': 'user_b_pouet',
            'password': 'user_b_pouet',
            'name': 'User B',
        })
        # Portal access rule currently relies on mail follower(s) of the order
        cls.order._message_subscribe(partner_ids=[cls.user_with_so_access.partner_id.id])

    def _my_sub_assign_token(self, **values):
        url = self._build_url(f"/my/subscription/assign_token/{self.order.id}")
        with mute_logger('odoo.addons.base.models.ir_rule', 'odoo.http'):
            return self._make_json_rpc_request(
                url,
                data=values,
            )

    def _assertNotFound(self, response):
        response_data = response.json()
        self.assertTrue(response_data.get('error'))
        error_data = response_data['error']
        self.assertEqual(error_data['code'], 404)
        self.assertEqual(error_data['data']['name'], 'werkzeug.exceptions.NotFound')

    def test_assign_token_route_with_so_access(self):
        """Test Assign Token Route with a user allowed to access the SO."""
        self.authenticate(self.user_with_so_access.login, self.user_with_so_access.login)
        dumb_token_so_user = self._create_token(
            partner_id=self.user_with_so_access.partner_id.id
        )
        _response = self._my_sub_assign_token(token_id=dumb_token_so_user.id)
        self.assertEqual(
            self.order.payment_token_id, dumb_token_so_user,
            "Logged Customer wasn't able to assign their token to their subscription."
        )

    def test_assign_token_without_so_access(self):
        """Test Assign Token Route with a user without access to the SO."""
        self.authenticate(
            self.user_without_so_access.login,
            self.user_without_so_access.login,
        )

        # 1) with access token
        own_token = self._create_token(
            partner_id=self.user_without_so_access.partner_id.id
        )
        response = self._my_sub_assign_token(
            token_id=own_token.id,
            access_token=self.order._portal_ensure_token(),
        )
        self.assertEqual(
            self.order.payment_token_id, own_token,
            "User wasn't able to assign their token to the subscription of another customer,"
            " even with the right access token.",
        )

        # 2) Without access token
        response = self._my_sub_assign_token(
            token_id=own_token.id,
        )
        self._assertNotFound(response)

        # 3) With wrong access token
        response = self._my_sub_assign_token(
            token_id=own_token.id,
            access_token="hohoho",
        )
        self._assertNotFound(response)

    def test_assign_token_payment_token_access(self):
        self.authenticate(self.user_with_so_access.login, self.user_with_so_access.login)

        # correct token
        dumb_token_so_user = self._create_token(
            payment_details=f'token {self.user_with_so_access.name}',
            partner_id=self.user_with_so_access.partner_id.id,
        )
        _response = self._my_sub_assign_token(token_id=dumb_token_so_user.id)
        self.assertEqual(
            self.order.payment_token_id, dumb_token_so_user,
            "Logged Customer wasn't able to assign their token to their subscription."
        )

        # token of other user --> forbidden
        other_user_token = self._create_token(
            payment_details=f'token {self.user_without_so_access.name}',
            partner_id=self.user_without_so_access.partner_id.id,
        )
        with self.assertRaises(AccessError):
            # Make sure the test correctly tests what it should be testing
            # i.e. assigning a token not belonging to the user of the request
            other_user_token.with_user(self.user_with_so_access).read()

        response = self._my_sub_assign_token(token_id=other_user_token.id)
        self._assertNotFound(response)

        # archived token --> forbidden
        archived_token = self._create_token(
            payment_details=f"archived token {self.user_with_so_access.name}",
            partner_id=self.user_with_so_access.partner_id.id,
        )
        archived_token.action_archive()
        response = self._my_sub_assign_token(token_id=archived_token.id)
        self._assertNotFound(response)

        other_user_token.unlink()
        deleted_token_id = other_user_token.id

        response = self._my_sub_assign_token(token_id=deleted_token_id)
        self._assertNotFound(response)

        self.assertEqual(
            self.order.payment_token_id, dumb_token_so_user,
            "Previous forbidden operations shouldn't have modified the SO token"
        )
