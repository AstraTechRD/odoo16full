/** @odoo-module **/

import { ActionContainer } from "@web/webclient/actions/action_container";
import { useService } from "@web/core/utils/hooks";

export class StudioActionContainer extends ActionContainer {
    setup() {
        super.setup();
        this.actionService = useService("action");
        if (this.props.initialAction) {
            this.actionService.doAction(this.props.initialAction);
        }
    }
}
