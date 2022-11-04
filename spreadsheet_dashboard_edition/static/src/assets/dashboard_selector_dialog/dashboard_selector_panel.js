/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { SpreadsheetSelectorDialog } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_dialog";
import { SpreadsheetSelectorPanel } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_panel";

class DashboardSelectorPanel extends SpreadsheetSelectorPanel {
    constructor() {
        super(...arguments);
        this.actionTag = "action_edit_dashboard";
    }

    /**
     * Fetch spreadsheets according to the search domain and the pager
     * offset given as parameter.
     * @override
     * @returns {Promise<void>}
     */
    async _fetchSpreadsheets() {
        const domain = [];
        if (this.currentSearch !== "") {
            domain.push(["name", "ilike", this.currentSearch]);
        }
        const { offset, limit } = this.state.pagerProps;
        this.state.spreadsheets = await this.keepLast.add(
            this.orm.searchRead("spreadsheet.dashboard", domain, ["name", "thumbnail"], {
                offset,
                limit,
            })
        );
        this._selectItem(this.state.spreadsheets.length && this.state.spreadsheets[0].id);
    }

    /**
     * @override
     * @returns {Promise<number>}
     */
    async _fetchPagerTotal() {
        return this.orm.searchCount("spreadsheet.dashboard", []);
    }
}

patch(SpreadsheetSelectorDialog, "spreadsheet_dashboard_edition.DashboardSelectorPanel", {
    components: { ...SpreadsheetSelectorDialog.components, DashboardSelectorPanel },
});
