/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'EmojiView',
    recordMethods: {
        /**
         * Overrides click on emoji view so it's handled in the context of a
         * knowledge article. Useful to determine the resulting state of a click
         * on an emoji in this context.
         *
         * @override
         */
        onClick(ev) {
            if (!this.emojiGridItemViewOwner.emojiGridRowViewOwner) {
                return;
            }
            if (this.emojiGridItemViewOwner.emojiGridRowViewOwner.emojiGridViewOwner.emojiPickerViewOwner.popoverViewOwner.knowledgeOwnerAsEmojiPicker) {
                this.emojiGridItemViewOwner.emojiGridRowViewOwner.emojiGridViewOwner.emojiPickerViewOwner.popoverViewOwner.knowledgeOwnerAsEmojiPicker.onClickEmoji(this);
                return;
            }
            return this._super(ev);
        },
    },
});
