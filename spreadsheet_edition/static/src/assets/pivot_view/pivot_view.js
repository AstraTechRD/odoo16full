/** @odoo-module **/

import { PivotController } from "@web/views/pivot/pivot_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { removeContextUserInfo, PERIODS } from "@spreadsheet_edition/assets/helpers";

import { _t } from "@web/core/l10n/translation";
import { SpreadsheetSelectorDialog } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_dialog";

const { onWillStart } = owl;

patch(PivotController.prototype, "pivot_spreadsheet", {
    setup() {
        this._super.apply(this, arguments);
        this.userService = useService("user");
        this.notification = useService("notification");
        this.actionService = useService("action");
        onWillStart(async () => {
            this.canInsertPivot = await this.userService.hasGroup("base.group_system");
        });
    },

    onInsertInSpreadsheet() {
        let name = this.model.metaData.title;
        const groupBy =
            this.model.metaData.fullColGroupBys[0] || this.model.metaData.fullRowGroupBys[0];
        if (groupBy) {
            let [field, period] = groupBy.split(":");
            period = PERIODS[period];
            name +=
                ` ${_t("by")} ` +
                this.model.metaData.fields[field].string +
                (period ? ` (${period})` : "");
        }
        const actionOptions = {
            preProcessingAsyncAction: "insertPivot",
            preProcessingAsyncActionData: {
                data: this.model.data,
                metaData: this.model.metaData,
                searchParams: {
                    ...this.model.searchParams,
                    context: removeContextUserInfo(this.model.searchParams.context),
                },
                name,
            },
        };
        const params = {
            type: "PIVOT",
            name,
            actionOptions,
        };
        this.env.services.dialog.add(SpreadsheetSelectorDialog, params);
    },
});
