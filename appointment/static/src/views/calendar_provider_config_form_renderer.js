/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { CalendarProviderConfigFormRenderer } from "@calendar/views/calendar_provider_config_form_renderer";


patch(CalendarProviderConfigFormRenderer.prototype, 'calendar_provider_config_appointment_onboarding', {
    /**
     * Sets onboarding step state as completed.
     *
     * @override
     */
    async _beforeLeaveContext () {
        return this.orm.call(
            'onboarding.onboarding.step',
            'action_save_appointment_onboarding_configure_calendar_provider_step',
        );
    }
});
