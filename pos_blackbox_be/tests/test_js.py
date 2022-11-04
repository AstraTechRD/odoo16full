# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('-at_install', 'post_install')
class WebSuite(odoo.tests.HttpCase):
    def test_01_js(self):
        self.browser_js('/web/tests?module=pos_blackbox_be.Order',"","", login='admin')
