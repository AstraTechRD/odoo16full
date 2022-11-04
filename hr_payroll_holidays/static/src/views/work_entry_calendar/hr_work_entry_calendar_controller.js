/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { useTimeOffToDefer } from '@hr_payroll_holidays/views/hooks';
import { WorkEntryCalendarController } from '@hr_work_entry_contract/views/work_entry_calendar/work_entry_calendar_controller';

patch(WorkEntryCalendarController.prototype, 'hr_payroll_holidays.work_entries_calendar', {
    setup() {
        this._super(...arguments);
        useTimeOffToDefer('.o_content', 'first-child');
    }
});
