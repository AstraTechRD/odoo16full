/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PayslipRunController } from '@hr_payroll_holidays/js/hr_payslip_run_list';


patch(PayslipRunController.prototype, 'l10n_be_hr_payroll.payslip_run_warrant_payslips_patch', {
    generateWarrantPayslips () {
        this.actionService.doAction("l10n_be_hr_payroll.action_hr_payroll_generate_warrant_payslips");
    }
})
