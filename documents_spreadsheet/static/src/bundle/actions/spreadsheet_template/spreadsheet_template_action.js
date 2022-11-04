/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _t } from "web.core";

import SpreadsheetComponent from "@spreadsheet_edition/bundle/actions/spreadsheet_component";
import { base64ToJson, jsonToBase64 } from "@spreadsheet_edition/bundle/helpers";
import { useService } from "@web/core/utils/hooks";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { DocumentsSpreadsheetControlPanel } from "@documents_spreadsheet/bundle/components/control_panel/spreadsheet_control_panel";

export class SpreadsheetTemplateAction extends AbstractSpreadsheetAction {
    setup() {
        super.setup();
        this.notificationMessage = this.env._t("New spreadsheet template created");
        this.orm = useService("orm");
    }

    exposeSpreadsheet(spreadsheet) {
        this.spreadsheet = spreadsheet;
    }

    _initializeWith(record) {
        this.spreadsheetData = base64ToJson(record.data);
        this.state.spreadsheetName = record.name;
        this.isReadonly = record.isReadonly;
    }

    /**
     * Fetch all the necessary data to open a spreadsheet template
     * @returns {Object}
     */
    async _fetchData() {
        return this.orm.call("spreadsheet.template", "fetch_template_data", [this.resId]);
    }

    /**
     * Create a new empty spreadsheet template
     * @returns {number} id of the newly created spreadsheet template
     */
    async _onNewSpreadsheet() {
        const data = {
            name: _t("Untitled spreadsheet template"),
            data: btoa("{}"),
        };
        return this.orm.create("spreadsheet.template", [data]);
    }

    /**
     * Save the data and thumbnail on the given template
     * @param {number} spreadsheetTemplateId
     * @param {Object} values values to save
     * @param {Object} values.data exported spreadsheet data
     * @param {string} values.thumbnail spreadsheet thumbnail
     */
    async _onSpreadsheetSaved({ data, thumbnail }) {
        await this.orm.write("spreadsheet.template", [this.resId], {
            data: jsonToBase64(data),
            thumbnail,
        });
    }

    /**
     * Save a new name for the given template
     * @param {Object} detail
     * @param {string} detail.name
     */
    async _onSpreadSheetNameChanged(detail) {
        const { name } = detail;
        this.state.spreadsheetName = name;
        this.env.config.setDisplayName(this.state.spreadsheetName);
        await this.orm.write("spreadsheet.template", [this.resId], {
            name,
        });
    }

    async _onMakeCopy({ data, thumbnail }) {
        const defaultValues = {
            data: jsonToBase64(data),
            thumbnail,
        };
        const id = await this.orm.call("spreadsheet.template", "copy", [this.resId], {
            default: defaultValues,
        });
        this._openSpreadsheet(id);
    }
}

SpreadsheetTemplateAction.template = "documents_spreadsheet.SpreadsheetTemplateAction";
SpreadsheetTemplateAction.components = {
    SpreadsheetComponent,
    DocumentsSpreadsheetControlPanel,
};

registry
    .category("actions")
    .add("action_open_template", SpreadsheetTemplateAction, { force: true });
