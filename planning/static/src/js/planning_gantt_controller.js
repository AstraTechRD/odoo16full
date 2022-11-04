/** @odoo-module alias=planning.PlanningGanttController **/

import GanttController from 'web_gantt.GanttController';
import {_t} from 'web.core';
import { PlanningControllerMixin } from './planning_mixins';

const PlanningGanttController = GanttController.extend(PlanningControllerMixin, {
    events: Object.assign({}, GanttController.prototype.events, {
        'click .o_gantt_button_copy_previous_week': '_onCopyWeekClicked',
        'click .o_gantt_button_send_all': '_onSendAllClicked',
    }),
    buttonTemplateName: 'PlanningGanttView.buttons',

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    _renderButtonQWebParameter: function () {
        return Object.assign({}, this._super(...arguments), {
            activeActions: this.activeActions
        });
    },

    /**
     * @private
     * @returns {Array} Array of objects
     */
    _getRecords() {
        return this.model.get().records;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onAddClicked: function (ev) {
        ev.preventDefault();
        const { startDate, stopDate } = this.model.get();
        const today = moment().startOf('date'); // for the context we want the beginning of the day and not the actual hour.
        if (this.renderer.state.scale !== 'day' && startDate.isSameOrBefore(today, 'day') && stopDate.isSameOrAfter(today, 'day')) {
            // get the today date if the interval dates contain the today date.
            const context = this._getDialogContext(today);
            for (const k in context) {
                context[`default_${k}`] = context[k];
            }
            this._onCreate(context);
            return;
        }
        this._super(...arguments);
    },

    /**
     * @override
     * @private
     * @param {OdooEvent} event
     */
     _getDialogContext(date, rowId) {
         const context = this._super(...arguments);
         const state = this.model.get();
         if (state.scale == "week" || state.scale == "month") {
             const dateStart = date.clone().set({"hour": 8, "minute": 0});
             const dateStop = date.clone().set({"hour": 17, "minute": 0, "second": 0});
             context[state.dateStartField] = this.model.convertToServerTime(dateStart);
             context[state.dateStopField] = this.model.convertToServerTime(dateStop);
         }
        return context;
    },

    /**
     * Opens dialog to add/edit/view a record. Overrides to tweak dialog's title
     *
     * @override
     */
    _openDialog: function (props, options) {
        var record = props.resId ? _.findWhere(this.model.get().records, {id: props.resId}) : {};
        var title = props.resId ? record.display_name : _t("Add Shift");
        this._super({ ...props, title }, options);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     * @param {MouseEvent} ev
     */
    _onScaleClicked: function (ev) {
        this._super.apply(this, arguments);
        var $button = $(ev.currentTarget);
        var scale = $button.data('value');
        if (scale !== 'week') {
            this.$('.o_gantt_button_copy_previous_week').hide();
        } else {
            this.$('.o_gantt_button_copy_previous_week').show();
        }
    },
});

export default PlanningGanttController;
