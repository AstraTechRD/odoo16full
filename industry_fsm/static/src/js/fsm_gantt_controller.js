/** @odoo-module **/

import TaskGanttController from '@project_enterprise/js/task_gantt_controller';

export default TaskGanttController.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onAddClicked(ev) {
        ev.preventDefault();
        const { startDate, stopDate } = this.model.get();
        const today = moment().startOf('day'); // for the context we want the beginning of the day and not the actual hour.
        if (
            this.context.fsm_mode &&
            startDate.isSameOrBefore(today, 'day') &&
            stopDate.isSameOrAfter(today, 'day')
        ) {
            // get the today date if the interval dates contain the today date.
            const context = {};
            const state = this.model.get();
            context[state.dateStartField] = this.model.convertToServerTime(today);
            context[state.dateStopField] = this.model.convertToServerTime(today.clone().endOf('day'));
            for (const k in context) {
                context[`default_${k}`] = context[k];
            }
            this._onCreate(context);
            return;
        }
        this._super(...arguments);
    },
});
