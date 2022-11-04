/** @odoo-module **/

import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from 'web.utils';

const { onWillStart } = owl;

patch(NewContentModal.prototype, 'website_appointment_new_content', {
    setup() {
        this._super();

        onWillStart(async () => {
            this.isAppointmentManager = await this.user.hasGroup('appointment.group_appointment_manager');

            const newAppointmentTypeElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_appointment');
            newAppointmentTypeElement.createNewContent = () => this.onAddContent('website_appointment.appointment_type_action_add_simplified');
            newAppointmentTypeElement.status = MODULE_STATUS.INSTALLED;
            newAppointmentTypeElement.isDisplayed = this.isAppointmentManager;
        });
    },
});
