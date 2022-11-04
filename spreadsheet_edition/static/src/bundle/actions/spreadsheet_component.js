/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import Dialog from "web.OwlDialog";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { useService } from "@web/core/utils/hooks";

import { DEFAULT_LINES_NUMBER } from "@spreadsheet/helpers/constants";

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";

const { onMounted, onWillUnmount, useExternalListener, useState, useSubEnv, onWillStart } = owl;
const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

const { Spreadsheet, Model } = spreadsheet;

const tags = new Set();

export default class SpreadsheetComponent extends LegacyComponent {
    setup() {
        this.orm = useService("orm");
        const user = useService("user");
        this.ui = useService("ui");
        this.action = useService("action");
        this.notifications = useService("notification");

        this.props.exposeSpreadsheet(this);

        useSubEnv({
            newSpreadsheet: this.newSpreadsheet.bind(this),
            makeCopy: this.makeCopy.bind(this),
            download: this._download.bind(this),
            getLinesNumber: this._getLinesNumber.bind(this),
            notifyUser: this.notifyUser.bind(this),
            raiseError: this.raiseError.bind(this),
            editText: this.editText.bind(this),
            askConfirmation: this.askConfirmation.bind(this),
            loadCurrencies: this.loadCurrencies.bind(this),
        });

        useSetupAction({
            beforeLeave: this._onLeave.bind(this),
        });

        useExternalListener(window, "beforeunload", this._onLeave.bind(this));

        this.state = useState({
            dialog: {
                isDisplayed: false,
                title: undefined,
                isEditText: false,
                errorText: undefined,
                inputContent: undefined,
                isEditInteger: false,
                inputIntegerContent: undefined,
            },
        });

        const dataSources = new DataSources(this.orm);

        this.model = new Model(
            migrate(this.props.data),
            {
                evalContext: { env: this.env, orm: this.orm },
                transportService: this.props.transportService,
                client: {
                    id: uuidGenerator.uuidv4(),
                    name: user.name,
                    userId: user.uid,
                },
                mode: this.props.isReadonly ? "readonly" : "normal",
                snapshotRequested: this.props.snapshotRequested,
                dataSources,
            },
            this.props.stateUpdateMessages
        );

        if (this.env.debug) {
            spreadsheet.__DEBUG__ = spreadsheet.__DEBUG__ || {};
            spreadsheet.__DEBUG__.model = this.model;
        }

        this.model.on("unexpected-revision-id", this, () => {
            if (this.props.onUnexpectedRevisionId) {
                this.props.onUnexpectedRevisionId();
            }
        });
        dataSources.addEventListener("data-source-updated", () => {
            const sheetId = this.model.getters.getActiveSheetId();
            this.model.dispatch("EVALUATE_CELLS", { sheetId });
        });
        if (this.props.showFormulas) {
            this.model.dispatch("SET_FORMULA_VISIBILITY", { show: true });
        }

        this.dialogContent = undefined;
        this.pivot = undefined;
        this.confirmDialog = () => true;

        onWillStart(async () => {
            if (this.props.asyncInitCallback) {
                await this.props.asyncInitCallback(this.model);
            }
        });

        onMounted(() => {
            if (this.props.initCallback) {
                this.props.initCallback(this.model);
            }
            this.model.on("update", this, () => {
                if (this.props.spreadsheetSyncStatus) {
                    this.props.spreadsheetSyncStatus({
                        synced: this.model.getters.isFullySynchronized(),
                        numberOfConnectedUsers: this.getConnectedUsers(),
                    });
                }
            });
        });

        onWillUnmount(() => this._onLeave());
    }

    exposeSpreadsheet(spreadsheet) {
        this.spreadsheet = spreadsheet;
    }

    /**
     * Return the number of connected users. If one user has more than
     * one open tab, it's only counted once.
     * @return {number}
     */
    getConnectedUsers() {
        return new Set(
            [...this.model.getters.getConnectedClients().values()].map((client) => client.userId)
        ).size;
    }

    /**
     * Open a dialog to ask a confirmation to the user.
     *
     * @param {string} content Content to display
     * @param {Function} confirm Callback if the user press 'Confirm'
     */
    askConfirmation(content, confirm) {
        this.dialogContent = content;
        this.confirmDialog = () => {
            confirm();
            this.closeDialog();
        };
        this.state.dialog.isDisplayed = true;
    }

    /**
     * Ask the user to edit a text
     *
     * @param {string} title Title of the popup
     * @param {Function} callback Callback to call with the entered text
     * @param {Object} options Options of the dialog. Can contain a placeholder and an error message.
     */
    editText(title, callback, options = {}) {
        this.dialogContent = undefined;
        this.state.dialog.title = title && title.toString();
        this.state.dialog.errorText = options.error && options.error.toString();
        this.state.dialog.isEditText = true;
        this.state.inputContent = options.placeholder;
        this.confirmDialog = () => {
            this.closeDialog();
            callback(this.state.inputContent);
        };
        this.state.dialog.isDisplayed = true;
    }

    _getLinesNumber(callback) {
        this.dialogContent = _t("Select the number of records to insert");
        this.state.dialog.title = _t("Re-insert list");
        this.state.dialog.isEditInteger = true;
        this.state.dialog.inputIntegerContent = DEFAULT_LINES_NUMBER;
        this.confirmDialog = () => {
            this.closeDialog();
            callback(this.state.dialog.inputIntegerContent);
        };
        this.state.dialog.isDisplayed = true;
    }

    /**
     * Close the dialog.
     */
    closeDialog() {
        this.dialogContent = undefined;
        this.confirmDialog = () => true;
        this.state.dialog.title = undefined;
        this.state.dialog.errorText = undefined;
        this.state.dialog.isDisplayed = false;
        this.state.dialog.isEditText = false;
        this.state.dialog.isEditInteger = false;
        document.querySelector(".o-grid").focus();
    }

    /**
     * Load currencies from database
     */
    async loadCurrencies() {
        const odooCurrencies = await this.orm.searchRead(
            "res.currency", // model
            [], // domain
            ["symbol", "full_name", "position", "name", "decimal_places"], // fields
            {
                // opts
                order: "active DESC, full_name ASC",
                context: { active_test: false },
            }
        );
        return odooCurrencies.map((currency) => {
            return {
                code: currency.name,
                symbol: currency.symbol,
                position: currency.position || "after",
                name: currency.full_name || _t("Currency"),
                decimalPlaces: currency.decimal_places || 2,
            };
        });
    }

    /**
     * Retrieve the spreadsheet_data and the thumbnail associated to the
     * current spreadsheet
     */
    getSaveData() {
        const data = this.model.exportData();
        return {
            data,
            revisionId: data.revisionId,
            thumbnail: this.getThumbnail(),
        };
    }

    getThumbnail() {
        const dimensions = spreadsheet.SPREADSHEET_DIMENSIONS;
        const canvas = document.querySelector("canvas");
        const canvasResizer = document.createElement("canvas");
        const size = this.props.thumbnailSize;
        canvasResizer.width = size;
        canvasResizer.height = size;
        const canvasCtx = canvasResizer.getContext("2d");
        // use only 25 first rows in thumbnail
        const sourceSize = Math.min(
            25 * dimensions.DEFAULT_CELL_HEIGHT,
            canvas.width,
            canvas.height
        );
        canvasCtx.drawImage(
            canvas,
            dimensions.HEADER_WIDTH - 1,
            dimensions.HEADER_HEIGHT - 1,
            sourceSize,
            sourceSize,
            0,
            0,
            size,
            size
        );
        return canvasResizer.toDataURL().replace("data:image/png;base64,", "");
    }
    /**
     * Make a copy of the current document
     */
    makeCopy() {
        const { data, thumbnail } = this.getSaveData();
        this.props.onMakeCopy({ data, thumbnail });
    }
    /**
     * Create a new spreadsheet
     */
    newSpreadsheet() {
        this.props.onNewSpreadsheet();
    }

    /**
     * Downloads the spreadsheet in xlsx format
     */
    async _download() {
        this.ui.block();
        try {
            await this.action.doAction({
                type: "ir.actions.client",
                tag: "action_download_spreadsheet",
                params: {
                    orm: this.orm,
                    name: this.props.name,
                    data: this.model.exportData(),
                    stateUpdateMessages: [],
                },
            });
        } finally {
            this.ui.unblock();
        }
    }

    /**
     * Adds a notification to display to the user
     * @param {{text: string, tag: string}} notification
     */
    notifyUser(notification) {
        if (tags.has(notification.tag)) {
            return;
        }
        this.notifications.add(notification.text, {
            type: "warning",
            sticky: true,
            onClose: () => tags.delete(notification.tag),
        });
        tags.add(notification.tag);
    }

    /**
     * Open a dialog to display an error message to the user.
     *
     * @param {string} content Content to display
     */
    raiseError(content) {
        this.dialogContent = content;
        this.confirmDialog = this.closeDialog;
        this.state.dialog.isDisplayed = true;
    }

    _onLeave() {
        if (this.alreadyLeft) {
            return;
        }
        this.alreadyLeft = true;
        this.model.leaveSession();
        this.model.off("update", this);
        if (!this.props.isReadonly) {
            this.props.onSpreadsheetSaved(this.getSaveData());
        }
    }
}

SpreadsheetComponent.template = "spreadsheet_edition.SpreadsheetComponent";
SpreadsheetComponent.components = { Spreadsheet, Dialog };
Spreadsheet._t = _t;
SpreadsheetComponent.props = {
    name: String,
    data: Object,
    thumbnailSize: Number,
    isReadonly: { type: Boolean, optional: true },
    snapshotRequested: { type: Boolean, optional: true },
    showFormulas: { type: Boolean, optional: true },
    stateUpdateMessages: { type: Array, optional: true },
    asyncInitCallback: {
        optional: true,
        type: Function,
    },
    initCallback: {
        optional: true,
        type: Function,
    },
    transportService: {
        optional: true,
        type: Object,
    },
    spreadsheetSyncStatus: {
        optional: true,
        type: Function,
    },
    onDownload: {
        optional: true,
        type: Function,
    },
    onUnexpectedRevisionId: {
        optional: true,
        type: Function,
    },
    onMakeCopy: {
        type: Function,
    },
    onSpreadsheetSaved: {
        type: Function,
    },
    onNewSpreadsheet: {
        type: Function,
    },
    exposeSpreadsheet: {
        type: Function,
        optional: true,
    },
};
SpreadsheetComponent.defaultProps = {
    isReadonly: false,
    snapshotRequested: false,
    showFormulas: false,
    stateUpdateMessages: [],
    exposeSpreadsheet: () => {},
    onDownload: () => {},
};
