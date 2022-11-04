/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";
import { Field } from "@web/views/fields/field";

export class WorkedDaysField extends Field {
    get fieldComponentProps() {
        const props = super.fieldComponentProps;
        const record = this.props.record;
        const oldUpdate = props.update;
        props.update = async (value) => {
            if (this.props.name === 'amount' && record.data.amount !== value) {
                await record.update({ [this.props.name]: value });
                await record.save( { stayInEdition: true, noReload: true });
                // getting the wizard id. when js team gets rid of the basic relational model, we'll clean this
                const wizardId = record.model.__bm_load_params__.res_id;
                if (wizardId) {
                    const action = await this.env.services.orm.call(
                        "hr.payroll.edit.payslip.lines.wizard",
                        "recompute_worked_days_lines",
                        [wizardId]
                    );
                    await this.env.services.action.doAction(action);
                }
            } else {
                await oldUpdate(value);
            }
        }
        return props;
    }
}

export class WorkedDaysRenderer extends ListRenderer {}
WorkedDaysRenderer.components = {
    ...ListRenderer.components,
    Field: WorkedDaysField,
}

export class WorkedDaysLineOne2Many extends X2ManyField {
    async onAdd ({ context, editable }) {
        const wizardId = this.props.record.resId;
        return super.onAdd({
            context: {
                ...context,
                default_edit_payslip_lines_wizard_id: wizardId,
            },
            editable
        });
    }
}
WorkedDaysLineOne2Many.components = {
    ...X2ManyField.components,
    ListRenderer: WorkedDaysRenderer
};

export class PayslipLineField extends Field {
    get fieldComponentProps() {
        const props = super.fieldComponentProps;
        const record = this.props.record;
        const oldUpdate = props.update;
        props.update = async (value) => {
            if (this.props.name === 'amount' || this.props.name === 'quantity') {
                await record.update({ [this.props.name]: value });
                await record.save( { stayInEdition: true, noReload: true });
                const wizardId = record.model.__bm_load_params__.res_id;
                if (wizardId) {
                    const line_id = record.data.id;
                    const action = await this.env.services.orm.call(
                        "hr.payroll.edit.payslip.lines.wizard",
                        "recompute_following_lines",
                        [wizardId, line_id]
                    );
                    await this.env.services.action.doAction(action);
                }
            } else {
                await oldUpdate(value);
            }
        }
        return props;
    }
}
export class PayslipLineRenderer extends ListRenderer {}
PayslipLineRenderer.components = {
    ...ListRenderer.components,
    Field: PayslipLineField
}

export class PayslipLineOne2Many extends X2ManyField {
    async onAdd ({ context, editable }) {
        const wizardId = this.props.record.resId;
        return super.onAdd({
            context: {
                ...context,
                default_edit_payslip_lines_wizard_id: wizardId,
            },
            editable
        });
    }
}

PayslipLineOne2Many.components = {
    ...X2ManyField.components,
    ListRenderer: PayslipLineRenderer
};

registry.category('fields').add('payslip_line_one2many', PayslipLineOne2Many);
registry.category('fields').add('worked_days_line_one2many', WorkedDaysLineOne2Many);
