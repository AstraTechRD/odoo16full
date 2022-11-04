/** @odoo-module **/

import { GroupMenu } from "./group_menu";
import { download } from "@web/core/network/download";
import { useService } from "@web/core/utils/hooks";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";


export class MrpMpsControlPanel extends ControlPanel {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.dialogService = useService("dialog");
    }

    get model() {
        return this.env.model;
    }

    get groups() {
        return this.env.model.data.groups[0];
    }

    get isRecordSelected() {
        return this.model.selectedRecords.size > 0;
    }

    getActionMenuItems() {
        return Object.assign({}, {
            other: [{
                key: "export",
                description: this.env._t("Export"),
                callback: () => this.onExportData(),
            }, {
                key: "delete",
                description: this.env._t("Delete"),
                callback: () => this.unlinkSelectedRecord(),
            }, {
                key: "replenish",
                description: this.env._t("Replenish"),
                callback: () => this.replenishSelectedRecords(),
            }]
        });
    }

    /**
     * Handles the click on replenish button. It will call action_replenish with
     * all the Ids present in the view.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickReplenish(ev) {
        this.env.model.replenishAll();
    }

    _onMouseOverReplenish(ev) {
        this.model.mouseOverReplenish()
    }

    _onMouseOutReplenish(ev) {
        this.model.mouseOutReplenish()
    }

    _onClickCreate(ev) {
        this.env.model._createProduct();
    }

    replenishSelectedRecords() {
        this.env.model.replenishSelectedRecords();
    }

    unlinkSelectedRecord() {
        this.env.model.unlinkSelectedRecord();
    }

    async getExportedFields(model, import_compat, parentParams) {
        return await this.rpc("/web/export/get_fields", {
            ...parentParams,
            model,
            import_compat,
        });
    }

    async downloadExport(fields, import_compat, format) {
        const resIds = Array.from(this.model.selectedRecords);
        const exportedFields = fields.map((field) => ({
            name: field.name || field.id,
            label: field.label || field.string,
            store: field.store,
            type: field.field_type,
        }));
        if (import_compat) {
            exportedFields.unshift({ name: "id", label: this.env._t("External ID") });
        }
        await download({
            data: {
                data: JSON.stringify({
                    import_compat,
                    context: this.props.context,
                    domain: this.model.domain,
                    fields: exportedFields,
                    ids: resIds.length > 0 && resIds,
                    model: "mrp.production.schedule",
                }),
            },
            url: `/web/export/${format}`,
        });
    }

    /**
     * Opens the Export Dialog
     *
     * @private
     */
    onExportData() {
        const resIds = Array.from(this.model.selectedRecords);
        const dialogProps = {
            resIds,
            context: this.props.context,
            download: this.downloadExport.bind(this),
            getExportedFields: this.getExportedFields.bind(this),
            root: {
                resModel: "mrp.production.schedule",
                activeFields: [],
            },
        };
        this.dialogService.add(ExportDataDialog, dialogProps);
    }
}

MrpMpsControlPanel.template = "mrp_mps.MrpMpsControlPanel";
MrpMpsControlPanel.components = {
    ...ControlPanel.components,
    ActionMenus,
    GroupMenu,
};
