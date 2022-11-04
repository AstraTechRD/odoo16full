/** @odoo-module **/

import { Field } from "@web/views/fields/field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { _t } from "web.core";

export class DocumentsInspectorField extends Field {
    get fieldComponentProps() {
        const doLockAction = this.props.lockAction;
        const record = this.props.record;
        const props = super.fieldComponentProps;

        // Set "Multiple Values" instead of the actual value in case multiple values are selected for
        //  Many2one Fields.
        if (
            this.FieldComponent === Many2OneField &&
            new Set(
                this.props.selection.map((rec) => (rec.data[this.props.name] ? rec.data[this.props.name][0] : false))
            ).size > 1
        ) {
            props.value = [null, _t("Multiple values")];
        }

        props.readonly = this.props.inspectorReadonly || false;
        props.update = async (value) => {
            doLockAction(async () => {
                // Temporarily enable multiEdit -> save on all selected records
                const originalFolderId = record.data.folder_id[0];
                const previousMultiEdit = record.model.multiEdit;
                record.model.multiEdit = true;
                await record.update({ [this.props.name]: value });
                record.model.multiEdit = previousMultiEdit;
                if (this.props.name === "folder_id" && record.data.folder_id[0] !== originalFolderId) {
                    this.props.selection.forEach((rec) => record.model.root.removeRecord(rec));
                }
            });
        };
        delete props.selection;
        delete props.inspectorReadonly;
        delete props.lockAction;
        return props;
    }
}
