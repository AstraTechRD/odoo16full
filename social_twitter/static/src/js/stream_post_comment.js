/** @odoo-module **/

import { StreamPostComment } from '@social/js/stream_post_comment';
import { StreamPostCommentsReplyTwitter } from './stream_post_comments_reply';

import { sprintf } from '@web/core/utils/strings';

export class StreamPostCommentTwitter extends StreamPostComment {

    //--------
    // Getters
    //--------

    get authorPictureSrc() {
        return this.comment.from.profile_image_url_https
    }

    get link() {
        return sprintf('https://www.twitter.com/%s/statuses/%s', this.comment.from.id, this.comment.id);
    }

    get authorLink() {
        return sprintf('https://twitter.com/intent/user?user_id=%s', this.comment.from.id);
    }

    get isAuthor() {
        return this.comment.from.id === this.props.mediaSpecificProps.twitterUserId;
    }

    get commentReplyComponent() {
        return StreamPostCommentsReplyTwitter;
    }

    get deleteCommentEndpoint() {
        return '/social_twitter/delete_tweet';
    }

    get isEditable() {
        return false;
    }

    get likesClass() {
        return 'fa-heart';
    }

    get commentName() {
        return this.env._t('tweet');
    }

}
