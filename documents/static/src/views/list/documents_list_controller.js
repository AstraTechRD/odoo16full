/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";

import { preSuperSetup, useDocumentView } from "@documents/views/hooks";

export class DocumentsListController extends ListController {
    setup() {
        preSuperSetup();
        super.setup(...arguments);
        const properties = useDocumentView({
            getSelectedDocumentsElements: () =>
                this.root.el.querySelectorAll(".o_data_row.o_data_row_selected .o_list_record_selector"),
        });
        Object.assign(this, properties);
    }
}

DocumentsListController.template = "documents.DocumentsListController";
