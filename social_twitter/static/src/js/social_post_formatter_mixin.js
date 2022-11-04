/** @odoo-module **/

import { SocialPostFormatterMixin } from '@social/js/social_post_formatter_mixin';

import { patch } from '@web/core/utils/patch';

/*
 * Add Twitter @tag and #hashtag support.
 * Replace all occurrences of `#hashtag` by a HTML link to a search of the hashtag
 * on the media website
 */
patch(SocialPostFormatterMixin, 'social_twitter.SocialPostFormatterMixin', {

    _formatPost(value) {
        value = this._super(...arguments);
        if (this._getMediaType() === 'twitter') {
            value = value.replace(this.REGEX_HASHTAG,
                `$1<a href='https://twitter.com/hashtag/$2?src=hash' target='_blank'>#$2</a>`);
            value = value.replace(this.REGEX_AT,
                `<a href='https://twitter.com/$1' target='_blank'>@$1</a>`);
        }
        return value;
    }

});
