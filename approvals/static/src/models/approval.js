/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'Approval',
    recordMethods: {
        /**
         * Approves the current `approval.approver`.
         */
        async approve() {
            const activity = this.activity;
            await this.messaging.rpc({
                model: 'approval.approver',
                method: 'action_approve',
                args: [[this.id]],
            });
            if (activity.exists()) {
                activity.delete();
            }
            if (!this.exists()) {
                return;
            }
            this.delete();
        },
        /**
         * Refuses the current `approval.approver`.
         */
        async refuse() {
            const activity = this.activity;
            await this.messaging.rpc({
                model: 'approval.approver',
                method: 'action_refuse',
                args: [[this.id]],
            });
            if (activity.exists()) {
                activity.delete();
            }
            if (!this.exists()) {
                return;
            }
            this.delete();
        },
    },
    fields: {
        activity: one('Activity', {
            inverse: 'approval',
        }),
        id: attr({
            identifying: true,
        }),
        isCurrentPartnerApprover: attr({
            default: false,
            related: 'activity.isCurrentPartnerAssignee',
        }),
        status: attr(),
    },
});
