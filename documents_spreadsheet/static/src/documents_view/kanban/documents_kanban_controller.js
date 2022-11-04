/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DocumentsKanbanController } from "@documents/views/kanban/documents_kanban_controller";
import { DocumentsSpreadsheetControllerMixin } from "../documents_spreadsheet_controller_mixin";

patch(DocumentsKanbanController.prototype, "documents_spreadsheet_documents_kanban_controller", DocumentsSpreadsheetControllerMixin);
