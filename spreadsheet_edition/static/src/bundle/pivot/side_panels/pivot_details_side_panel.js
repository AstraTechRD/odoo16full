/** @odoo-module */

import { Domain } from "@web/core/domain";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "web.core";
import { time_to_str } from "web.time";
import EditableName from "../../o_spreadsheet/editable_name/editable_name";

const { Component, onWillStart, onWillUpdateProps } = owl;

export default class PivotDetailsSidePanel extends Component {
    setup() {
        this.dialog = useService("dialog");
        /** @type {import("@spreadsheet/pivot/pivot_data_source").default} */
        this.dataSource = undefined;
        const loadData = async () => {
            this.dataSource = await this.env.model.getters.getAsyncPivotDataSource(
                this.props.pivotId
            );
            this.modelDisplayName = await this.dataSource.getModelLabel();
        };
        onWillStart(loadData);
        onWillUpdateProps(loadData);
    }

    get pivotDefinition() {
        const definition = this.env.model.getters.getPivotDefinition(this.props.pivotId);
        return {
            model: definition.model,
            modelDisplayName: this.modelDisplayName,
            domain: new Domain(definition.domain).toString(),
            dimensions: [...definition.rowGroupBys, ...definition.colGroupBys].map((fieldName) =>
                this.dataSource.getFormattedGroupBy(fieldName)
            ),
            measures: definition.measures.map((measure) =>
                this.dataSource.getGroupByDisplayLabel("measure", measure)
            ),
            sortedColumn: definition.sortedColumn,
        };
    }

    onNameChanged(name) {
        this.env.model.dispatch("RENAME_ODOO_PIVOT", {
            pivotId: this.props.pivotId,
            name,
        });
    }

    formatSort() {
        const sortedColumn = this.pivotDefinition.sortedColumn;
        const order = sortedColumn.order === "asc" ? _t("ascending") : _t("descending");
        const measureDisplayName = this.dataSource.getGroupByDisplayLabel(
            "measure",
            sortedColumn.measure
        );
        return `${measureDisplayName} (${order})`;
    }

    /**
     * Get the last update date, formatted
     *
     * @returns {string} date formatted
     */
    getLastUpdate() {
        const lastUpdate = this.dataSource.lastUpdate;
        if (lastUpdate) {
            return time_to_str(new Date(lastUpdate));
        }
        return _t("never");
    }

    /**
     * Refresh the cache of the current pivot
     *
     */
    refresh() {
        this.env.model.dispatch("REFRESH_PIVOT", { id: this.props.pivotId });
    }

    openDomainEdition() {
        const definition = this.env.model.getters.getPivotDefinition(this.props.pivotId);
        this.dialog.add(DomainSelectorDialog, {
            resModel: definition.model,
            initialValue: new Domain(definition.domain).toString(),
            readonly: false,
            isDebugMode: !!this.env.debug,
            onSelected: (domain) =>
                this.env.model.dispatch("UPDATE_ODOO_PIVOT_DOMAIN", {
                    pivotId: this.props.pivotId,
                    domain: new Domain(domain).toList(),
                }),
        });
    }
}
PivotDetailsSidePanel.template = "spreadsheet_edition.PivotDetailsSidePanel";
PivotDetailsSidePanel.components = { DomainSelector, EditableName };
PivotDetailsSidePanel.props = {
    pivotId: {
        type: String,
        optional: true,
    },
};
