from odoo import api, models


class SpreadsheetDashboard(models.Model):
    _name = 'spreadsheet.dashboard'
    _inherit = ['spreadsheet.dashboard']

    def action_add_document_spreadsheet_to_dashboard(self):
        return {
            "type": "ir.actions.client",
            "tag": "action_dashboard_add_spreadsheet",
            "params": {
                "dashboardGroupId": self.env.context.get("dashboard_group_id"),
            },
        }

    @api.model
    def add_document_spreadsheet_to_dashboard(self, dashboard_group_id, document_id):
        document = self.env["documents.document"].browse(document_id)
        dashboard = self.create({
            "name": document.name,
            "dashboard_group_id": dashboard_group_id,
            "spreadsheet_snapshot": document.spreadsheet_snapshot,
        })
        revisions_data = []
        for revision_id in document.spreadsheet_revision_ids:
            revisions_data.append(revision_id.copy_data({"res_id": dashboard.id, "res_model": "spreadsheet.dashboard"})[0])
        revision_ids = self.env["spreadsheet.revision"].create(revisions_data)
        dashboard.spreadsheet_revision_ids = revision_ids
