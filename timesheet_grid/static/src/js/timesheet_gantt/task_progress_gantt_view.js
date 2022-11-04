/** @odoo-module **/

import TaskGanttRow from '@project_enterprise/js/task_gantt_row';
import fieldUtils from 'web.field_utils';
import { registry } from '@web/core/registry';


/*
    Although this might look quite crappy at first sight, this is unfortunately necessary as there is a real
    dependency of the include() on the timesheet_uom service. Indeed fieldUtils.format.timesheet_uom(),
    which depends on the session, is only defined once the timesheet_uom service has started.
*/

const timesheetUomGanttPopoverService = {
    dependencies: ["timesheet_uom"],
    start() {
        TaskGanttRow.include({
            _getPopoverContext: function () {
                const data = this._super.apply(this, arguments);
                if (data.allow_subtasks) {
                    data.total_hours_spent_formatted = fieldUtils.format.timesheet_uom(data.total_hours_spent);
                } else {
                    data.effective_hours_formatted = fieldUtils.format.timesheet_uom(data.effective_hours);
                }
                data.progressFormatted = Math.round(data.progress);
                return data;
            },
        });
    },
};

registry.category("services").add("timesheet_uom_gantt_popover", timesheetUomGanttPopoverService);
