/** @odoo-module */

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";

const { Component } = owl;
const favoriteMenuRegistry = registry.category("favoriteMenu");

export class InsertListSpreadsheetMenu extends Component {
    /**
     * @private
     */
    _onClick() {
        this.env.bus.trigger("insert-list-spreadsheet");
    }
}

InsertListSpreadsheetMenu.props = {};
InsertListSpreadsheetMenu.template = "spreadsheet_edition.InsertListSpreadsheetMenu";
InsertListSpreadsheetMenu.components = { DropdownItem };

favoriteMenuRegistry.add(
    "insert-list-spreadsheet-menu",
    {
        Component: InsertListSpreadsheetMenu,
        groupNumber: 4,
        isDisplayed: ({ config, isSmall }) =>
            !isSmall && config.actionType === "ir.actions.act_window" && config.viewType === "list",
    },
    { sequence: 5 }
);
