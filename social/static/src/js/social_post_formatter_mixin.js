/** @odoo-module **/

import MailEmojisMixin from '@mail/js/emojis_mixin';

const SocialPostFormatterRegex = {
    REGEX_AT: /\B@([\w\dÀ-ÿ-.]+)/g,
    REGEX_HASHTAG: /(^|\s|<br>)#([a-zA-Z\d\-_]+)/g,
    REGEX_URL: /http(s)?:\/\/(www\.)?[a-zA-Z0-9@:%_+~#=~#?&/=\-;!.]{3,2000}/g,
};

export const SocialPostFormatterMixin = Object.assign({}, SocialPostFormatterRegex, {

    /**
     * Add emojis support
     * Wraps links, #hashtag and @tag around anchors
     * Regex from: https://stackoverflow.com/questions/19484370/how-do-i-automatically-wrap-text-urls-in-anchor-tags
     *
     * @param {String} value
     * @private
     */
    _formatPost(value) {
        // add emojis support and escape HTML
        value = MailEmojisMixin._formatText(value);

        // highlight URLs
        value = value.replace(
            SocialPostFormatterRegex.REGEX_URL,
            "<a href='$&' target='_blank' rel='noreferrer noopener'>$&</a>");

        return value;
    },

    _getMediaType() {
        return this.props && this.props.mediaType || 
            this.record && this.record.media_type.raw_value ||
            this.originalPost && this.originalPost.media_type.raw_value || '';
    }

});
