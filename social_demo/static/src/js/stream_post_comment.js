/** @odoo-module **/

import { StreamPostCommentFacebook } from '@social_facebook/js/stream_post_comment';
import { StreamPostCommentInstagram } from '@social_instagram/js/stream_post_comment';
import { StreamPostCommentLinkedin } from '@social_linkedin/js/stream_post_comment';
import { StreamPostCommentTwitter } from '@social_twitter/js/stream_post_comment';
import { StreamPostCommentYoutube } from '@social_youtube/js/stream_post_comment';

import { patch } from '@web/core/utils/patch';

const getDemoAuthorPictureSrc = function() {
    return this.comment.from.profile_image_url_https;
};

patch(StreamPostCommentFacebook.prototype, 'social_demo.StreamPostCommentFacebook', {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentInstagram.prototype, 'social_demo.StreamPostCommentInstagram', {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentLinkedin.prototype, 'social_demo.StreamPostCommentLinkedin', {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentTwitter.prototype, 'social_demo.StreamPostCommentTwitter', {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentYoutube.prototype, 'social_demo.StreamPostCommentYoutube', {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});
