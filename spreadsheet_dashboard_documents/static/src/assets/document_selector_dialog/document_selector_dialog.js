/** @odoo-module */

import { DocumentsSelectorPanel } from "@documents_spreadsheet/spreadsheet_selector_dialog/document_selector_panel";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class DocumentSelectorDialog extends Component {
    setup() {
        this.selectedSpreadsheet = null;
        this.orm = useService("orm");
    }

    onSpreadsheetSelected({ spreadsheet }) {
        this.selectedSpreadsheet = spreadsheet;
    }

    _confirm() {
        if (this.selectedSpreadsheet) {
            this.orm.call("spreadsheet.dashboard", "add_document_spreadsheet_to_dashboard", [
                this.props.dashboardGroupId,
                this.selectedSpreadsheet.id,
            ]);
        }
        this.props.close();
        window.location.reload();
    }

    _cancel() {
        this.props.close();
    }
}

DocumentSelectorDialog.template = "spreadsheet_dashboard_documents.DocumentSelectorDialog";
DocumentSelectorDialog.components = { Dialog, DocumentsSelectorPanel };
DocumentSelectorDialog.props = {
    close: Function,
    dashboardGroupId: Number,
};
