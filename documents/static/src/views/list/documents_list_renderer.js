/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";

import { useService } from "@web/core/utils/hooks";
import { DocumentsInspector } from "../inspector/documents_inspector";
import { FileUploadProgressContainer } from "@web/core/file_upload/file_upload_progress_container";
import { FileUploadProgressDataRow } from "@web/core/file_upload/file_upload_progress_record";
import { DocumentsDropZone } from "../helper/documents_drop_zone";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { DocumentsActionHelper } from "../helper/documents_action_helper";
import { DocumentsAttachmentViewer } from "../helper/documents_attachment_viewer";

const { useEffect, useRef } = owl;

export class DocumentsListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.root = useRef("root");
        const { uploads } = useService("file_upload");
        this.documentUploads = uploads;

        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                const handler = (ev) => {
                    if (ev.key !== "Enter" && ev.key !== " ") {
                        return;
                    }
                    const row = ev.target.closest(".o_data_row");
                    const record = row && this.props.list.records.find((rec) => rec.id === row.dataset.id);
                    if (!record) {
                        return;
                    }
                    const options = {};
                    if (ev.key === " ") {
                        options.isKeepSelection = true;
                    }
                    ev.stopPropagation();
                    ev.preventDefault();
                    record.onRecordClick(ev, options);
                };
                el.addEventListener("keydown", handler);
                return () => {
                    el.removeEventListener("keydown", handler);
                };
            },
            () => [this.root.el]
        );
    }

    get hasSelectors() {
        return this.props.allowSelectors;
    }


    getDocumentsInspectorProps() {
        return {
            selection: this.props.list.selection,
            count: this.props.list.model.useSampleModel ? 0 : this.props.list.count,
            fileSize: this.props.list.fileSize,
            archInfo: this.props.archInfo,
            withFilePreview: !this.env.documentsView.previewStore.documentList || !this.env.documentsView.previewStore.documentList.exists(),
        };
    }
}

// We need the actual event when clicking on a checkbox (to support multi select), only accept onClick
export class DocumentsListRendererCheckBox extends CheckBox {
    /**
     * @override
     */
    onChange(ev) {}

    /**
     * @override
     */
    onClick(ev) {
        if (ev.target.tagName !== "INPUT") {
            return;
        }
        this.props.onChange(ev);
    }
}

DocumentsListRenderer.template = "documents.DocumentsListRenderer";
DocumentsListRenderer.recordRowTemplate = "documents.DocumentsListRenderer.RecordRow";

DocumentsListRenderer.components = Object.assign({}, ListRenderer.components, {
    DocumentsInspector,
    DocumentsListRendererCheckBox,
    FileUploadProgressContainer,
    FileUploadProgressDataRow,
    DocumentsDropZone,
    DocumentsActionHelper,
    DocumentsAttachmentViewer,
});
