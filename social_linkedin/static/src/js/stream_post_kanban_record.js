/** @odoo-module **/

import { StreamPostKanbanRecord } from '@social/js/stream_post_kanban_record';
import { StreamPostCommentsLinkedin } from './stream_post_comments';

import { patch } from '@web/core/utils/patch';

patch(StreamPostKanbanRecord.prototype, 'social_linkedin.StreamPostKanbanRecord', {

    _onLinkedInCommentsClick() {
        const postId = this.record.id.raw_value;
        this.rpc('/social_linkedin/get_comments', {
            stream_post_id: postId,
            comments_count: this.commentsCount
        }).then((result) => {
            this.dialog.add(StreamPostCommentsLinkedin, {
                title: this.env._t('LinkedIn Comments'),
                commentsCount: this.commentsCount,
                accountId: this.record.account_id.raw_value,
                originalPost: this.record,
                postId: postId,
                comments: result.comments,
                summary: result.summary,
                postAuthorImage: result.postAuthorImage,
                currentUserUrn: result.currentUserUrn,
                offset: result.offset,
            });
        });
    },

});
