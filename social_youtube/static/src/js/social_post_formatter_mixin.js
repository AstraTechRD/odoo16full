/** @odoo-module **/

import { SocialPostFormatterMixin } from '@social/js/social_post_formatter_mixin';

import { patch } from '@web/core/utils/patch';

/*
 * Add Youtube #hashtag support.
 * Replace all occurrences of `#hashtag` by a HTML link to a search of the hashtag
 * on the media website
 */
patch(SocialPostFormatterMixin, 'social_youtube.SocialPostFormatterMixin', {

    _formatPost(value) {
        value = this._super(...arguments);
        if (['youtube', 'youtube_preview'].includes(this._getMediaType())) {
            value = value.replace(this.REGEX_HASHTAG,
                `$1<a href='https://www.youtube.com/results?search_query=%23$2' target='_blank'>#$2</a>`);
        }
        return value;
    }

});
