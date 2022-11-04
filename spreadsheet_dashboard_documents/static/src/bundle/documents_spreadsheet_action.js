/** @odoo-module **/

import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { _lt } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
const { topbarMenuRegistry } = spreadsheet.registries;
const { useSubEnv } = owl;

topbarMenuRegistry.addChild("add_document_to_dashboard", ["file"], {
    name: _lt("Add to dashboard"),
    sequence: 200,
    isVisible: (env) => env.canAddDocumentAsDashboard,
    action: (env) => env.createDashboardFromDocument(env.model),
});

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

patch(SpreadsheetAction.prototype, "spreadsheet_dashboard_documents.SpreadsheetAction", {
    setup() {
        this._super();
        useSubEnv({
            canAddDocumentAsDashboard: true,
            createDashboardFromDocument: this._createDashboardFromDocument.bind(this),
        });
    },

    /**
     * @param {Model} model
     * @private
     */
    _createDashboardFromDocument(model) {
        const resId = this.resId;
        const name = this.state.spreadsheetName;
        this.env.services.orm.write("documents.document", [resId], {
            raw: JSON.stringify(model.exportData()),
        });
        this.env.services.action.doAction(
            {
                name: this.env._t("Name your dashboard and select its section"),
                type: "ir.actions.act_window",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                res_model: "spreadsheet.document.to.dashboard",
            },
            {
                additionalContext: {
                    default_document_id: resId,
                    default_name: name
                },
            }
        );
    },
});
