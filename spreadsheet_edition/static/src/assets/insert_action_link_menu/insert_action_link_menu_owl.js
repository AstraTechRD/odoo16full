/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { SpreadsheetSelectorDialog } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_dialog";


const { Component } = owl;
const favoriteMenuRegistry = registry.category("favoriteMenu");

/**
 * Insert a link to a view in spreadsheet
 * @extends Component
 */
export class InsertViewSpreadsheet extends Component {
    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.dialogManager = useService("dialog");
    }

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    linkInSpreadsheet() {
        const actionToLink = this.getViewDescription();
        // do action with action link
        const actionOptions = {
            preProcessingAction: "insertLink",
            preProcessingActionData: actionToLink,
        };

        this.dialogManager.add(SpreadsheetSelectorDialog, {
            type: "LINK",
            actionOptions,
            name: this.env.config.getDisplayName(),
        });
    }

    getViewDescription() {
        const { resModel } = this.env.searchModel;
        const { views = [] } = this.env.config;
        const { context } = this.env.searchModel.getIrFilterValues();
        const action = {
            domain: this.env.searchModel.domain,
            context,
            modelName: resModel,
            views: views.map(([, type]) => [false, type]),
        };
        return {
            viewType: this.env.config.viewType,
            action,
        };
    }
}

InsertViewSpreadsheet.props = {};
InsertViewSpreadsheet.template = "spreadsheet_edition.InsertActionSpreadsheet";
InsertViewSpreadsheet.components = { DropdownItem };

favoriteMenuRegistry.add(
    "insert-action-link-in-spreadsheet",
    {
        Component: InsertViewSpreadsheet,
        groupNumber: 4,
        isDisplayed: ({ config, isSmall }) =>
            !isSmall && config.actionType === "ir.actions.act_window",
    },
    { sequence: 1 }
);
