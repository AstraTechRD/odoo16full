/** @odoo-module **/

import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { ListController } from "@web/views/list/list_controller";
import { useTimeOffToDefer } from '@hr_payroll_holidays/views/hooks';

export class PayslipRunController extends ListController {
    setup() {
        super.setup();
        useTimeOffToDefer('.o_list_renderer', "first-child");
    }
}

registry.category('views').add('hr_payslip_run_tree', {
    ...listView,
    Controller: PayslipRunController,
    buttonTemplate: 'hr_payroll_holidays.ListViewButtonTemplate'
});
