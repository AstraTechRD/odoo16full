/** @odoo-module **/

import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'ThreadNeedactionPreviewView',
    fields: {
        /**
         * Determines whether this thread needaction preview view should have
         * the swiper feature, and if so contains the component managing this
         * feature.
         */
        swiperView: one('SwiperView', {
            compute() {
                return this.messaging.device.isSmall ? {} : clear();
            },
            inverse: 'threadNeedactionPreviewViewOwner',
        }),
    },
});
