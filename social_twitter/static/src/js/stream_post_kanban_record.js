/** @odoo-module **/

import { StreamPostKanbanRecord } from '@social/js/stream_post_kanban_record';
import { StreamPostCommentsTwitter } from './stream_post_comments';
import { StreamPostTwitterQuote } from './stream_post_twitter_quote';

import { patch } from '@web/core/utils/patch';
import { sprintf } from '@web/core/utils/strings';
import { useService } from '@web/core/utils/hooks';

patch(StreamPostKanbanRecord.prototype, 'social_twitter.StreamPostKanbanRecord', {

    setup() {
        this._super(...arguments);
        this.notification = useService('notification');
    },

    _onTwitterCommentsClick() {
        const postId = this.record.id.raw_value;

        this.rpc('/social_twitter/get_comments', {
            stream_post_id: postId,
        }).then((result) => {
            this.dialog.add(StreamPostCommentsTwitter, {
                title: this.env._t('Twitter Comments'),
                commentsCount: this.commentsCount,
                accountId: this.record.account_id.raw_value,
                originalPost: this.record,
                postId: postId,
                streamId: this.record.stream_id.raw_value,
                allComments: result.comments,
                comments: result.comments.slice(0, this.commentsCount),
            });
        });
    },

    _onTwitterTweetLike() {
        const userLikes = this.record.twitter_user_likes.raw_value;
        this.rpc(sprintf('social_twitter/%s/like_tweet', this.record.stream_id.raw_value), {
            tweet_id: this.record.twitter_tweet_id.raw_value,
            like: !userLikes
        });
        this._updateLikesCount('twitter_user_likes', 'twitter_likes_count');
    },

    _onTwitterRetweet(ev) {
        this.rpc(sprintf('social_twitter/%s/%s', this.record.stream_id.raw_value,
                 this.record.twitter_can_retweet.raw_value ? 'retweet' : 'unretweet'), {
            tweet_id: this.record.twitter_tweet_id.raw_value,
            stream_id: this.record.stream_id.raw_value,
        }).then((result) => {
            result = JSON.parse(result);
            if (result === true) {
                const retweetCount = this.record.twitter_can_retweet.raw_value ?
                    this.record.twitter_retweet_count.raw_value + 1 :
                    this.record.twitter_retweet_count.raw_value - 1;
                this.props.record.update({
                    'twitter_can_retweet': !this.record.twitter_can_retweet.raw_value,
                    'twitter_retweet_count': retweetCount,
                });
            } else if (result.error) {
                this.notification.add(result.error, {
                    title: this.env._t('Error'),
                    type: 'danger',
                });
            }
        });
    },

    _onTwitterQuote() {
        this.dialog.add(StreamPostTwitterQuote, {
            title: this.env._t('Quote a Tweet'),
            mediaSpecificProps: {
                accountId: this.record.account_id.raw_value,
                accountName: this.record.author_name.value,
            },
            originalPost: this.record,
            refreshStats: () => this.env.refreshStats(),
        });
    },

});
