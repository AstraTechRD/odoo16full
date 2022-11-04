/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerPatch({
    name: 'PopoverView',
    fields: {
        /**
         * Determines the anchorRef of the PopoverView.
         */
        anchorRef: {
            compute() {
                if (this.knowledgeOwnerAsEmojiPicker) {
                    return this.knowledgeOwnerAsEmojiPicker.emojiPickerPopoverAnchorRef;
                }
                return this._super();
            },
        },
        /**
         * Determines the content of the PopoverView.
         */
        emojiPickerView: {
            compute() {
                if (this.knowledgeOwnerAsEmojiPicker) {
                    return {};
                }
                return this._super();
            },
        },
        /**
         * Registers knowledge emoji picker as a uniquely identifiable popover
         * view.
         */
        knowledgeOwnerAsEmojiPicker: one('Knowledge', {
            identifying: true,
            inverse: 'emojiPickerPopoverView',
        }),
        /**
         * Determines the position of the PopoverView.
         */
        position: {
            compute() {
                if (this.knowledgeOwnerAsEmojiPicker) {
                    return 'bottom';
                }
                return this._super();
            },
        },
    },
});
