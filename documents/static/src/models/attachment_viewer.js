/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";
import { attr, one } from "@mail/model/model_field";

registerPatch({
    name: "AttachmentViewer",
    recordMethods: {
        /**
         * @override
         */
        next() {
            if (this.documentListOwner) {
                this.documentListOwner.selectNextAttachment();
                return;
            }
            return this._super();
        },
        /**
         * Called upon clicking on the "Split PDF" button
         */
        onClickPdfSplit() {
            if (this.documentListOwner) {
                this.documentListOwner.openPdfManager();
                this.close();
            }
        },
        /**
         * @override
         */
        previous() {
            if (this.documentListOwner) {
                this.documentListOwner.selectPreviousAttachment();
                return;
            }
            return this._super();
        },
    },
    fields: {
        attachmentViewerViewable: {
            compute() {
                if (this.documentListOwner) {
                    return this.documentListOwner.selectedDocument.attachmentViewerViewable;
                }
                return this._super();
            },
        },
        attachmentViewerViewables: {
            compute() {
                if (this.documentListOwner) {
                    return this.documentListOwner.documents.map(doc => {
                        return { documentOwner: doc };
                    });
                }
                return this._super();
            },
        },
        documentListOwner: one("DocumentList", {
            identifying: true,
            inverse: "attachmentViewer",
            isCausal: true,
        }),
        hasPdfSplit: attr({
            default: false,
        }),
        withPdfSplit: attr({
            /**
             * If the initial record selection is a single record, and the current record is a pdf, return true.
             * If the initial record selection is a list, return true if every record is a pdf.
             */
            compute() {
                if (!this.documentListOwner) {
                    return false;
                }
                if (this.documentListOwner.initialRecordSelectionLength === 1) {
                    return this.attachmentViewerViewable.isPdf;
                }
                return this.attachmentViewerViewables.every(viewable => viewable.isPdf);
            },
        }),
    },
});
