/** @odoo-module **/

import { useBus, useService } from "@web/core/utils/hooks";
import { escape, sprintf } from "@web/core/utils/strings";
import { memoize } from "@web/core/utils/functions";
import { useSetupView } from "@web/views/view_hook";
import { insert } from "@mail/model/model_field_command";
import { PdfManager } from "@documents/owl/components/pdf_manager/pdf_manager";
import { x2ManyCommands } from "@web/core/orm_service";
import { ShareFormViewDialog } from "@documents/views/helper/share_form_view_dialog";

const { EventBus, onWillStart, markup, reactive, useComponent, useEnv, useRef, useSubEnv } = owl;

/**
 * Controller/View hooks
 */

// Small hack, memoize uses the first argument as cache key, but we need the orm which will not be the same.
const loadMaxUploadSize = memoize((_null, orm) => orm.call("documents.document", "get_document_max_upload_limit"));

/**
 * To be executed before calling super.setup in view controllers.
 */
export function preSuperSetup() {
    const component = useComponent();
    const props = component.props;
    // Root state is shared between views to keep the selection
    if (props.globalState && props.globalState.documentsRootState) {
        if (!props.state) {
            props.state = {};
        }
        props.state.rootState = props.globalState.documentsRootState;
    }
    // Otherwise not available in model.env
    useSubEnv({
        documentsView: {
            bus: new EventBus(),
        },
    });
}

/**
 * Sets up the env required by documents view, as well as any other hooks.
 * Returns properties to be applied to the calling component. The code assumes that those properties are assigned to the component.
 */
export function useDocumentView(helpers) {
    const component = useComponent();
    const props = component.props;
    const root = useRef("root");
    const uploadFileInputRef = useRef("uploadFileInput");
    const orm = useService("orm");
    const notification = useService("notification");
    const dialogService = useService("dialog");
    const action = useService("action");

    // Env setup
    useSubEnv({
        model: component.model,
    });
    const env = useEnv();

    // Keep selection between views
    useSetupView({
        rootRef: root,
        getGlobalState: () => ({
            documentsRootState: component.model.root.exportState(),
        }),
    });

    let maxUploadSize;
    Object.defineProperty(component, "maxUploadSize", {
        get: () => maxUploadSize,
        set: (newVal) => {
            maxUploadSize = newVal;
        },
    });
    onWillStart(async () => {
        component.maxUploadSize = await loadMaxUploadSize(null, orm);
    });

    return {
        // Refs
        root,
        uploadFileInputRef,
        // Services
        orm,
        notification,
        dialogService,
        actionService: action,
        // Document preview
        ...useDocumentsViewFilePreviewer(helpers),
        // Document upload
        ...useDocumentsViewFileUpload(),
        // Trigger rule
        ...useTriggerRule(),
        // Helpers
        hasDisabledButtons: () => {
            const folder = env.searchModel.getSelectedFolder();
            return !folder.id || !folder.has_write_access;
        },
        // Listeners
        onClickDocumentsRequest: () => {
            action.doAction("documents.action_request_form", {
                additionalContext: {
                    default_partner_id: props.context.default_partner_id || false,
                    default_folder_id: env.searchModel.getSelectedFolderId(),
                    default_tag_ids: [x2ManyCommands.replaceWith(env.searchModel.getSelectedTagIds())],
                },
                fullscreen: env.isSmall,
                onClose: async () => env.model.load(),
            });
        },
        onClickDocumentsAddUrl: () => {
            action.doAction("documents.action_url_form", {
                additionalContext: {
                    default_partner_id: props.context.default_partner_id || false,
                    default_folder_id: env.searchModel.getSelectedFolderId(),
                    default_tag_ids: [x2ManyCommands.replaceWith(env.searchModel.getSelectedTagIds())],
                    default_res_id: props.context.default_res_id || false,
                    default_res_model: props.context.default_res_model || false,
                },
                fullscreen: env.isSmall,
                onClose: async () => env.model.load(),
            });
        },
        onClickShareDomain: async () => {
            const act = await orm.call("documents.share", "open_share_popup", [
                {
                    domain: env.searchModel.domain,
                    folder_id: env.searchModel.getSelectedFolderId(),
                    tag_ids: [x2ManyCommands.replaceWith(env.searchModel.getSelectedTagIds())],
                    type: env.model.root.selection.length ? "ids" : "domain",
                    document_ids: env.model.root.selection.length
                        ? [[6, 0, await env.model.root.getResIds(true)]]
                        : false,
                },
            ]);
            let shareResId = act.res_id;
            let saved = false;
            const close = dialogService.add(
                ShareFormViewDialog,
                {
                    resModel: "documents.share",
                    resId: shareResId,
                    onSave: async (record) => {
                        saved = true;
                        // Copy the share link to the clipboard
                        navigator.clipboard.writeText(record.data.full_url);
                        // Show a notification to the user about the copy to clipboard
                        notification.add(env._t("The share url has been copied to your clipboard."), {
                            type: "success",
                        });
                        close();
                    },
                    onDiscard: () => {close();},
                },
                {
                    onClose: async () => {
                        if (!saved) {
                            await orm.unlink("documents.share", [shareResId]);
                        }
                    },
                }
            );
        },
    };
}

/**
 * Hook to setup the file previewer
 */
function useDocumentsViewFilePreviewer({ getSelectedDocumentsElements }) {
    const component = useComponent();
    const env = useEnv();
    const bus = env.documentsView.bus;

    env.documentsView.previewStore = reactive({
        inspectedDocuments: [],
        attachmentViewer: null,
    });

    const onOpenDocumentsPreview = async ({ documents, mainDocument, isPdfSplit, rules, hasPdfSplit }) => {
        const messaging = await env.services.messaging.get();
        const openPdfSplitter = (documents) => {
            let newDocumentIds = [];
            component.dialogService.add(
                PdfManager,
                {
                    documents: documents.map((doc) => doc.data),
                    rules: rules.map((rule) => rule.data),
                    onProcessDocuments: ({ documentIds, ruleId, exit }) => {
                        if (documentIds && documentIds.length) {
                            newDocumentIds = [...new Set(newDocumentIds.concat(documentIds))];
                        }
                        if (ruleId) {
                            component.triggerRule(documentIds, ruleId, !exit);
                        }
                    },
                },
                {
                    onClose: async () => {
                        if (!newDocumentIds.length) {
                            return;
                        }
                        await component.model.load();
                        const records = component.model.root.records;
                        let count = 0;
                        for (const record of records) {
                            if (!newDocumentIds.includes(record.resId)) {
                                continue;
                            }
                            record.onRecordClick(null, {
                                isKeepSelection: count++ !== 0,
                                isRangeSelection: false,
                            });
                        }
                        component.model.notify();
                    },
                }
            );
        };
        if (isPdfSplit) {
            openPdfSplitter(documents);
            return;
        }
        const documentsRecords = ((documents.length === 1 && component.model.root.records) || documents).map((rec) => {
            return messaging.models["Document"].insert({
                id: rec.resId,
                attachmentId: rec.data.attachment_id && rec.data.attachment_id[0],
                name: rec.data.name,
                mimetype: rec.data.mimetype,
                url: rec.data.url,
                displayName: rec.data.display_name,
                record: rec,
            });
        });
        // If there is a scrollbar we don't want it whenever the previewer is opened
        if (component.root.el) {
            component.root.el.querySelector(".o_documents_view").classList.add("overflow-hidden");
        }
        const selectedDocument = documentsRecords.find((rec) => rec.id === (mainDocument || documents[0]).resId);
        const documentList = messaging.models["DocumentList"].insert({
            documents: documentsRecords,
            initialRecordSelectionLength: documents.length,
            pdfManagerOpenCallback: (documents) => {
                openPdfSplitter(documents);
            },
            onDeleteCallback: () => {
                component.env.documentsView.previewStore.documentList = null;
                // Restore selection
                if (documents.length > 1) {
                    for (const rec of documents) {
                        rec.toggleSelection(true);
                    }
                }
                // We want to focus on the first selected document's element
                const elements = getSelectedDocumentsElements();
                if (elements.length) {
                    elements[0].focus();
                }
                if (component.root.el) {
                    component.root.el.querySelector(".o_documents_view").classList.remove("overflow-hidden");
                }
            },
            onSelectDocument: (record) => {
                for (const rec of component.model.root.selection) {
                    rec.selected = false;
                }
                record.toggleSelection(true);
            },
        });
        documentList.update({
            attachmentViewer: insert({ hasPdfSplit: hasPdfSplit || true }),
            selectedDocument: selectedDocument,
        });
        for (const rec of component.model.root.selection) {
            rec.selected = false;
        }
        selectedDocument.record.toggleSelection(true);
        component.env.documentsView.previewStore.documentList = documentList;
    };

    useBus(bus, "documents-open-preview", async (ev) => {
        component.onOpenDocumentsPreview(ev.detail);
    });
    useBus(bus, "documents-close-preview", () => {
        if (
            component.env.documentsView.previewStore.documentList &&
            component.env.documentsView.previewStore.documentList.exists()
        ) {
            component.env.documentsView.previewStore.documentList.delete();
        }
    });

    return {
        onOpenDocumentsPreview,
    };
}

/**
 * Hook to setup file upload
 */
function useDocumentsViewFileUpload() {
    const component = useComponent();
    const env = useEnv();
    const bus = env.documentsView.bus;
    const notification = useService("notification");
    const fileUpload = useService("file_upload");

    const handleUploadError = (result) => {
        notification.add(result.error, {
            title: env._t("Error"),
            sticky: true,
        });
    };

    let wasUsingSampleModel = false;
    useBus(fileUpload.bus, "FILE_UPLOAD_ADDED", () => {
        if (env.model.useSampleModel) {
            wasUsingSampleModel = true;
            env.model.useSampleModel = false;
        }
    });

    useBus(fileUpload.bus, "FILE_UPLOAD_ERROR", async (ev) => {
        const { upload } = ev.detail;
        if (wasUsingSampleModel) {
            wasUsingSampleModel = false;
            env.model.useSampleModel = true;
        }
        if (upload.state !== "error") {
            return;
        }
        handleUploadError({
            error: env._t("An error occured while uploading."),
        });
    });

    useBus(fileUpload.bus, "FILE_UPLOAD_LOADED", async (ev) => {
        wasUsingSampleModel = false;
        const { upload } = ev.detail;
        const xhr = upload.xhr;
        const result =
            xhr.status === 200
                ? JSON.parse(xhr.response)
                : {
                      error: sprintf(env._t("status code: %s, message: %s"), xhr.status, xhr.response),
                  };
        if (result.error) {
            handleUploadError(result);
        } else {
            env.model.useSampleModel = false;
            await env.model.load();
            if (!result.ids) {
                return;
            }
            const records = env.model.root.records;
            let count = 0;
            for (const record of records) {
                if (!result.ids.includes(record.resId)) {
                    continue;
                }
                record.onRecordClick(null, {
                    isKeepSelection: count++ !== 0,
                    isRangeSelection: false,
                });
            }
        }
    });

    const uploadFiles = async ({ files, folderId, recordId, context, tagIds }) => {
        if (component.maxUploadSize && [...files].some((file) => file.size > component.maxUploadSize)) {
            return notification.add(env._t("File is too large."), {
                type: "danger",
            });
        }
        await fileUpload.upload("/documents/upload_attachment", files, {
            buildFormData: (formData) => {
                formData.append("folder_id", folderId);
                if (recordId) {
                    formData.append("document_id", recordId);
                }
                formData.append("tag_ids", tagIds);
                if (context) {
                    for (const key of [
                        "default_owner_id",
                        "default_partner_id",
                        "default_res_id",
                        "default_res_model",
                    ]) {
                        if (context[key]) {
                            formData.append(key.replace("default_", ""), context[key]);
                        }
                    }
                }
            },
            displayErrorNotification: false,
        });
    };

    useBus(bus, "documents-upload-files", (ev) => {
        ev.detail.context = ev.detail.context || component.props.context;
        component.uploadFiles(ev.detail);
    });

    return {
        uploadFiles,
        onFileInputChange: async (ev) => {
            if (!ev.target.files.length) {
                return;
            }
            await component.uploadFiles({
                files: ev.target.files,
                folderId: env.searchModel.getSelectedFolderId(),
                recordId: false,
                context: component.props.context,
                tagIds: env.searchModel.getSelectedTagIds(),
            });
            ev.target.value = "";
        },
    };
}

/**
 * Trigger rule hook.
 * NOTE: depends on env.model being set
 */
export function useTriggerRule() {
    const env = useEnv();
    const orm = useService("orm");
    const notification = useService("notification");
    const action = useService("action");
    return {
        triggerRule: async (documentIds, ruleId, preventReload = false) => {
            const result = await orm.call("documents.workflow.rule", "apply_actions", [[ruleId], documentIds]);
            if (result && typeof result === "object") {
                if (result.hasOwnProperty("warning")) {
                    notification.add(
                        markup(`<ul>${result["warning"]["documents"].map((d) => `<li>${escape(d)}</li>`).join("")}</ul>`),
                        {
                            title: result["warning"]["title"],
                            type: "danger",
                        }
                    );
                    if (!preventReload) {
                        await env.model.load();
                    }
                } else if (!preventReload) {
                    await action.doAction(result, {
                        onClose: async () => await env.model.load(),
                    });
                    return;
                }
            } else if (!preventReload) {
                await env.model.load();
            }
        },
    };
}
