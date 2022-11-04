/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

/**
 * Models a knowledge article.
 */
registerModel({
    name: 'KnowledgeArticle',
    fields: {
        id: attr({
            identifying: true,
        }),
    },
});
