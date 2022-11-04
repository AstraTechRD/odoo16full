/** @odoo-module **/

import { sprintf } from "@web/core/utils/strings";
import { _t } from "web.core";
import { inspectorFields } from "./inspector/documents_inspector";

export const DocumentsModelMixin = (component) => class extends component {
    /**
     * Add inspector fields to the list of fields to load
     * @override
     */
    setup(params) {
        _.defaults(params.activeFields, _.pick(params.fields, inspectorFields));
        inspectorFields.forEach((field) => {
            const fieldInfo = params.activeFields[field];
            fieldInfo.options = fieldInfo.options || {};
            fieldInfo.attrs = fieldInfo.attrs || {};
            fieldInfo.rawAttrs = fieldInfo.rawAttrs || {};
            // Domains in params.fields is in array format while in string format for activeFields
            fieldInfo.domain = (typeof fieldInfo.domain === "string" && fieldInfo.domain) || "[]";
        });
        params.activeFields.available_rule_ids = Object.assign({}, params.activeFields.available_rule_ids, {
            fieldsToFetch: {
                id: {
                    type: "integer",
                    options: {
                        always_reload: true,
                    },
                },
                display_name: {
                    type: "string",
                    options: {
                        always_reload: true,
                    },
                },
                note: {
                    type: "string",
                    options: {
                        always_reload: true,
                    },
                },
                limited_to_single_record: {
                    type: "boolean",
                    options: {
                        always_reload: true,
                    },
                },
                create_model: {
                    type: "string",
                    options: {
                        always_reload: true,
                    },
                },
            },
        });
        super.setup(...arguments);
    }
};

export const DocumentsDataPointMixin = (component) => class extends component {
    /**
     * Keep selection
     * @override
     */
    setup(_params, state) {
        super.setup(...arguments);
        if (this.resModel === "documents.document") {
            this.originalSelection = state.selection;
        }
    }

    /**
     * @override
     */
    exportState() {
        return {
            ...super.exportState(...arguments),
            selection: (this.selection || []).map((rec) => rec.resId),
        };
    }

    /**
     * Also load the total file size
     * @override
     */
    async load() {
        const selection = this.selection;
        if (selection && selection.length > 0) {
            this.originalSelection = selection.map((rec) => rec.resId);
        }
        const res = await super.load(...arguments);
        if (this.resModel !== "documents.document") {
            return res;
        }
        this.model.env.bus.trigger("documents-close-preview");
        if (this.originalSelection && this.originalSelection.length > 0 && this.records) {
            const originalSelection = new Set(this.originalSelection);
            this.records.forEach((rec) => {
                rec.selected = originalSelection.has(rec.resId);
            });
            delete this.originalSelection;
        }
        let size = 0;
        if (this.groups) {
            size = this.groups.reduce((size, group) => {
                return size + group.aggregates.file_size;
            }, 0);
        } else if (this.records) {
            size = this.records.reduce((size, rec) => {
                return size + rec.data.file_size;
            }, 0);
        }
        size /= 1000 * 1000; // in MB
        this.fileSize = Math.round(size * 100) / 100;
        return res;
    }

    /**
     * Remove the confirmation dialog upon multiSave + keep selection.
     * Warning: we do remove some validation -> see original DynamicList._multiSave
     * @override
     */
    async _multiSave(record, changes = undefined) {
        if (this.blockUpdate) {
            return;
        }
        changes = changes || record.getChanges();
        if (!changes) {
            return;
        }
        const resIds = this.selection.map((rec) => rec.resId);
        try {
            const context = this.context;
            await this.model.orm.write(this.resModel, resIds, changes, { context });
            this.invalidateCache();
            await Promise.all(this.selection.map((rec) => rec.load()));
            this.model.notify();
        } catch (_) {
            if (record.getChanges()) {
                record.discard();
            }
        }
    }
};

export const DocumentsRecordMixin = (component) => class extends component {

    isPdf() {
        return this.data.mimetype === "application/pdf" || this.data.mimetype === "application/pdf;base64";
    }

    hasThumbnail() {
        return this.data.thumbnail_status === "present";
    }

    isViewable() {
        return (
            [
                "image/bmp",
                "image/gif",
                "image/jpeg",
                "image/png",
                "image/svg+xml",
                "image/tiff",
                "image/x-icon",
                "application/javascript",
                "application/json",
                "text/css",
                "text/html",
                "text/plain",
                "application/pdf",
                "application/pdf;base64",
                "audio/mpeg",
                "video/x-matroska",
                "video/mp4",
                "video/webm",
            ].includes(this.data.mimetype) ||
            (this.data.url && this.data.url.includes("youtu"))
        );
    }

    /**
     * Upon clicking on a record, we want to select it and unselect other records.
     */
    onRecordClick(ev, options = {}) {
        const isKeepSelection =
            options.isKeepSelection !== undefined ? options.isKeepSelection : ev.ctrlKey || ev.metaKey;
        const isRangeSelection = options.isRangeSelection !== undefined ? options.isRangeSelection : ev.shiftKey;

        const root = this.model.root;
        const anchor = root._documentsAnchor;
        if (!isRangeSelection || root.selection.length === 0) {
            root._documentsAnchor = this;
        }

        // Make sure to keep the record if we were in a multi select
        const isMultiSelect = root.selection.length > 1;
        let thisSelected = !this.selected;
        if (isRangeSelection && anchor) {
            const indexFrom = root.records.indexOf(root.records.find((rec) => rec.resId === anchor.resId));
            const indexTo = root.records.indexOf(this);
            const lowerIdx = Math.min(indexFrom, indexTo);
            const upperIdx = Math.max(indexFrom, indexTo) + 1;
            root.selection.forEach((rec) => (rec.selected = false));
            for (let idx = lowerIdx; idx < upperIdx; idx++) {
                root.records[idx].selected = true;
            }
            thisSelected = true;
        } else if (!isKeepSelection && (isMultiSelect || thisSelected)) {
            root.selection.forEach((rec) => {
                rec.selected = false;
            });
            thisSelected = undefined;
        }
        this.toggleSelection(thisSelected);
    }

    /**
     * Called when starting to drag kanban/list records
     */
    async onDragStart(ev) {
        if (!this.selected) {
            this.onRecordClick(ev, { isKeepSelection: false, isRangeSelection: false });
        }
        const root = this.model.root;
        const foldersById = this.model.env.searchModel.getFolders().reduce((agg, folder) => {
            agg[folder.id] = folder;
            return agg;
        }, {});
        const draggableRecords = root.selection.filter(
            (record) => (!record.data.lock_uid || record.data.lock_uid[0] === this.context.uid) && foldersById[record.data.folder_id[0]].has_write_access
        );
        if (draggableRecords.length === 0) {
            ev.preventDefault();
            return;
        }
        const lockedCount = draggableRecords.reduce((count, record) => {
            return count + (record.data.lock_uid && record.data.lock_uid[0] !== this.context.uid);
        }, 0);
        ev.dataTransfer.setData(
            "o_documents_data",
            JSON.stringify({
                recordIds: draggableRecords.map((record) => record.resId),
                lockedCount,
            })
        );
        let dragText;
        if (draggableRecords.length === 1) {
            dragText = draggableRecords[0].data.name ? draggableRecords[0].data.display_name : _t("Unnamed");
        } else if (lockedCount > 0) {
            dragText = sprintf(_t("%s Documents (%s locked)"), draggableRecords.length, lockedCount);
        } else {
            dragText = sprintf(_t("%s Documents"), draggableRecords.length);
        }
        const newElement = document.createElement("span");
        newElement.classList.add("o_documents_drag_icon");
        newElement.innerText = dragText;
        document.body.append(newElement);
        ev.dataTransfer.setDragImage(newElement, -5, -5);
        setTimeout(() => newElement.remove());
    }
};
