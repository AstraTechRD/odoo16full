/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/activity_list_view_item';



registerPatch({
    name: 'ActivityListViewItem',
    fields: {
        hasMarkDoneButton: {
            compute() {
                if (this.activity.category === 'sign_request') {
                    return false;
                }
                return this._super();
            },
        },
    },
    recordMethods: {
        async onClickRequestSign() {
            const webRecord = this.webRecord;
            const activity = this.activity;
            const thread = activity.thread;
            this.activityListViewOwner.popoverViewOwner.delete();
            await activity.requestSignature();
            if (thread.exists()) {
                webRecord.model.load({ resId: thread.id });
            }
        },
    },
});
