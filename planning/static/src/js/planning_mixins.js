/** @odoo-module */

import { _t } from 'web.core';
import { Markup } from 'web.utils';

export const PlanningControllerMixin = {
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handler for "Copy Previous" button
     * @private
     * @param {MouseEvent} ev
     */
    async _onCopyWeekClicked(ev) {
        ev.preventDefault();
        const startDate = this.model.getStartDate();
        const result = await this._rpc({
            model: this.modelName,
            method: 'action_copy_previous_week',
            args: [
                startDate,
                this.model._getDomain(),
            ],
            context: this.context || {},
        });
        if (result) {
            const message = _t("The shifts from the previous week have successfully been copied.");
            this.displayNotification({
                type: 'success',
                message: Markup`<i class="fa fa-fw fa-check"></i><span class="ms-1">${message}</span>`,
            });
        } else {
            this.displayNotification({
                type: 'danger',
                message: _t('There are no shifts planned for the previous week, or they have already been copied.'),
            });
        }
        this.reload();
    },

    /**
     * Returns the records.
     * This function is intended to be overridden in the class using this mixin as the
     * model implementation can differ from a View to another.
     *
     * @private
     * @returns {Array}
     */
    _getRecords() {
        return []
    },

    /**
     * Handler for "Publish" button
     * @private
     * @param {MouseEvent} ev
     */
    _onSendAllClicked(ev) {
        ev.preventDefault();
        const records = this._getRecords();

        if (!records || records.length === 0) {
            this.displayNotification({
                type: 'danger',
                message: _t("The shifts have already been published, or there are no shifts to publish.")
            });
            return;
        }

        const additionalContext = this.model.getAdditionalContext(this.context);

        return this.do_action('planning.planning_send_action', {
            additional_context: additionalContext,
            on_close: this.reload.bind(this)
        });
    },
};
