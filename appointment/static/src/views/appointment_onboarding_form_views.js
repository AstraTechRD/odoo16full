/** @odoo-module **/

import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";

import AppointmentOnboardingAppointmentTypeFormController from "./appointment_onboarding_form_controller.js";

import {
    AppointmentOnboardingLinkFormRenderer,
} from "./appointment_onboarding_link_form_renderer.js";


const AppointmentOnboardingAppointmentTypeFormView = {
    ...formView,
    Controller: AppointmentOnboardingAppointmentTypeFormController,
};

const AppointmentOnboardingLinkFormView = {
    ...formView,
    Renderer: AppointmentOnboardingLinkFormRenderer,
};

registry.category("views").add("appointment_onboarding_link_form", AppointmentOnboardingLinkFormView);
registry.category("views").add('appointment_onboarding_create_appointment_type_form', AppointmentOnboardingAppointmentTypeFormView);
