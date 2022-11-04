/** @odoo-module */

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

import { CheckBox } from "@web/core/checkbox/checkbox";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { BooleanToggleField } from '@web/views/fields/boolean_toggle/boolean_toggle_field';

import { session } from '@web/session';

export class ConfirmCheckBox extends CheckBox {
    onClick(ev) {
        ev.preventDefault();

        if (ev.target.tagName !== "INPUT") {
            return;
        }
        this.props.onChange(ev.target.checked);
    }
}

export class BooleanToggleConfirm extends BooleanToggleField {
    setup() {
        super.setup();
        this.dialogService = useService('dialog');
    }

    onChange(value) {
        const record = this.props.record.data;

        const isEmployee = record.employee_user_id && record.employee_user_id[0] === session.uid;
        const isManager = record.is_appraisal_manager || record.is_implicit_manager;
        if (isManager && value && !isEmployee) {
            this.dialogService.add(ConfirmationDialog, {
                body: this.env._t("The employee's feedback will be published without their consent. Do you really want to publish it? This action will be logged in the chatter."),
                confirm: () => this.props.update(value),
                cancel: () => {},
            });
        }
        else {
            this.props.update(value);
        }
    }
}
BooleanToggleConfirm.template = 'hr_appraisal.BooleanToggleConfirm';
BooleanToggleConfirm.components = { ConfirmCheckBox };

registry.category('fields').add('boolean_toggle_confirm', BooleanToggleConfirm);
