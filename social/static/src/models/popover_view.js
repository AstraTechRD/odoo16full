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
                if (this.socialOwnerAsEmojiPicker) {
                    return this.socialOwnerAsEmojiPicker.emojiPickerPopoverAnchorRef;
                }
                return this._super();
            },
        },
        /**
         * Determines the content of the PopoverView.
         */
        emojiPickerView: {
            compute() {
                if (this.socialOwnerAsEmojiPicker) {
                    return {};
                }
                return this._super();
            },
        },
        /**
         * Registers social emoji picker as a uniquely identifiable popover
         * view.
         */
         socialOwnerAsEmojiPicker: one('Social', {
            identifying: true,
            inverse: 'emojiPickerPopoverView',
        }),
        /**
         * Determines the position of the PopoverView.
         */
        position: {
            compute() {
                if (this.socialOwnerAsEmojiPicker) {
                    return 'bottom';
                }
                return this._super();
            },
        },
    },
});
