/** @odoo-module **/

import { SocialPostFormatterMixin } from '@social/js/social_post_formatter_mixin';

import { patch } from '@web/core/utils/patch';

/*
 * Add LinkedIn #hashtag support.
 * Replace all occurrences of `#hashtag` by a HTML link to a search of the hashtag
 * on the media website
 */
patch(SocialPostFormatterMixin, 'social_linkedin.SocialPostFormatterMixin', {

    _formatPost(value) {
        value = this._super(...arguments);
        if (this._getMediaType() === 'linkedin') {
            value = value.replace(this.REGEX_HASHTAG,
                `$1<a href='https://www.linkedin.com/feed/hashtag/$2' target='_blank'>#$2</a>`);
        }
        return value;
    }

});
