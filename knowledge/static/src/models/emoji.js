/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'Emoji',
    fields: {
        emojiAsKnowledgeRandom: one('Knowledge', {
            compute() {
                if (!this.messaging || !this.messaging.knowledge) {
                    return clear();
                }
                if (['💩', '💀', '☠️', '🤮', '🖕', '🤢'].includes(this.codepoints)) {
                    return clear();
                }
                return this.messaging.knowledge;
            },
            inverse: 'randomEmojis',
        }),
    },
});
