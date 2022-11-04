# Part of Odoo. See LICENSE file for full copyright and licensing details.

# from odoo.fields import Markup
from odoo.tests import Form, HttpCase, tagged
from .test_workorder import TestWorkOrder


@tagged('post_install', '-at_install')
class TestPickingWorkorderClientAction(TestWorkOrder, HttpCase):
    def _get_client_action_url(self, workorder_id):
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.tablet_client_action")
        return '/web#action=%s&active_id=%s' % (action['id'], workorder_id)

    def test_add_component(self):
        self.bom_submarine.bom_line_ids.write({'operation_id': False})
        self.bom_submarine.operation_ids = False
        self.bom_submarine.write({
            'operation_ids': [(0, 0, {
                'workcenter_id': self.mrp_workcenter_3.id,
                'name': 'Manual Assembly',
                'time_cycle': 60,
                })]
            })
        self.bom_submarine.consumption = 'flexible'
        self.env['stock.lot'].create([{
            'product_id': self.submarine_pod.id,
            'name': 'sn1',
            'company_id': self.env.company.id,
        }])
        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        production = mrp_order_form.save()
        production.action_confirm()
        production.action_assign()
        production.button_plan()
        self.assertEqual(len(production.workorder_ids.check_ids), 2)
        wo = production.workorder_ids[0]
        wo.button_start()
        extra = self.env['product.product'].create({
            'name': 'extra',
            'type': 'product',
            'tracking': 'lot',
        })
        extra_bp = self.env['product.product'].create({
            'name': 'extra-bp',
            'type': 'product',
            'tracking': 'lot',
        })
        self.env['stock.lot'].create([{
            'product_id': extra.id,
            'name': 'lot1',
            'company_id': self.env.company.id,
        }, {
            'product_id': extra_bp.id,
            'name': 'lot2',
            'company_id': self.env.company.id,
        }])
        url = self._get_client_action_url(wo.id)
        self.start_tour(url, 'test_add_component', login='admin', timeout=80)

    def test_add_step(self):
        """ Add a step as instruction in the tablet view via the 'suggest
        worksheet improvement' """
        self.bom_submarine.consumption = 'flexible'
        self.env['stock.lot'].create([{
            'product_id': self.submarine_pod.id,
            'name': 'sn1',
            'company_id': self.env.company.id,
        }])
        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        production = mrp_order_form.save()
        production.action_confirm()
        production.action_assign()
        production.button_plan()
        self.assertEqual(len(production.workorder_ids.check_ids), 2)
        wo = production.workorder_ids[0]
        wo.button_start()
        url = self._get_client_action_url(wo.id)

        self.start_tour(url, 'test_add_step', login='admin', timeout=80)
        # activities = production.bom_id.activity_ids
        # self.assertEqual(len(activities), 2, 'should be 2 activities')
        # activity = activities[0]
        # self.assertEqual(activity.summary, 'BoM feedback Instructions "Cutting Machine" (%s)' % production.name)
        # self.assertEqual(activity.note, Markup('<span><b>New Step suggested by Mitchell Admin</b><br><b>Reason:</b>why am I adding a step</span>'))
        # activity = activities[1]
        # self.assertEqual(activity.summary, 'BoM feedback Register Consumed Materials "Metal cylinder" (%s)' % production.name)
        # self.assertEqual(activity.note, Markup('<span><b>New Instruction suggested by Mitchell Admin</b><br>False<br><b>Reason: my reason</b></span>'))
