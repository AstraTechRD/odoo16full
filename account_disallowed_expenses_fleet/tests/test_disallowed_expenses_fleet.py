# -*- coding: utf-8 -*-

from freezegun import freeze_time
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from odoo import Command, fields
from odoo.tests import tagged


@freeze_time('2022-07-15')
@tagged('post_install', '-at_install')
class TestAccountDisallowedExpensesFleetReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.dna_category = cls.env['account.disallowed.expenses.category'].create({
            'code': '1234',
            'name': 'DNA category',
            'rate_ids': [
                Command.create({
                    'date_from': fields.Date.from_string('2022-01-01'),
                    'rate': 10.0,
                    'company_id': cls.company_data['company'].id,
                }),
                Command.create({
                    'date_from': fields.Date.from_string('2022-04-01'),
                    'rate': 20.0,
                    'company_id': cls.company_data['company'].id,
                }),
            ],
        })

        cls.company_data['default_account_expense'].disallowed_expenses_category_id = cls.dna_category.id

        batmobile, batpod = cls.env['fleet.vehicle'].create([
            {
                'model_id': cls.env['fleet.vehicle.model'].create({
                    'name': name,
                    'brand_id': cls.env['fleet.vehicle.model.brand'].create({
                        'name': 'Wayne Enterprises',
                    }).id,
                    'vehicle_type': vehicle_type,
                    'default_fuel_type': 'hydrogen',
                }).id,
                'rate_ids': [Command.create({
                    'date_from': fields.Date.from_string('2022-01-01'),
                    'rate': rate,
                })],
            } for name, vehicle_type, rate in [('Batmobile', 'car', 30.0), ('Batpod', 'bike', 56.0)]
        ])

        bill_1 = cls.env['account.move'].create({
            'partner_id': cls.partner_a.id,
            'move_type': 'in_invoice',
            'date': fields.Date.from_string('2022-01-15'),
            'invoice_date': fields.Date.from_string('2022-01-15'),
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test',
                    'quantity': 1,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense'].id,
                }),
                Command.create({
                    'vehicle_id': batmobile.id,
                    'quantity': 1,
                    'price_unit': 200.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense'].id,
                }),
                Command.create({
                    'vehicle_id': batpod.id,
                    'quantity': 1,
                    'price_unit': 300.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense'].id,
                }),
            ],
        })

        # Create a second bill at a later date in order to have multiple rates in the annual report.
        bill_2 = cls.env['account.move'].create({
            'partner_id': cls.partner_a.id,
            'move_type': 'in_invoice',
            'date': fields.Date.from_string('2022-05-15'),
            'invoice_date': fields.Date.from_string('2022-05-15'),
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test',
                    'quantity': 1,
                    'price_unit': 400.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense'].id,
                }),
            ],
        })

        (bill_1 + bill_2).action_post()
