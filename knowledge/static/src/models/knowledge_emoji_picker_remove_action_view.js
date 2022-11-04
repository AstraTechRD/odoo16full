/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

/**
 * Models specifically the remove action in the emoji picker.
 */
registerModel({
    name: 'KnowledgeEmojiPickerRemoveActionView',
    recordMethods: {
        onClick() {
            this.messaging.knowledge.onClickRemoveEmoji();
        },
    },
    fields: {
        owner: one('EmojiPickerHeaderActionView', {
            identifying: true,
            inverse: 'removeActionView',
        }),
    },
});
