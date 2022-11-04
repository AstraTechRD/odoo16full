/** @odoo-module  */

import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { ListController } from "@web/views/list/list_controller";
const { onWillStart } = owl;

export class HRContractTreeController extends ListController {
    setup () {
        super.setup();
        onWillStart(async () => {
            this.isUserContractManager = await this.userService.hasGroup("hr_contract.group_hr_contract_manager");
        });
    }

    async indexWage () {
        this.actionService.doAction('hr_payroll.action_hr_payroll_index', {
            additionalContext: {
                active_ids: await this.getSelectedResIds(),
            },
        });
    }
}

registry.category('views').add('hr_contract_tree', {
    ...listView,
    Controller: HRContractTreeController,
    buttonTemplate: 'hr_payroll.ContractTreeIndexButton',
})
