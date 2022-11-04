/** @odoo-module **/

import { StreamPostComment } from '@social/js/stream_post_comment';

import { patch } from '@web/core/utils/patch';
import { useService } from "@web/core/utils/hooks";

patch(StreamPostComment.prototype, 'stream_post_comment_crm', {
    setup() {
        this._super(...arguments);

        this.actionService = useService("action");
    },

    get isManageable() {
        return super.isManageable || this.isConvertibleToLead();
    },

    isConvertibleToLead() {
        return !this.isAuthor;
    },

    /**
     * Method called when generating a social.lead from a post comment.
     * It retrieves necessary data for the lead creation and open the social.post.to.lead wizard.
     */
    generateLeadFromComment() {
        this.actionService.doAction("social_crm.social_post_to_lead_action", {
            additionalContext: {
                default_conversion_source: 'comment',
                default_social_stream_post_id: this.originalPost.id.raw_value,
                default_social_account_id: this.originalPost.account_id.raw_value,
                default_author_name: this.comment.from.name,
                default_post_content: this._formatPost(this.comment.message),
                // expected datetime format by the server
                // as social comments are not stored as records, we need to do some manual formatting
                default_post_datetime: moment(this.comment.created_time).format('YYYY-MM-DD HH:mm:ss'),
                default_post_link: this.originalPost.post_link.raw_value
            }
        });

        this.env.closeCommentsModal();
    }
});
