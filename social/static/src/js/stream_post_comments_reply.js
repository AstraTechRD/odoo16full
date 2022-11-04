/** @odoo-module **/

import { FileUploader } from '@web/views/fields/file_handler';
import { useAutofocus, useService } from '@web/core/utils/hooks';

const { Component, onMounted, onWillUnmount, useState } = owl;

export class StreamPostCommentsReply extends Component {

    setup() {
        super.setup();
        this.messagingService = useService('messaging');
        this.state = useState({
            disabled: false,
            attachmentSrc: false,
        });
        this.inputRef = useAutofocus();

        this.messagingService.get().then(messaging => this.messaging = messaging);
        this._onAddEmoji = this._onAddEmoji.bind(this);
        onMounted(() => {
            this.messaging.messagingBus.addEventListener(`social_add_emoji_to_${this.inputRef.el.dataset.id}`, this._onAddEmoji);
        });
        onWillUnmount(() => {
            this.messaging.messagingBus.removeEventListener(`social_add_emoji_to_${this.inputRef.el.dataset.id}`, this._onAddEmoji);
        });
    }

    /**
     * Method called when the user presses 'Enter' after writing a comment in the textarea.
     *
     * @param {KeyboardEvent} event
     * @private
     */
    _onAddComment(event) {
        if (event.key !== 'Enter' || event.ctrlKey || event.shiftKey) {
            return;
        }
        event.preventDefault();
        let textarea = event.currentTarget;

        if (textarea.value.trim() === '') {
            return;
        }

        this.state.disabled = true;

        this._addComment(textarea);
    }

    _showEmojiPicker(event) {
        this.messaging.social.update({
            textareaId: this.inputRef.el.dataset.id,
            emojiPickerPopoverAnchorRef: { el: event.target.closest('.o_social_emoji_dropdown') },
            emojiPickerPopoverView: {},
        });
    }

    //---------
    // Private
    //---------

    _addComment(textarea) {
        if (this.props.preventAddComment(textarea, this.isCommentReply ? this.comment.id : undefined)) {
            return;
        }

        let formData = new FormData(textarea.closest('.o_social_write_reply').querySelector('form'));

        const xhr = new window.XMLHttpRequest();
        xhr.open('POST', this.addCommentEndpoint);
        formData.append('csrf_token', odoo.csrf_token);
        formData.append('stream_post_id', this.originalPost.id.raw_value);
        if (this.isCommentEdit) {
            formData.append('is_edit', this.isCommentEdit);
        }
        if (this.isCommentEdit || this.isCommentReply) {
            formData.append('comment_id', this.comment.id);
        }
        let existingAttachmentId = textarea.dataset.existingAttachmentId;
        if (existingAttachmentId) {
            formData.append('existing_attachment_id', this.props.attachmentSrc);
        }

        xhr.send(formData);
        xhr.onload = () => {
            const comment = JSON.parse(xhr.response);
            if (!comment.error) {
                this.props.onAddComment(comment);
            }
            this.state.attachmentSrc = false;
            this.inputRef.el.value = '';
            this.state.disabled = false;
            if (this.isCommentEdit) {
                this.props.toggleEditMode();
            }
        }
    }

    /**
     * This method adds the emoji just after the user selection. After it's inserted it
     * gives back the focus to the textarea just after the added emoji.
     *
     * @param { CustomEvent } event
     * @private
     */
    _onAddEmoji(event) {
        const input = this.inputRef.el;
        const selectionStart = input.selectionStart;
        const emoji = event.detail.emoji.codepoints;

        input.value = input.value.slice(0, selectionStart) + emoji + input.value.slice(selectionStart);
        input.focus();
        input.setSelectionRange(selectionStart + emoji.length, selectionStart + emoji.length);
    }

    //------------------------
    // Image Upload Processing
    //------------------------

    /**
     * Triggers image selection (file system browse).
     *
     * @param {MouseEvent} event
     */
    _onAddImage(event) {
        event.currentTarget.closest('.o_social_write_reply').querySelector('.o_input_file').click();
    }

    /**
     * When the user selects a file to attach to the comment,
     * a preview of the image is shown below the comment.
     *
     * This is very similar to what Facebook does when commenting a post.
     *
     * @param {Object} file
     * @param {String} file.data
     * @param {String} file.type
     */
    _onImageChange({data, type}) {
        this.state.attachmentSrc = 'data:' + type + ';base64,' + data;
    }

    /**
     * Removes the image preview when the user decides to remove it.
     */
    _onImageRemove() {
        this.state.attachmentSrc = false;
    }

    //--------
    // Getters
    //--------

    get comment() {
        return this.props.comment;
    }

    get account() {
        return this.props.account;
    }

    get originalPost() {
        return this.props.originalPost;
    }

    get authorPictureSrc() {
        return '';
    }

    get addCommentEndpoint() {
        return null;
    }

    get isCommentReply() {
        return this.props.isCommentReply;
    }

    get isCommentEdit() {
        return this.props.isCommentEdit;
    }

    get initialValue() {
        return this.props.initialValue;
    }

    get canAddImage() {
        return true;
    }

}
StreamPostCommentsReply.template = 'social.StreamPostCommentsReply';
StreamPostCommentsReply.components = { FileUploader };
StreamPostCommentsReply.defaultProps = {
    isCommentReply: false,
    isCommentEdit: false,
};
