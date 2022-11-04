/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";

export class CallQueueSwitchView extends owl.Component {

    get callQueueSwitchView() {
        return this.props.record;
    }

}

Object.assign(CallQueueSwitchView, {
    props: { record: Object },
    template: "voip.CallQueueSwitchView",
});

registerMessagingComponent(CallQueueSwitchView);
