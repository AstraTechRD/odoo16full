/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class Approval extends Component {

    /**
     * @returns {ApprovalView}
     */
    get approvalView() {
        return this.props.record;
    }

}

Object.assign(Approval, {
    props: { record: Object },
    template: 'approvals.Approval',
});

registerMessagingComponent(Approval);
