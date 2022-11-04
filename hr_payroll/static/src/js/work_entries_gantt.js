odoo.define('hr_payroll.work_entries_gantt', function (require) {
    'use strict';

    var WorkEntryPayrollControllerMixin = require('hr_payroll.WorkEntryPayrollControllerMixin');
    var WorkEntryGanttController = require("hr_work_entry_contract_enterprise.work_entries_gantt");

    var WorkEntryPayrollGanttController = WorkEntryGanttController.include(WorkEntryPayrollControllerMixin);

    return WorkEntryPayrollGanttController;

});

