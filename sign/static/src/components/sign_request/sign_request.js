/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from "@web/legacy/legacy_component";

class SignRequest extends LegacyComponent {

    /**
     * @override
     */
     setup() {
        super.setup();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {SignRequestView}
     */
    get signRequestView() {
        return this.props.record;
    }

}

Object.assign(SignRequest, {
    props: { record: Object },
    template: 'sign.SignRequest',
});

registerMessagingComponent(SignRequest);

export default SignRequest;
