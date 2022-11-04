/** @odoo-module **/

import { StreamPostDashboard } from '@social/js/stream_post_kanban_dashboard';

import { patch } from '@web/core/utils/patch';

patch(StreamPostDashboard.prototype, 'social_youtube.StreamPostDashboard', {

    /**
     * We do not want to display audience information for Youtube account.
     * @override
     */
    _hasAudience(account) {
        return account.media_type !== 'youtube' && this._super(...arguments);
    },

    /**
     * We do not want to display engagement information for Youtube account.
     * @override
     */
    _hasEngagement(account) {
        return account.media_type !== 'youtube' && this._super(...arguments);
    },

    /**
     * We do not want to display stories information for Youtube account.
     * @override
     */
    _hasStories(account) {
        return account.media_type !== 'youtube' && this._super(...arguments);
    },

});
