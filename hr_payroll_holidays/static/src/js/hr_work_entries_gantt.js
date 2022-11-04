odoo.define('hr_payroll_holidays.work_entries_gantt', function (require) {
    'use strict';

    var WorkEntryPayrollHolidaysControllerMixin = require('hr_payroll_holidays.WorkEntryPayrollHolidaysControllerMixin');
    var WorkEntryGanttController = require("hr_work_entry_contract_enterprise.work_entries_gantt");

    var WorkEntryPayrollHolidaysGanttController = WorkEntryGanttController.include(WorkEntryPayrollHolidaysControllerMixin);

    return WorkEntryPayrollHolidaysGanttController;

});

