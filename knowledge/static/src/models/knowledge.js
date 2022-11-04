/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

/**
 * Models the state in the scope of the module 'knowledge'.
 */
registerModel({
    name: 'Knowledge',
    recordMethods: {
        /**
         * @param {EmojiView} emojiView 
         */
        async onClickEmoji(emojiView) {
            const emoji = emojiView.emoji;
            await this.messaging.rpc({
                model: 'knowledge.article',
                method: 'write',
                args: [[this.currentArticle.id], { icon: emoji.codepoints }],
            });
            this.messaging.messagingBus.trigger('knowledge_add_emoji', { article: this.currentArticle, emoji });
            this.update({ emojiPickerPopoverView: clear() });
        },
        async onClickRemoveEmoji() {
            await this.messaging.rpc({
                model: 'knowledge.article',
                method: 'write',
                args: [[this.currentArticle.id], { icon: false }],
            });
            this.messaging.messagingBus.trigger('knowledge_remove_emoji', { article: this.currentArticle });
            this.update({ emojiPickerPopoverView: clear() });
        },
    },
    fields: {
        randomEmojis: many('Emoji', {
            inverse: 'emojiAsKnowledgeRandom',
        }),
        currentArticle: one('KnowledgeArticle'),
        emojiPickerPopoverAnchorRef: attr(),
        emojiPickerPopoverView: one('PopoverView', {
            inverse: 'knowledgeOwnerAsEmojiPicker',
            isCausal: true,
        }),
    },
});
