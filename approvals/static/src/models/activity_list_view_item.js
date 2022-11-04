/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/activity_list_view_item';

registerPatch({
    name: 'ActivityListViewItem',
    fields: {
        approvalView: one('ApprovalView', {
            compute() {
                if (this.activity.approval) {
                    return {};
                }
                return clear();
            },
            inverse: 'activityListViewItemOwner',
        }),
        hasEditButton: {
            compute() {
                if (this.approvalView) {
                    return false;
                }
                return this._super();
            }
        },
        hasMarkDoneButton: {
            compute() {
                if (this.approvalView) {
                    return false;
                }
                return this._super();
            },
        },
    }
});
