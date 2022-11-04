/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { useService } from "@web/core/utils/hooks";

import SpreadsheetComponent from "@spreadsheet_edition/bundle/actions/spreadsheet_component";
import { SpreadsheetName } from "@spreadsheet_edition/bundle/actions/control_panel/spreadsheet_name";

import { UNTITLED_SPREADSHEET_NAME } from "@spreadsheet/helpers/constants";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { getDataFromTemplate } from "@documents_spreadsheet/bundle/helpers";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { DocumentsSpreadsheetControlPanel } from "../components/control_panel/spreadsheet_control_panel";

const { Component, useState } = owl;
const { createEmptyWorkbookData } = spreadsheet.helpers;

export class SpreadsheetAction extends AbstractSpreadsheetAction {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notificationMessage = this.env._t("New spreadsheet created in Documents");

        this.state = useState({
            numberOfConnectedUsers: 1,
            isSynced: true,
            isFavorited: false,
            spreadsheetName: UNTITLED_SPREADSHEET_NAME,
        });

        this.spreadsheetCollaborative = useService("spreadsheet_collaborative");
    }

    exposeSpreadsheet(spreadsheet) {
        this.spreadsheet = spreadsheet;
    }

    async onWillStart() {
        await super.onWillStart();
        this.transportService = this.spreadsheetCollaborative.getCollaborativeChannel(
            Component.env,
            "documents.document",
            this.resId
        );
    }

    /**
     * @override
     * @returns {Promise<number>}
     */
    async _createSpreadsheetRecord() {
        const data = this.params.createFromTemplateId
            ? await getDataFromTemplate(this.env, this.orm, this.params.createFromTemplateId)
            : createEmptyWorkbookData(`${this.env._t("Sheet")}1`);
        return this.orm.create("documents.document", [
            {
                name: this.params.createFromTemplateName || UNTITLED_SPREADSHEET_NAME,
                mimetype: "application/o-spreadsheet",
                handler: "spreadsheet",
                raw: JSON.stringify(data),
                folder_id: this.params.createInFolderId,
            },
        ]);
    }

    async _fetchData() {
        const record = await this.orm.call("documents.document", "join_spreadsheet_session", [
            this.resId,
        ]);
        return record;
    }

    /**
     * @override
     */
    _initializeWith(record) {
        this.state.isFavorited = record.is_favorited;
        this.spreadsheetData = JSON.parse(record.raw);
        this.stateUpdateMessages = record.revisions;
        this.snapshotRequested = record.snapshot_requested;
        this.state.spreadsheetName = record.name;
        this.isReadonly = record.isReadonly;
    }

    /**
     * @private
     * @param {Object}
     */
    async _onDownload({ name, files }) {
        await download({
            url: "/spreadsheet/xlsx",
            data: {
                zip_name: `${name}.xlsx`,
                files: JSON.stringify(files),
            },
        });
    }

    /**
     * @param {OdooEvent} ev
     * @returns {Promise}
     */
    async _onSpreadSheetFavoriteToggled(ev) {
        this.state.isFavorited = !this.state.isFavorited;
        return await this.orm.call("documents.document", "toggle_favorited", [[this.resId]]);
    }

    /**
     * Updates the control panel with the sync status of spreadsheet
     *
     * @param {Object}
     */
    _onSpreadsheetSyncStatus({ synced, numberOfConnectedUsers }) {
        this.state.isSynced = synced;
        this.state.numberOfConnectedUsers = numberOfConnectedUsers;
    }

    /**
     * Reload the spreadsheet if an unexpected revision id is triggered.
     */
    _onUnexpectedRevisionId() {
        this.actionService.doAction("reload_context");
    }

    /**
     * Create a copy of the given spreadsheet and display it
     */
    async _onMakeCopy({ data, thumbnail }) {
        const defaultValues = {
            mimetype: "application/o-spreadsheet",
            raw: JSON.stringify(data),
            spreadsheet_snapshot: false,
            thumbnail,
        };
        const id = await this.orm.call("documents.document", "copy", [this.resId], {
            default: defaultValues,
        });
        this._openSpreadsheet(id);
    }

    /**
     * Create a new sheet and display it
     */
    async _onNewSpreadsheet() {
        const data = {
            name: UNTITLED_SPREADSHEET_NAME,
            mimetype: "application/o-spreadsheet",
            raw: JSON.stringify(createEmptyWorkbookData(`${_t("Sheet")}1`)),
            handler: "spreadsheet",
        };
        const id = await this.orm.create("documents.document", [data]);
        this._openSpreadsheet(id);
    }

    async _onSpreadsheetSaved({ data, thumbnail }) {
        await this.orm.write("documents.document", [this.resId], {
            thumbnail,
            raw: JSON.stringify(data),
            mimetype: "application/o-spreadsheet",
        });
    }

    /**
     * Saves the spreadsheet name change.
     * @param {Object} detail
     * @returns {Promise}
     */
    async _onSpreadSheetNameChanged(detail) {
        const { name } = detail;
        this.state.spreadsheetName = name;
        this.env.config.setDisplayName(this.state.spreadsheetName);
        return await this.orm.write("documents.document", [this.resId], { name });
    }
}

SpreadsheetAction.template = "documents_spreadsheet.SpreadsheetAction";
SpreadsheetAction.components = {
    SpreadsheetComponent,
    DocumentsSpreadsheetControlPanel,
    SpreadsheetName,
};

registry.category("actions").add("action_open_spreadsheet", SpreadsheetAction, { force: true });
