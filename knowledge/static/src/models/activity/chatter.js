/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import core from 'web.core';

registerPatch({
    name: 'Chatter',
    recordMethods: {
        onClickChatterSearchArticle(event) {
            core.bus.trigger("openMainPalette", {
                searchValue: "?",
            });
        },
    },
});
