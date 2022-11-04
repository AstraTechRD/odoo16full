/** @odoo-module **/

import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { AppointmentInviteFormRenderer } from './appointment_invite_form_renderer.js';

const AppointmentInviteFormView = {
    ...formView,
    Renderer: AppointmentInviteFormRenderer,
};

registry.category("views").add('appointment_invite_view_form', AppointmentInviteFormView);

export {
    AppointmentInviteFormView,
}
