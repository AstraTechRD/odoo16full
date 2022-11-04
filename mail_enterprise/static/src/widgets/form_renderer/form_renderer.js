/** @odoo-module **/

import config from 'web.config';
import FormRenderer from 'web.FormRenderer';

// ensure `.include()` on `mail` is applied before `mail_enterprise`
import '@mail/widgets/form_renderer/form_renderer';

/**
 * Display attachment preview on side of form view for large screen devices.
 *
 * To use this simply add div with class o_attachment_preview in format
 *     <div class="o_attachment_preview"/>
**/

FormRenderer.include({
    //--------------------------------------------------------------------------
    // Form Overrides
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._onResizeWindow = _.debounce(this._onResizeWindow.bind(this), 200);
    },
    /**
     * @override
     */
    start() {
        window.addEventListener('resize', this._onResizeWindow);
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        window.removeEventListener('resize', this._onResizeWindow);
        this._super();
    },

    //--------------------------------------------------------------------------
    // Mail Methods
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    hasAttachmentViewer() {
        if (!this.messaging || !this.state.res_id) {
            return false;
        }
        const thread = this.messaging.models['Thread'].insert({
            id: this.state.res_id,
            model: this.state.model,
        });
        // simulate legacy form view widget having useModels() to ensure
        // attachment view gets displayed again when attachments change
        owl.Component.env.services.messaging.modelManager.startListening(this.modelsListener);
        const hasAttachments = thread.attachmentsInWebClientView.length > 0;
        owl.Component.env.services.messaging.modelManager.stopListening(this.modelsListener);
        return (
            config.device.size_class >= config.device.SIZES.XXL &&
            this.attachmentViewerTarget && !$(this.attachmentViewerTarget).hasClass('o_invisible_modifier') &&
            hasAttachments
        );
    },
    /**
     * @override
     */
    _isChatterAside() {
        return (
            config.device.size_class >= config.device.SIZES.XXL &&
            !this.hasAttachmentViewer() &&
            !this.isChatterInSheet
        );
    },
    /**
     * Reflects the move of chatter (from aside to underneath of form sheet or
     * the other way around) into classes and component props to allow theming
     * to be adapted
     *
     * @private
     * @param {Event} ev
     */
    _onResizeWindow(ev) {
        if (this._chatterContainerComponent) {
            this._interchangeChatter();
        }
        this._applyFormSizeClass();
    },
});
