/** @odoo-module */

import { SpreadsheetDashboardAction } from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_action";
import { patch } from "@web/core/utils/patch";

patch(
    SpreadsheetDashboardAction.prototype,
    "spreadsheet_dashboard_edition.SpreadsheetDashboardAction",
    {
        /**
         * @param {number} dashboardId
         * @returns {Promise<{ data: string, revisions: object[] }>}
         */
        async _fetchDashboardData(dashboardId) {
            const data = await this.orm.call("spreadsheet.dashboard", "join_spreadsheet_session", [
                dashboardId,
            ]);
            return { data: data.raw, revisions: data.revisions };
        },
    }
);
