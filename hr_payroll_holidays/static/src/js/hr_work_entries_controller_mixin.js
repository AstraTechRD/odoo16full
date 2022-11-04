odoo.define('hr_payroll_holidays.WorkEntryPayrollHolidaysControllerMixin', function (require) {
    'use strict';

    var core = require('web.core');
    var QWeb = core.qweb;

    var WorkEntryPayrollHolidaysControllerMixin = {
        /**
         * @override
         */
        init: function () {
            var self = this;
            this._super.apply(this, arguments);
            this._rpc({
                model: 'hr.leave',
                method: 'search',
                args: [[['payslip_state', '=', 'blocked']]],
            }).then(function (result) {
                if(!_.isEmpty(result)) {
                    var $warning = $(QWeb.render("warning.time.off.to.defer", {}));                
                    $warning.find('.o_open_defer_time_off').on('click', function() {
                        self.do_action('hr_payroll_holidays.hr_leave_action_open_to_defer');
                    });
                    self._displayWarning($warning);
                }
            });
        },
    };

    return WorkEntryPayrollHolidaysControllerMixin;

});
