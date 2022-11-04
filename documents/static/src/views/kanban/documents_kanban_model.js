/** @odoo-module **/

import session from "web.session";
import { KanbanModel } from "@web/views/kanban/kanban_model";
import { DocumentsModelMixin, DocumentsDataPointMixin, DocumentsRecordMixin } from "../documents_model_mixin";

export class DocumentsKanbanModel extends DocumentsModelMixin(KanbanModel) {}

export class DocumentsKanbanRecord extends DocumentsRecordMixin(KanbanModel.Record) {
    async onClickPreview(ev) {
        if (this.data.type === "empty") {
            // In case the file is actually empty we open the input to replace the file
            ev.stopPropagation();
            ev.currentTarget.querySelector(".o_kanban_replace_document").click();
        } else if (this.isViewable()) {
            ev.stopPropagation();
            ev.preventDefault();
            const folder = this.model.env.searchModel
                .getFolders()
                .filter((folder) => folder.id === this.data.folder_id[0]);
            const hasPdfSplit =
                (!this.data.lock_uid || this.data.lock_uid[0] === session.uid) && folder.has_write_access;
            const selection = this.model.root.selection;
            let documents = selection.length > 1 && selection.find(rec => rec === this) && selection.filter(rec => rec.isViewable()) || [this];
            await this.model.env.documentsView.bus.trigger("documents-open-preview", {
                documents,
                mainDocument: this,
                isPdfSplit: false,
                rules: this.data.available_rule_ids.records,
                hasPdfSplit,
            });
        }
    }

    async onReplaceDocument(ev) {
        if (!ev.target.files.length) {
            return;
        }
        await this.model.env.bus.trigger("documents-upload-files", {
            files: ev.target.files,
            folderId: this.data.folder_id && this.data.folder_id[0],
            recordId: this.resId,
            tagIds: this.model.env.searchModel.getSelectedTagIds(),
        });
        ev.target.value = "";
    }
}
DocumentsKanbanModel.Record = DocumentsKanbanRecord;
DocumentsKanbanModel.Group = class DocumentsKanbanGroup extends DocumentsDataPointMixin(KanbanModel.Group) {};
DocumentsKanbanModel.DynamicGroupList = class DocumentsKanbanDynamicGroupList extends DocumentsDataPointMixin(KanbanModel.DynamicGroupList) {};
DocumentsKanbanModel.DynamicRecordList = class DocumentsKanbanDynamicRecordList extends DocumentsDataPointMixin(KanbanModel.DynamicRecordList) {};
DocumentsKanbanModel.StaticList = class DocumentsKanbanStaticList extends DocumentsDataPointMixin(KanbanModel.StaticList) {};
