/** @odoo-module **/

import { SocialPostFormatterMixin } from './social_post_formatter_mixin';
import { StreamPostCommentsReply } from './stream_post_comments_reply';

import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { escape, sprintf } from '@web/core/utils/strings';
import { patch } from '@web/core/utils/patch';
import { useService } from '@web/core/utils/hooks';

const { Component, markup, useState } = owl;

export class StreamPostComment extends Component {

    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.rpc = useService('rpc');
        this.action = useState({
            showSubComment: false,
            showReplyComment: false,
        });
        this.state = useState({
            isEditMode: false,
        });
    }

    //----------
    // Handlers
    //----------

    _onLoadReplies() {
        this.action.showSubComment = true;
    }

    _onReplyComment() {
        this.action.showReplyComment = true;
    }

    _toggleEditMode() {
        this.state.isEditMode = !this.state.isEditMode;
    }

    _deleteComment() {
        this.dialog.add(ConfirmationDialog, {
            title: this.env._t('Delete Comment'),
            body: sprintf(this.env._t('Do you really want to delete %s'), this.commentName),
            confirm: () => {
                this._confirmDeleteComment();
            },
            cancel: () => {},
        });
    }

    //---------
    // Private
    //---------

    async _confirmDeleteComment() {
        await this.rpc(this.deleteCommentEndpoint, {
            stream_post_id: this.originalPost.id.raw_value,
            comment_id: this.comment.id,
        });

        this.props.onDeleteComment();
    }

    //-------
    // Utils
    //-------

    _htmlEscape(message) {
        return escape(message);
    }

    formatComment(commentMessage) {
        return markup(this._formatPost(commentMessage));
    }

    //----------
    // Getters
    //----------

    get comment() {
        return this.props.comment;
    }

    get account() {
        return this.props.account;
    }

    get originalPost() {
        return this.props.originalPost;
    }

    get deleteCommentEndpoint() {
        return null;
    }

    get authorPictureSrc() {
        return '';
    }

    get currentAuthorPictureSrc() {
        return '';
    }

    get commentName() {
        return this.env._t('comment/reply');
    }

    get link() {
        return '';
    }

    get isDeletable() {
        return this.isAuthor;
    }

    get isEditable() {
        return this.isAuthor;
    }

    get isManageable() {
        return this.isDeletable || this.isEditable;
    }

    get isAuthor() {
        return false;
    }

    get isLikable() {
        return true;
    }

    get likesClass() {
        return 'fa-thumbs-up';
    }

    get commentComponent() {
        return this.constructor;
    }

    get commentReplyComponent() {
        return StreamPostCommentsReply;
    }

}

patch(StreamPostComment.prototype, 'social_post_formatter_mixin', SocialPostFormatterMixin);

StreamPostComment.template = 'social.StreamPostComment';
