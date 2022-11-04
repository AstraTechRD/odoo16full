# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.tests import tagged


@tagged('appointment_ui', '-at_install', 'post_install')
class WebsiteAppointmentUITest(AppointmentCommon):

    def _create_invite_test_data(self):
        super()._create_invite_test_data()
        self.all_apts += self.env['appointment.type'].create({
            'name': 'Unpublished',
            'category': 'website',
            'is_published': False,
        })

    def test_share_multi_appointment_types_with_unpublished(self):
        self._create_invite_test_data()
        self.invite_all_apts.write({
            'appointment_type_ids': self.all_apts,
        })

        self.authenticate(None, None)
        res = self.url_open(self.invite_all_apts.book_url)
        self.assertEqual(res.status_code, 200, "Response should = OK")
