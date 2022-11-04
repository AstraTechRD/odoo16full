/** @odoo-module **/

import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

/**
 * The purpose of this Dialog Component is to parse the close function and the kanbanAction function
 * to the form view inside
 */
export class BankRecWidgetRejectDialog extends FormViewDialog {}
BankRecWidgetRejectDialog.props = {
    ...FormViewDialog.props,
    kanbanActionFn: { type: Function, optional: true },
}
BankRecWidgetRejectDialog.template = "account_accountant.BankRecWidgetRejectDialog";
