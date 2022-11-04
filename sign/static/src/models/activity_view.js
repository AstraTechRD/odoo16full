/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'ActivityView',
    fields: {
        chatter: one('Chatter', {
            related: 'activityBoxView.chatter',
        }),
        signRequestView: one('SignRequestView', {
            compute() {
                if (this.activity.category === 'sign_request') {
                    return {};
                }
                return clear();
            },
            inverse: 'activityViewOwner',
        }),
    },
});
