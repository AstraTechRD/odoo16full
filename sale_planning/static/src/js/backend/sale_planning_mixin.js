/** @odoo-module */

import { _t } from 'web.core';

export const SalePlanningControllerMixin = {

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handler for "Plan Orders" button
     * @private
     * @param {MouseEvent} ev
     */
    async _onPlanSOClicked(ev) {
        ev.preventDefault();
        const result = await this._rpc({
            model: this.modelName,
            method: 'action_plan_sale_order',
            args: [
                this.model._getDomain(),
            ],
            context: this.addViewContextValues(this.context),
        });
        if (result.length) {
            const scale = this.viewType == 'gantt' ? this.model.ganttData.scale : this.model.data.scale;
            const anchor = (
                this.viewType == 'gantt' ? this.model.ganttData.focusDate : this.model.data.highlight_date
            ).format('YYYY-MM-DD');

            this.displayNotification({
                type: 'success',
                message: _t("The sales orders have successfully been assigned."),
                buttons: [{
                    'text': 'View Shifts',
                    'icon': 'fa-arrow-right',
                    'click': () => this.do_action('sale_planning.planning_action_orders_planned', {
                        view_type: this.viewType,
                        additional_context: {
                            active_ids: result,
                            default_scale: scale,
                            default_mode: scale,
                            initialDate: anchor,
                            initial_date: anchor,
                        },
                    }),
                }],
            });
        } else {
            this.displayNotification({
                type: 'danger',
                message: _t('There are no sales orders to assign or no employees are available.'),
            });
        }
        this.reload();
    },
};
