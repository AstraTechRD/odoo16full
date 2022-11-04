/** @odoo-module **/

import { registry } from '@web/core/registry';
import { formView } from '@web/views/form/form_view';
import { FormController } from "@web/views/form/form_controller";
import { useTimeOffToDefer } from '@hr_payroll_holidays/views/hooks';

export class PayslipFormController extends FormController {
    setup() {
        super.setup();
        useTimeOffToDefer('.o_form_sheet_bg', "first-child");
    }
}


registry.category('views').add('hr_payslip_form', {
    ...formView,
    Controller: PayslipFormController
});
