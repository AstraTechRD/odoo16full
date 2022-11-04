/** @odoo-module */

import { _lt, _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { sprintf } from "@web/core/utils/strings";
import { useService } from "@web/core/utils/hooks";
import { Notebook } from "@web/core/notebook/notebook";

const { Component, useState } = owl;

const LABELS = {
    PIVOT: _lt("pivot"),
    LIST: _lt("list"),
    LINK: _lt("link"),
    GRAPH: _lt("graph"),
};

const PAGE_LABELS = {
    SPREADSHEET: _lt("Spreadsheets"),
    DASHBOARD: _lt("Dashboards"),
};
/**
 * @typedef State
 * @property {Object} spreadsheets
 * @property {string} panel
 * @property {string} name
 * @property {number|false} selectedSpreadsheetId
 * @property {string} [threshold]
 * @property {Object} pagerProps
 * @property {number} pagerProps.offset
 * @property {number} pagerProps.limit
 * @property {number} pagerProps.total
 */

export class SpreadsheetSelectorDialog extends Component {
    setup() {
        /** @type {State} */
        this.state = useState({
            threshold: this.props.threshold,
            name: this.props.name,
        });
        this.actionState = {
            actionTag: undefined,
            selectedSpreadsheet: false,
            notificationMessage: "",
        };
        this.notification = useService("notification");
        this.actionService = useService("action");
    }

    /**
     * @param {"SPREADSHEET" | "DASHBOARD"} title
     */
    getPageTitle(title) {
        return PAGE_LABELS[title];
    }

    get nameLabel() {
        return sprintf(_t("Name of the %s:"), LABELS[this.props.type]);
    }

    get title() {
        return sprintf(_t("Select a spreadsheet to insert your %s."), LABELS[this.props.type]);
    }

    /**
     * @param {number|false} id
     */
    onSpreadsheetSelected({ spreadsheet, actionTag, notificationMessage }) {
        this.actionState = {
            selectedSpreadsheet: spreadsheet,
            actionTag,
            notificationMessage,
        };
    }

    _confirm() {
        const threshold = this.state.threshold ? parseInt(this.state.threshold, 10) : 0;
        const isNewItem = this.actionState.selectedSpreadsheet === false;
        const notificationMessage = isNewItem
            ? this.actionState.notificationMessage
            : sprintf(_t("New sheet inserted in '%s'"), this.actionState.selectedSpreadsheet.name);
        // make sure we send a primitive string instead of a LazyTranslatedString
        const name = this.state.name.toString();
        const actionOptions = {
            ...this.props.actionOptions,
            preProcessingAsyncActionData: {
                ...this.props.actionOptions.preProcessingAsyncActionData,
                threshold,
                name,
            },
            preProcessingActionData: {
                ...this.props.actionOptions.preProcessingActionData,
                threshold,
                name,
            },
            alwaysCreate: isNewItem,
            spreadsheet_id:
                this.actionState.selectedSpreadsheet && this.actionState.selectedSpreadsheet.id,
        };

        this.notification.add(notificationMessage, { type: "info" });
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: this.actionState.actionTag,
            params: actionOptions,
        });
        this.props.close();
    }

    _cancel() {
        this.props.close();
    }
}

SpreadsheetSelectorDialog.template = "spreadsheet_edition.SpreadsheetSelectorDialog";
SpreadsheetSelectorDialog.components = { Dialog, Notebook };
SpreadsheetSelectorDialog.props = {
    actionOptions: Object,
    type: String,
    threshold: { type: Number, optional: true },
    maxThreshold: { type: Number, optional: true },
    name: String,
    close: Function,
};
