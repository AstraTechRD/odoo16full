/** @odoo-module */

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import FavoriteMenu from "web.FavoriteMenu";
import pyUtils from "web.py_utils";
import Domain from "web.Domain";
import { useService } from "@web/core/utils/hooks";
import { useModel } from "web.Model";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { SpreadsheetSelectorDialog } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_dialog";

export class InsertViewSpreadsheet extends LegacyComponent {
    setup() {
        this.model = useModel("searchModel");
        this.notification = useService("notification");
        this.dialogManager = useService("dialog");
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    /**
     * @private
     */
    linkInSpreadsheet() {
        const actionOptions = {
            preProcessingAction: "insertLink",
            preProcessingActionData: this._getViewDescription(),
        };
        this.dialogManager.add(SpreadsheetSelectorDialog, {
            type: "LINK",
            actionOptions,
            name: this.env.action.name,
        });
    }

    _getViewDescription() {
        const irFilterValues = this.model.get("irFilterValues");
        const domain = pyUtils.assembleDomains(
            [
                Domain.prototype.arrayToString(this.env.action.domain),
                Domain.prototype.arrayToString(irFilterValues.domain),
            ],
            "AND"
        );
        const action = {
            domain,
            context: irFilterValues.context,
            modelName: this.env.action.res_model,
            views: this.env.action.views.map((view) => [false, view.type]),
        };
        return {
            viewType: this.env.view.type,
            action: action,
        };
    }

    //---------------------------------------------------------------------
    // Static
    //---------------------------------------------------------------------

    /**
     * @returns {boolean}
     */
    static shouldBeDisplayed(env) {
        return env.view && env.action.type === "ir.actions.act_window" && !env.device.isMobile;
    }
}

InsertViewSpreadsheet.props = {};
InsertViewSpreadsheet.template = "spreadsheet_edition.InsertActionSpreadsheet";
InsertViewSpreadsheet.components = { DropdownItem };

FavoriteMenu.registry.add("insert-action-link-in-spreadsheet", InsertViewSpreadsheet, 1);
