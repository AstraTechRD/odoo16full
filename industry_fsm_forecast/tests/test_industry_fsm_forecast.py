# -- coding: utf-8 --
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests.common import TransactionCase

class TestFsmFlowCommon(TransactionCase):

    def test_default_forecast_project(self):
        fsm_project = self.env['project.project'].with_context(default_is_fsm=True).create({
            'name': 'Test FSM Project',
        })
        self.assertFalse(fsm_project.allow_forecast, "By default, planning for FSM project should be disabled.")
