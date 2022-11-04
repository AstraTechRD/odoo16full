/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";


export default class AppointmentOnboardingAppointmentTypeFormController extends FormController {
    setup() {
        super.setup();
        this.orm = useService('orm');
    }
    /**
     * Overridden to mark the onboarding step as completed and reload the view.
     *
     * @override
     */
    async saveButtonClicked()  {
        await super.saveButtonClicked();
        const wasFirstValidation = await this.orm.call(
            'onboarding.onboarding.step',
            'action_save_appointment_onboarding_create_appointment_type_step',
        );
        this.env.dialogData.close();
        if (wasFirstValidation) {
            window.location.reload();
        }
    }
    /**
     * Close modal on discard.
     *
     * @override
     */
    async discard() {
        await super.discard();
        this.env.dialogData.close();
    }
}
