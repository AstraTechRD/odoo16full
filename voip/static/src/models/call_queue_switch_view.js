/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { attr } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";

/**
 * Models a button in CRM leads Kanban view cards that deletes or creates call
 * activity from the related record. Call activities created this way are
 * included in the "Next activities" tab of the softphone.
 *
 * The term "call queue" refers to the list of the elements in the "Next
 * activities" tab.
 */
registerModel({
    name: "CallQueueSwitchView",
    lifecycleHooks: {
        _created() {
            // useful to update the state of this view when the record is
            // deleted from the "Next Activities" tab
            this.messaging.messagingBus.addEventListener("on-call-activity-removed", this._onCallActivityRemoved);
        },
        _willDelete() {
            this.messaging.messagingBus.removeEventListener("on-call-activity-removed", this._onCallActivityRemoved);
        },
    },
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        async onClickAddToCallQueueButton(ev) {
            if (this.hasPendingRpc) {
                return;
            }
            await this.performRpcToRecord("create_call_in_queue");
            this.update({ isRecordInCallQueue: true });
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickRemoveFromCallQueueButton(ev) {
            if (this.hasPendingRpc) {
                return;
            }
            await this.performRpcToRecord("delete_call_in_queue");
            this.update({ isRecordInCallQueue: false });
        },
        /**
         * @param {string} methodName The name of voip.queue.mixin method to be
         * called.
         */
        async performRpcToRecord(methodName) {
            this.update({ hasPendingRpc: true });
            await this.messaging.rpc({
                model: this.recordResModel,
                method: methodName,
                args: [this.recordResId],
            });
            this.update({ hasPendingRpc: clear() });
        },
        /**
         * @param {Object} param0
         * @param {integer} param0.detail The resId of the deleted record.
         */
        _onCallActivityRemoved({ detail: resId }) {
            if (this.recordResId !== resId) {
                return;
            }
            this.update({ isRecordInCallQueue: false });
        },
    },
    fields: {
        /**
         * Useful to prevent other unnecessary RPCs being sent if one is already
         * in progress.
         */
        hasPendingRpc: attr({
            default: false,
        }),
        id: attr({
            identifying: true,
        }),
        isRecordInCallQueue: attr(),
        onClickHandler: attr({
            compute() {
                return this[this.isRecordInCallQueue ? "onClickRemoveFromCallQueueButton" : "onClickAddToCallQueueButton"];
            }
        }),
        operatorIconClasses: attr({
            compute() {
                return this.isRecordInCallQueue ? "fa-minus text-danger" : "fa-plus text-success";
            },
        }),
        /**
         * The resId of the record to be added to or to be removed from the
         * call queue.
         */
        recordResId: attr(),
        /**
         * The resModel of the record to be added to or to be removed from the
         * call queue.
         */
        recordResModel: attr(),
        title: attr({
            compute() {
                if (this.isRecordInCallQueue) {
                    return this.env._t("Remove from Call Queue");
                }
                return this.env._t("Add to Call Queue");
            },
        }),
    },
});
