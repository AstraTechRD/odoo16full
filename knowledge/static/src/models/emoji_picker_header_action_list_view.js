/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'EmojiPickerHeaderActionListView',
    fields: {
        /**
         * Adds an action list in emoji picker to remove icon.
         */
        removeActionView: one('EmojiPickerHeaderActionView', {
            compute() {
                if (!this.emojiPickerView) {
                    return clear();
                }
                if (this.emojiPickerView.popoverViewOwner.knowledgeOwnerAsEmojiPicker) {
                    return {};
                }
                return clear();
            },
            inverse: 'ownerAsRemove',
        }),
    },
});
