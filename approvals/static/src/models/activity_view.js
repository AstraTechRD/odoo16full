/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'ActivityView',
    fields: {
        approvalView: one('ApprovalView', {
            compute() {
                if (this.activity.approval) {
                    return {};
                }
                return clear();
            },
            inverse: 'activityViewOwner',
        }),
    },
});
