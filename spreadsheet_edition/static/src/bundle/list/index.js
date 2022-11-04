/** @odoo-module */

import { _t, _lt } from "@web/core/l10n/translation";

import spreadsheet, {
    initCallbackRegistry,
} from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

import "./autofill";
import "./operational_transform";

import ListingAllSidePanel from "./side_panels/listing_all_side_panel";
import ListAutofillPlugin from "./plugins/list_autofill_plugin";

import { insertList } from "./list_init_callback";

const { uiPluginRegistry, sidePanelRegistry, cellMenuRegistry } = spreadsheet.registries;

uiPluginRegistry.add("odooListAutofillPlugin", ListAutofillPlugin);

sidePanelRegistry.add("LIST_PROPERTIES_PANEL", {
    title: () => _t("List properties"),
    Body: ListingAllSidePanel,
});

initCallbackRegistry.add("insertList", insertList);

cellMenuRegistry.add("listing_properties", {
    name: _lt("See list properties"),
    sequence: 190,
    action(env) {
        const { col, row } = env.model.getters.getPosition();
        const sheetId = env.model.getters.getActiveSheetId();
        const listId = env.model.getters.getListIdFromPosition(sheetId, col, row);
        env.model.dispatch("SELECT_ODOO_LIST", { listId });
        env.openSidePanel("LIST_PROPERTIES_PANEL", {});
    },
    isVisible: (env) => {
        const { col, row } = env.model.getters.getPosition();
        const sheetId = env.model.getters.getActiveSheetId();
        return env.model.getters.getListIdFromPosition(sheetId, col, row) !== undefined;
    },
});
