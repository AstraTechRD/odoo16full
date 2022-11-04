/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DocumentsListModel } from "@documents/views/list/documents_list_model";

patch(DocumentsListModel.Record.prototype, "documents_spreadsheet_documents_kanban_record", {
    /**
     * @override
     */
    isViewable() {
      return this.data.handler === "spreadsheet" || this._super(...arguments);
    },
});
