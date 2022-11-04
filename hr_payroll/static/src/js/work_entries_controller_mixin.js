odoo.define('hr_payroll.WorkEntryPayrollControllerMixin', function (require) {
    'use strict';

    var core = require('web.core');
    var time = require('web.time');

    var _t = core._t;
    var QWeb = core.qweb;

    var WorkEntryPayrollControllerMixin = {
        /**
         * @override
         */
        updateButtons: function() {
            this._super.apply(this, arguments);

            if(!this.$buttons) {
                return;
            }

            var records = this._fetchRecords();
            var hasConflicts = records.some(function (record) { return record.state === 'conflict'; });
            var allValidated = records.every(function (record) { return record.state === 'validated'; });
            var generateButton = this.$buttons.find('.btn-payslip-generate');

            if (!allValidated && records.length !== 0) {
                generateButton.show();
                generateButton.replaceWith(this._renderGeneratePayslipButton(hasConflicts));
            } else {
                generateButton.hide();
            }
        },

        /*
            Private
        */
       _renderGeneratePayslipButton: function(disabled) {
            return $(QWeb.render('hr_work_entry.work_entry_button', {
                button_text: _t("Generate Payslips"),
                event_class: 'btn-payslip-generate',
                primary: true,
                disabled: disabled,
            })).on('click', this._onGeneratePayslips.bind(this));
       },

        _renderWorkEntryButtons: function() {
            let buttons = this._super.apply(this, arguments);
            return buttons.prepend(this._renderGeneratePayslipButton());
        },

        _getActiveEmployeeIds: function () {
            const records = this._fetchRecords();
            const employees_datas = _.pluck(records, "employee_id");
            const employee_ids = _.map(employees_datas, employee_datas => employee_datas[0]);
            return _.uniq(employee_ids);
        },

        _generatePayslips: function () {
            this.trigger_up('do_action', {
                action: 'hr_payroll.action_generate_payslips_from_work_entries',
                options: {
                    additional_context: {
                        default_date_start: time.date_to_str(this.firstDay),
                        default_date_end: time.date_to_str(this.lastDay),
                        active_employee_ids: this._getActiveEmployeeIds(),
                    },
                },
            });
        },

        _onGeneratePayslips: function (e) {
            this._generatePayslips();
        },
    };

    return WorkEntryPayrollControllerMixin;

});
