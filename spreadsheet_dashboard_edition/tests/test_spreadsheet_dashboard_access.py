import base64

from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user


class SpreadsheetDashboardAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.env["res.groups"].create({"name": "test group"})
        cls.user = new_test_user(cls.env, login="Raoul")
        cls.user.groups_id |= cls.group


    def test_join_new_dashboard_user(self):
        dashboard_group = self.env["spreadsheet.dashboard.group"].create({
            "name": "Dashboard group"
        })
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": "a dashboard",
                "data": base64.b64encode(b"{}"),
                "group_ids": [Command.set(self.group.ids)],
                "dashboard_group_id": dashboard_group.id,
            }
        )
        # only read access, no one ever joined this dashboard
        result = dashboard.with_user(self.user).join_spreadsheet_session()
        self.assertEqual(result["raw"], b"{}")
