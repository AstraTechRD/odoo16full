/** @odoo-module **/

import PlanningGanttController from '@planning/js/planning_gantt_controller';
import { SalePlanningControllerMixin } from './sale_planning_mixin';
import { _t } from 'web.core';
import { Domain } from '@web/core/domain';

PlanningGanttController.include(SalePlanningControllerMixin);

PlanningGanttController.include({
    events: Object.assign({}, PlanningGanttController.prototype.events, {
        'click .o_gantt_button_plan_so': '_onPlanSOClicked',
    }),
    buttonTemplateName: 'SalePlanningGanttView.buttons',

    //--------------------------------------------------------------------------
    // Utils
    //--------------------------------------------------------------------------
    /**
     * Add and returns gantt view context keys to context in order to give info
     * about what is actually rendered client-side to server.
     *
     * @param {Object} context
     */
    _addGanttContextValues: function (context) {
        const state = this.model.get();
        return Object.assign(context, {
            scale: state.scale,
            focus_date: this.model.convertToServerTime(state.focusDate),
            start_date: this.model.convertToServerTime(state.startDate),
            stop_date: this.model.convertToServerTime(state.stopDate),
        });
    },
    /**
     * @param {Object} context
     * @returns {Object} object
     */
    addViewContextValues(context) {
        return this._addGanttContextValues(context);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * @override
     * @param {Object} state
     * @returns {Array[]}
     */
    _getPlanDialogDomain(state) {
        const domain = this._super(state);
        return Domain.and([
            domain,
            [['sale_line_id', '!=', false]],
        ]).toList({});
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * @private
     * @override
     * @param {Object} context
     */
    _openPlanDialog: function (context) {
        this.openPlanDialogCallback = (result) => {
            if (!result) {
                let notificationOptions = {
                    type: 'danger',
                    message: _t('This resource is not available for this shift during the selected period.'),
                };
                this.displayNotification(notificationOptions);
            }
        };
        Object.assign(context, {
            search_default_group_by_resource: false,
            search_default_group_by_role: false,
            planning_slots_to_schedule: true,
            search_default_sale_order_id: this.model.context.planning_gantt_active_sale_order_id || null,
        });
        this._addGanttContextValues(this.model.context);
        this._super.apply(this, arguments);
    },
});
