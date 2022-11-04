odoo.define('hr_contract_salary_payroll', function (require) {
"use strict";

var SalaryPackageWidget = require("hr_contract_salary");
var core = require('web.core');

var qweb = core.qweb;

SalaryPackageWidget.include({
    updateGrossToNetModal(data) {
        var modal_body = $(qweb.render('hr_contract_salary_payroll.salary_package_brut_to_net_modal', {'datas': data.payslip_lines}));
        this.$("main.modal-body").html(modal_body);
        this._super.apply(this, arguments);
    },
});
});
