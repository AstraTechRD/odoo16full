# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, HttpCase, tagged
from odoo import Command

from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged('post_install', '-at_install')
class TestTabletWorkorderHr(TestMrpCommon, HttpCase):
    def _get_client_action_url(self, workorder_id):
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.tablet_client_action")
        return '/web?debug=assets#action=%s&active_id=%s' % (action['id'], workorder_id)

    def test_production_with_employee(self):
        self.env['mrp.workcenter'].search([]).write({
            'allow_employee': True,
            'employee_ids': [
                Command.create({
                    'name': 'Arthur Fu',
                    'pin': '1234',
                }),
                Command.create({
                    'name': 'Thomas Nific',
                    'pin': '5678',
                })
            ]
        })
        self.env['stock.lot'].create([{
            'product_id': self.product_6.id,
            'name': 'sn1',
            'company_id': self.env.company.id,
        }])
        picking_type = self.env.ref('stock.warehouse0').manu_type_id
        self.bom_3.operation_ids[0].quality_point_ids = [
            Command.create({
                'product_ids': self.product_6.ids,
                'picking_type_ids': picking_type.ids,
                'operation_id': self.bom_3.operation_ids[0],
                'test_type_id': self.env.ref('quality.test_type_instructions').id,
                'note': "this is the first note",
                'title': "Instruction 1",
            }),
            Command.create({
                'product_ids': self.product_6.ids,
                'picking_type_ids': picking_type.ids,
                'operation_id': self.bom_3.operation_ids[0],
                'test_type_id': self.env.ref('quality.test_type_instructions').id,
                'note': "this is the second note",
                'title': "Instruction 2",
            }),
            Command.create({
                'product_ids': self.product_6.ids,
                'picking_type_ids': picking_type.ids,
                'operation_id': self.bom_3.operation_ids[0],
                'test_type_id': self.env.ref('quality.test_type_instructions').id,
                'note': "this is the third note",
                'title': "Instruction 3",
            }),
        ]

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.product_6
        production = mrp_order_form.save()
        production.action_confirm()
        production.action_assign()
        production.button_plan()
        production.qty_producing = 2
        self.assertEqual(len(production.workorder_ids.check_ids), 3)
        wo = production.workorder_ids[0]
        wo.button_start()
        url = self._get_client_action_url(wo.id)

        self.start_tour(url, 'test_production_with_employee', login='admin', timeout=20)
        employee1 = self.env['hr.employee'].search([
            ('name', '=', 'Arthur Fu'),
        ])
        employee2 = self.env['hr.employee'].search([
            ('name', '=', 'Thomas Nific'),
        ])
        self.assertEqual(len(wo.time_ids), 2)
        self.assertTrue(wo.time_ids[0].employee_id, employee1)
        self.assertTrue(wo.time_ids[1].employee_id, employee2)
