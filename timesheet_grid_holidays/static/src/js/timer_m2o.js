/** @odoo-module **/

import TimerHeaderM2O from 'timesheet_grid.TimerHeaderM2O';

TimerHeaderM2O.include({
    /**
     * @override
     * @return {Object} taskDomain
     */
     _getTaskDomain() {
        const taskDomain = this._super(...arguments);
        taskDomain.push(['is_timeoff_task', '=', false]);
        return taskDomain
     }
});
