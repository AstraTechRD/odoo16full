/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";

import { preSuperSetup, useDocumentView } from "@documents/views/hooks";

export class DocumentsKanbanController extends KanbanController {
    setup() {
        preSuperSetup();
        super.setup(...arguments);
        const properties = useDocumentView({
            getSelectedDocumentsElements: () => this.root.el.querySelectorAll(".o_kanban_record.o_record_selected"),
        });
        Object.assign(this, properties);
    }
}
DocumentsKanbanController.template = "documents.DocumentsKanbanView";
