/** @odoo-module **/

import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class ShareFormViewDialog extends FormViewDialog {
    setup() {
        super.setup();
        if (this.props.onSave) {
            this.viewProps.onSave = this.props.onSave;
        }
        if (this.props.onDiscard) {
            this.viewProps.onDiscard = this.props.onDiscard;
        }
    }
}
ShareFormViewDialog.props = {
    ...FormViewDialog.props,
    onSave: { type: Function, optional: true },
    onDiscard: { type: Function, optional: true },
};
