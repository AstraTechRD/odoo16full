/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/webclient/actions/action_hook";

import { UNTITLED_SPREADSHEET_NAME } from "@spreadsheet/helpers/constants";
import { initCallbackRegistry } from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

import { LegacyComponent } from "@web/legacy/legacy_component";
import { loadSpreadsheetDependencies } from "@spreadsheet/helpers/helpers";

/**
 * @typedef SpreadsheetRecord
 * @property {number} id
 * @property {string} name
 * @property {string} raw
 * @property {Object[]} revisions
 * @property {boolean} snapshot_requested
 * @property {Boolean} isReadonly
 */

const { onMounted, onWillStart, useState } = owl;
export class AbstractSpreadsheetAction extends LegacyComponent {
    setup() {
        if (!this.props.action.params) {
            // the action is coming from a this.trigger("do-action", ... ) of owl (not wowl and not legacy)
            this.params = this.props.action.context;
        } else {
            // the action is coming from wowl
            this.params = this.props.action.params;
        }
        this.isEmptySpreadsheet = !(this.params.spreadsheet_id || this.params.active_id);
        this.resId =
            this.params.spreadsheet_id ||
            this.params.active_id || // backward compatibility. spreadsheet_id used to be active_id
            (this.props.state && this.props.state.resId); // used when going back to a spreadsheet via breadcrumb
        this.router = useService("router");
        this.actionService = useService("action");
        this.notifications = useService("notification");
        this.orm = useService("orm");
        useSetupAction({
            getLocalState: () => {
                return {
                    resId: this.resId,
                };
            },
        });
        this.state = useState({
            spreadsheetName: UNTITLED_SPREADSHEET_NAME,
        });

        onWillStart(() => this.onWillStart());
        onMounted(() => this.onMounted());
    }

    async onWillStart() {
        // if we are returning to the spreadsheet via the breadcrumb, we don't want
        // to do all the "creation" options of the actions
        if (!this.props.state) {
            [this.resId] = await Promise.all([
                this._createAddSpreadsheetData(),
                loadSpreadsheetDependencies(),
            ]);
        }
        const [record] = await Promise.all([this._fetchData(), loadSpreadsheetDependencies()]);
        this._initializeWith(record);
    }

    async _createAddSpreadsheetData() {
        let resId = this.resId;
        if (this.params.alwaysCreate) {
            resId = this._createSpreadsheetRecord();
        }
        if (this.params.preProcessingAction) {
            const initCallbackGenerator = initCallbackRegistry
                .get(this.params.preProcessingAction)
                .bind(this);
            this.initCallback = await initCallbackGenerator(this.params.preProcessingActionData);
        }
        if (this.params.preProcessingAsyncAction) {
            const initCallbackGenerator = initCallbackRegistry
                .get(this.params.preProcessingAsyncAction)
                .bind(this);
            this.asyncInitCallback = await initCallbackGenerator(
                this.params.preProcessingAsyncActionData
            );
        }
        return resId;
    }

    onMounted() {
        this.router.pushState({ spreadsheet_id: this.resId });
        this.env.config.setDisplayName(this.state.spreadsheetName);
    }

    /**
     * @protected
     * @abstract
     * @param {SpreadsheetRecord} record
     */
    _initializeWith(record) {
        throw new Error("not implemented by children");
    }

    /**
     * @protected
     * @returns {Promise<number>}
     */
    async _createSpreadsheetRecord() {
        throw new Error("not implemented by children");
    }

    async _onMakeCopy() {
        throw new Error("not implemented by children");
    }
    async _onNewSpreadsheet() {
        throw new Error("not implemented by children");
    }
    async _onSpreadsheetSaved() {
        throw new Error("not implemented by children");
    }
    async _onSpreadSheetNameChanged() {
        throw new Error("not implemented by children");
    }

    /**
     * @returns {Promise<SpreadsheetRecord>}
     */
    async _fetchData() {
        throw new Error("not implemented by children");
    }

    /**
     * Open a spreadsheet
     * @private
     */
    _openSpreadsheet(spreadsheet_id) {
        this.notifications.add(this.notificationMessage, {
            type: "info",
            sticky: false,
        });
        this.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: this.props.action.tag,
                params: { spreadsheet_id },
            },
            { clear_breadcrumbs: true }
        );
    }
}
