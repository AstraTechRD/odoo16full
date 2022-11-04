/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
const { Component } = owl;

class MenuPopup extends Component {

    setup() {
        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.action = useService('action');
    }

    get step() {
        return this.props.popupData.selectedStepId;
    }

    get title() {
        return this.props.popupData.title;
    }

    block() {
        const options = {
            additionalContext: { default_workcenter_id: this.props.popupData.workcenterId },
            onClose: this.props.onClose,
        };
        this.props.onClosePopup('menu');
        this.action.doAction('mrp.act_mrp_block_workcenter_wo', options);
    }

    async callAction(method) {
        const action = await this.orm.call(
            'mrp.workorder',
            method,
            [[this.props.popupData.workorderId]]
        );
        this.props.onClosePopup('menu');
        this.action.doAction(action, { onClose: this.props.onClose });
    }

    cancel() {
        this.props.onClosePopup('menu');
    }

    async proposeChange(changeType, title, message) {
        const action = await this.orm.call(
            'mrp.workorder',
            'action_propose_change',
            [[this.props.popupData.workorderId], changeType, title],
        );
        this.props.onClosePopup('menu');
        this.action.doAction(action, { onClose: () => {
            this.props.onClose(message);
        }});
    }
}

MenuPopup.template = 'mrp_workorder.MenuPopup';

export default MenuPopup;
