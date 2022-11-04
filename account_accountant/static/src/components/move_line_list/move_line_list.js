/** @odoo-module **/


const { useState } = owl;

import { WebClientViewAttachmentViewContainer } from "@mail/components/web_client_view_attachment_view_container/web_client_view_attachment_view_container";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { insert } from '@mail/model/model_field_command';
import { SIZES } from '@web/core/ui/ui_service';

export class AccountMoveLineListController extends ListController {
    setup() {
        super.setup();
        this.messaging = useService("messaging");
        this.ui = useService("ui");
        this.attachmentPreviewState = useState({
            previewEnabled: !this.env.searchModel.context.disable_preview && this.ui.size >= SIZES.XXL,
            displayAttachment: true,
            selectedRecord: false,
            thread: null,
        });
        useBus(this.ui.bus, "resize", this.evaluatePreviewEnabled);
    }

    togglePreview() {
        this.attachmentPreviewState.displayAttachment = !this.attachmentPreviewState.displayAttachment;
    }

    evaluatePreviewEnabled() {
        this.attachmentPreviewState.previewEnabled = !this.env.searchModel.context.disable_preview && this.ui.size >= SIZES.XXL;
    }

    setSelectedRecord(accountMoveLineData) {
        this.attachmentPreviewState.selectedRecord = accountMoveLineData;
        this.setThread(this.attachmentPreviewState.selectedRecord);
    }

    async setThread(accountMoveLineData) {
        if (!accountMoveLineData || !accountMoveLineData.data.move_attachment_ids.records.length) {
            this.attachmentPreviewState.thread = null;
            return;
        }
        const attachments = insert(
            accountMoveLineData.data.move_attachment_ids.records.map(
                attachment => ({ id: attachment.resId, mimetype: attachment.data.mimetype }),
            ),
        );
        const messaging = await this.messaging.get();
        // As the real thread is AccountMove and the attachment are from AccountMove
        // We prevent this hack to leak into the WebClientViewAttachmentViewContainer here
        // by declaring the model as account.move instead of account.move.line
        const thread = messaging.models['Thread'].insert({
            attachments,
            id: accountMoveLineData.data.move_id[0],
            model: accountMoveLineData.fields["move_id"].relation,
        });
        thread.update({ mainAttachment: thread.attachments[0] });
        this.attachmentPreviewState.thread = thread;
    }
}
AccountMoveLineListController.template = 'account_accountant.MoveLineListView';
AccountMoveLineListController.components = {
    ...ListController.components,
    WebClientViewAttachmentViewContainer,
};

class AccountMoveLineListRenderer extends ListRenderer {
    onCellClicked(record, column, ev) {
        this.props.setSelectedRecord(record);
        super.onCellClicked(record, column, ev);
    }

    findFocusFutureCell(cell, cellIsInGroupRow, direction) {
        const futureCell = super.findFocusFutureCell(cell, cellIsInGroupRow, direction);
        if (futureCell) {
            const dataPointId = futureCell.closest('tr').dataset.id;
            const record = this.props.list.records.filter(x=>x.id === dataPointId)[0];
            this.props.setSelectedRecord(record);
        }
        return futureCell;
    }
}
AccountMoveLineListRenderer.props = [...ListRenderer.props, "setSelectedRecord?"];
export const AccountMoveLineListView = {
    ...listView,
    Renderer: AccountMoveLineListRenderer,
    Controller: AccountMoveLineListController,
};

registry.category("views").add('account_move_line_list', AccountMoveLineListView);
