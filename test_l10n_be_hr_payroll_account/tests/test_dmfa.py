# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from odoo.tests import common, tagged
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('dmfa')
class TestDMFA(common.TransactionCase):

    def test_dmfa(self):
        user = mail_new_test_user(self.env, login='blou', groups='hr_payroll.group_hr_payroll_manager,fleet.fleet_group_manager')

        belgian_company = self.env['res.company'].create({
            'name': 'My Belgian Company - TEST',
            'country_id': self.env.ref('base.be').id,
        })

        lap_address = self.env['res.partner'].create({
            'name': 'Laurie Poiret',
            'street': '58 rue des Wallons',
            'city': 'Louvain-la-Neuve',
            'zip': '1348',
            'country_id': self.env.ref("base.be").id,
            'phone': '+0032476543210',
            'email': 'laurie.poiret@example.com',
            'company_id': belgian_company.id,
        })

        lap = self.env['hr.employee'].create({
            'name': 'Laurie Poiret',
            'marital': 'single',
            'address_home_id': lap_address.id,
            'resource_calendar_id': self.env.ref("resource.resource_calendar_std_38h").id,
            'company_id': belgian_company.id,
        })
        company = lap.company_id
        user.company_ids = [(4, company.id)]
        lap.address_id = lap.company_id.partner_id
        company.dmfa_employer_class = 456
        company.onss_registration_number = 45645
        company.onss_company_id = 45645
        self.env['l10n_be.dmfa.location.unit'].with_user(user).create({
            'company_id': lap.company_id.id,
            'code': 123,
            'partner_id': lap.address_id.id,
        })
        dmfa = self.env['l10n_be.dmfa'].with_user(user).create({
            'reference': 'TESTDMFA',
            'company_id': belgian_company.id
        })
        dmfa.with_context(dmfa_skip_signature=True).generate_dmfa_xml_report()
        self.assertFalse(dmfa.error_message)
        self.assertEqual(dmfa.validation_state, 'done')
