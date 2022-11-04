/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { ListController } from "@web/views/list/list_controller";

export class PayslipListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }
    async onPrintClick() {
        const selectedIds = await this.getSelectedResIds();
        if (selectedIds.length == 0) {
            return;
        }
        const results = await this.orm.call('hr.payslip', 'action_print_payslip', [selectedIds]);
        this.actionService.doAction(results);
    }
}

registry.category('views').add('hr_payroll_payslip_tree', {
    ...listView,
    Controller: PayslipListController,
    buttonTemplate: 'PayslipListView.print_button',
})
