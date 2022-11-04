/** @odoo-module **/

import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from 'web.utils';
const { xml } = owl;

patch(NewContentModal.prototype, 'website_enterprise_user_navbar', {
    setup() {
        this._super();

        this.state.newContentElements.push({
            moduleXmlId: 'base.module_website_appointment',
            status: MODULE_STATUS.NOT_INSTALLED,
            icon: xml`<i class="fa fa-calendar"/>`,
            title: this.env._t('Appointment Form'),
        });
    },
});
