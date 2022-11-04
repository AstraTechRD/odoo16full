/** @odoo-module **/

import { StreamPostKanbanRecord } from '@social/js/stream_post_kanban_record';
import { StreamPostCommentsInstagram } from './stream_post_comments';

import { patch } from '@web/core/utils/patch';

patch(StreamPostKanbanRecord.prototype, 'social_instagram.StreamPostKanbanRecord', {

    _onInstagramCommentsClick() {
        const postId = this.record.id.raw_value;
        this.rpc('/social_instagram/get_comments', {
            stream_post_id: postId,
            comments_count: this.commentsCount,
        }).then((result) => {
            this.dialog.add(StreamPostCommentsInstagram, {
                title: this.env._t('Instagram Comments'),
                commentCount: this.commentCount,
                originalPost: this.record,
                accountId: this.record.account_id.raw_value,
                postId: postId,
                comments: result.comments,
                nextRecordsToken: result.nextRecordsToken,
            });
        });
    },

});
