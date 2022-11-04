/** @odoo-module */

import { _t } from "web.core";
import { AbstractBehavior } from "@knowledge/components/behaviors/abstract_behavior/abstract_behavior";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AttachToMessageMacro, UseAsAttachmentMacro } from "@knowledge/macros/file_macros";
import { sprintf } from "@web/core/utils/strings";
import { useService } from "@web/core/utils/hooks";
import utils from "web.utils";

const { markup } = owl;


export class FileBehavior extends AbstractBehavior {
    setup() {
        super.setup();
        this.dialogService = useService('dialog');
        this.knowledgeCommandsService = useService('knowledgeCommandsService');
        this.rpcService = useService('rpc');
        this.uiService = useService('ui');
        this.targetRecordInfo = this.knowledgeCommandsService.getCommandsRecordInfo();
        if (this.props.fileImage) {
            this.props.fileImage = markup(this.props.fileImage);
        }
    }
    /**
     * Callback function called when the user clicks on the "Download" button.
     * The function will simply open a link that will trigger the download of
     * the associated file. If the url is not valid, the function will display
     * an error message.
     * @param {Event} ev
     */
    async onClickDownload(ev) {
        const fileLink = this.props.anchor.querySelector('.o_knowledge_file_image > a');
        if (!fileLink || !fileLink.hasAttribute('href')) {
            return;
        }
        const title = fileLink.getAttribute('title');
        const href = fileLink.getAttribute('href');
        try {
            const response = await window.fetch(href);
            const blob = await response.blob();
            const file = new Blob([blob], {
                type: 'application/octet-stream'
            });
            const downloadLink = document.createElement('a');
            downloadLink.href = URL.createObjectURL(file);
            downloadLink.download = title;
            downloadLink.click();
        } catch {
            this.dialogService.add(AlertDialog, {
                body: sprintf(_t('Oops, the file %s could not be found. Please replace this file box by a new one to re-upload the file.'), title),
                title: _t('Missing File'),
                confirm: () => {},
                confirmLabel: _t('Ok'),
            });
        }
    }
    /**
     * Callback function called when the user clicks on the "Send as Message" button.
     * The function will execute a macro that will open the last opened form view,
     * compose a new message and attach the associated file to it.
     * @param {Event} ev
     */
    async onClickAttachToMessage(ev) {
        const fileLink = this.props.anchor.querySelector('.o_knowledge_file_image > a');
        if (!fileLink || !fileLink.hasAttribute('href')) {
            return;
        }
        const dataTransfer = new DataTransfer();
        const href = fileLink.getAttribute('href');
        try {
            const response = await window.fetch(href);
            const blob = await response.blob();
            const file = new File([blob], fileLink.getAttribute('title'), {
                type: blob.type
            });
            /**
             * dataTransfer will be used to mimic a drag and drop of
             * the file in the target record chatter.
             * @see KnowledgeMacro
             */
            dataTransfer.items.add(file);
        } catch {
            return;
        }
        const macro = new AttachToMessageMacro({
            targetXmlDoc: this.targetRecordInfo.xmlDoc,
            breadcrumbs: this.targetRecordInfo.breadcrumbs,
            data: {
                dataTransfer: dataTransfer,
            },
            services: {
                ui: this.uiService,
                dialog: this.dialogService,
            },
        });
        macro.start();
    }
    /**
     * Callback function called when the user clicks on the "Use As Attachment" button.
     * The function will execute a macro that will open the last opened form view
     * and add the associated file to the attachments of the chatter.
     * @param {Event} ev
     */
    async onClickUseAsAttachment(ev) {
        const fileLink = this.props.anchor.querySelector('.o_knowledge_file_image > a');
        if (!fileLink || !fileLink.hasAttribute('href')) {
            return;
        }
        const href = fileLink.getAttribute('href');
        let attachment;
        try {
            const response = await window.fetch(href);
            const blob = await response.blob();
            const dataURL = await utils.getDataURLFromFile(blob);
            attachment = await this.rpcService('/web_editor/attachment/add_data', {
                name: fileLink.getAttribute('title'),
                data: dataURL.split(',')[1],
                is_image: false,
                res_id: this.targetRecordInfo.resId,
                res_model: this.targetRecordInfo.resModel,
            });
        } catch {
            return;
        }
        if (!attachment) {
            return;
        }
        const macro = new UseAsAttachmentMacro({
            targetXmlDoc: this.targetRecordInfo.xmlDoc,
            breadcrumbs: this.targetRecordInfo.breadcrumbs,
            data: null,
            services: {
                ui: this.uiService,
                dialog: this.dialogService,
            },
        });
        macro.start();
    }
}

FileBehavior.template = "knowledge.FileBehavior";
FileBehavior.props = {
    ...AbstractBehavior.props,
    fileName: { type: String, optional: true },
    fileExtension: { type: String, optional: true },
    fileImage: { type: String, optional: true },
};
