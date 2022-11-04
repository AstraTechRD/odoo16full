/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { useSignViewButtons } from "@sign/views/hooks";

export class SignListController extends ListController {
    setup() {
        super.setup(...arguments);
        const functions = useSignViewButtons();
        Object.assign(this, functions);
    }
}
