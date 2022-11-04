/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useService } from "@web/core/utils/hooks";

const { useEffect } = owl;

export class AppointmentInviteFormRenderer extends FormRenderer {
    /**
     * We want to disable the "Save & Copy" button if there is a warning that could
     * result to have an incorrect/empty link.
     */
    setup() {
        super.setup();
        this.notification = useService("notification");
        useEffect((saveButton, warning) => {
            if (saveButton) {
                saveButton.classList.toggle('disabled', !!warning);
            }
        }, () => [document.querySelector('.o_appointment_invite_copy_save'), document.querySelector('.alert.alert-warning')]);
    }
    /**
     * Save the invitation and copy the url in the clipboard
     * @param ev
     */
     async onSaveAndCopy (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        if (await this.props.record.save()) {
            const bookUrl = this.props.record.data.book_url;
            browser.navigator.clipboard.writeText(bookUrl);
            this.notification.add(
                this.env._t("Link copied to clipboard!"),
                {type: "success"}
            );
            this.env.dialogData.close();
        }
    }
}
