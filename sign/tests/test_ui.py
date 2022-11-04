# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .sign_request_common import SignRequestCommon
import odoo.tests

from odoo.tools.misc import mute_logger
from odoo.tools.translate import WEB_TRANSLATION_COMMENT


@odoo.tests.tagged('-at_install', 'post_install')
class TestUi(odoo.tests.HttpCase, SignRequestCommon):
    def test_ui(self):
        self.start_tour("/web", 'sign_widgets_tour', login='admin')

        self.start_tour("/web", 'shared_sign_request_tour', login='admin')
        shared_sign_request = self.env['sign.request'].search([('reference', '=', 'template_1_role-Shared'), ('state', '=', 'shared')])
        self.assertTrue(shared_sign_request.exists(), 'A shared sign request should be created')
        signed_sign_request = self.env['sign.request'].search([('reference', '=', 'template_1_role'), ('state', '=', 'signed')])
        self.assertTrue(signed_sign_request.exists(), 'A signed sign request should be created')
        self.assertEqual(signed_sign_request.create_uid, self.env.ref('base.user_admin'), 'The signed sign request should be created by the admin')
        signer = self.env['res.partner'].search([('email', '=', 'mitchell.admin@public.com')])
        self.assertTrue(signer.exists(), 'A partner should exists with the email provided while signing')

    def test_translate_sign_instructions(self):
        fr_lang = self.env['res.lang'].with_context(active_test=False).search([('code', '=', 'fr_FR')])
        self.env["base.language.install"].create({
            'overwrite': True,
            'lang_ids': [(6, 0, [fr_lang.id])]
        }).lang_install()

        # Once `website` is installed, the available langs are only the ones
        # from the website, which by default is just the `en_US` lang.
        langs = self.env['res.lang'].with_context(active_test=False).search([]).get_sorted()
        self.patch(self.registry['res.lang'], 'get_available', lambda self: langs)
        self.partner_1.lang = 'fr_FR'
        sign_request = self.create_sign_request_1_role(customer=self.partner_1, cc_partners=self.env['res.partner'])
        url = f"/sign/document/{sign_request.id}/{sign_request.request_item_ids.access_token}"
        self.start_tour(url, 'translate_sign_instructions', login=None)

    def test_sign_flow(self):
        flow_template = self.template_1_role.copy()
        self.env['sign.item'].create({
            'type_id': self.env.ref('sign.sign_item_type_signature').id,
            'required': True,
            'responsible_id': self.env.ref('sign.sign_item_role_customer').id,
            'page': 1,
            'posX': 0.144,
            'posY': 0.716,
            'template_id': flow_template.id,
            'width': 0.200,
            'height': 0.050,
        })
        self.start_tour("/web", 'test_sign_flow_tour', login='admin')
