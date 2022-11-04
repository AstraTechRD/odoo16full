/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class KnowledgeEmojiPickerRemoveActionView extends Component {
    /**
     * @returns {KnowledgeEmojiPickerRemoveActionView}
     */
    get knowledgeEmojiPickerRemoveActionView() {
        return this.props.record;
    }
}

Object.assign(KnowledgeEmojiPickerRemoveActionView, {
    props: { record: Object },
    template: 'mail.KnowledgeEmojiPickerRemoveActionView',
});

registerMessagingComponent(KnowledgeEmojiPickerRemoveActionView);
