/** @odoo-module */

import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";
import { LegacyComponent } from "@web/legacy/legacy_component";

/**
 * This is the side panel to define/edit a global filter.
 * It can be of 3 different type: text, date and relation.
 */
export default class GlobalFiltersSidePanel extends LegacyComponent {
    setup() {
        this.getters = this.env.model.getters;
    }

    get isReadonly() {
        return this.env.model.getters.isReadonly();
    }

    get filters() {
        return this.env.model.getters.getGlobalFilters();
    }

    hasDataSources() {
        return (
            this.env.model.getters.getPivotIds().length +
            this.env.model.getters.getListIds().length +
            this.env.model.getters.getOdooChartIds().length
        );
    }

    newText() {
        this.env.openSidePanel("FILTERS_SIDE_PANEL", { type: "text" });
    }

    newDate() {
        this.env.openSidePanel("FILTERS_SIDE_PANEL", { type: "date" });
    }

    newRelation() {
        this.env.openSidePanel("FILTERS_SIDE_PANEL", { type: "relation" });
    }

    onEdit(id) {
        this.env.openSidePanel("FILTERS_SIDE_PANEL", { id });
    }

    onDelete() {
        if (this.id) {
            this.env.model.dispatch("REMOVE_GLOBAL_FILTER", { id: this.id });
        }
        this.trigger("close-side-panel");
    }
}
GlobalFiltersSidePanel.template = "spreadsheet_edition.GlobalFiltersSidePanel";
GlobalFiltersSidePanel.components = { FilterValue };
