odoo.define('timesheet_grid.TimerGridController', function (require) {
    "use strict";

    const GridController = require('web_grid.GridController');
    const TimesheetGridControllerMixin = require('timesheet_grid.TimesheetGridControllerMixin');

    const TimerGridController = GridController.extend(TimesheetGridControllerMixin, {
        custom_events: Object.assign({}, GridController.prototype.custom_events, {
            update_timer: '_onUpdateTimer',
            update_timer_description: '_onUpdateTimerDescription',
            add_time_timer: '_onAddTimeTimer',
            stop_timer: '_onStopTimer',
            unlink_timer: '_onUnlinkTimer',
        }),

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * @constructor
         */
        init: function () {
            this._super.apply(this, arguments);
            this._onClickTimerButton = _.debounce(this._onClickTimerButton, 500);
        },

        /**
         * If we update an existing line, we update the view.
         *
         * @private
         */
        async _onUpdateTimer() {
            const state = await this.model.actionTimer(this.model.get());
            await this.renderer.update(state);
            this.updateButtons(state);
        },
        _onUpdateTimerDescription(event) {
            const timesheetId = event.data.timesheetId;
            const description = event.data.description;
            this.model._changeTimerDescription(timesheetId, description);
        },
        async _onAddTimeTimer(event) {
            const timesheetId = event.data.timesheetId;
            const time = event.data.time;
            await this.model._addTimeTimer(timesheetId, time);
            await this.reload();
        },
        async _onStopTimer(event) {
            const timesheetId = event.data.timesheetId;
            await this.model._stopTimer(timesheetId);
            await this.reload();
        },
        _onUnlinkTimer(event) {
            const timesheetId = event.data.timesheetId;
            this.model._unlinkTimer(timesheetId);
        }
    });

    return TimerGridController;
});
