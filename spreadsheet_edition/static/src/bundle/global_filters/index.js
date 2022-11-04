/** @odoo-module */

import { _t, _lt } from "@web/core/l10n/translation";

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

import FilterEditorSidePanel from "./filter_editor_side_panel";
import GlobalFiltersSidePanel from "./global_filters_side_panel";
import { FilterComponent } from "./filter_component";

import "./operational_transform";

const { sidePanelRegistry, topbarComponentRegistry, cellMenuRegistry } = spreadsheet.registries;

sidePanelRegistry.add("FILTERS_SIDE_PANEL", {
    title: _t("Filter properties"),
    Body: FilterEditorSidePanel,
});

sidePanelRegistry.add("GLOBAL_FILTERS_SIDE_PANEL", {
    title: _t("Filters"),
    Body: GlobalFiltersSidePanel,
});

topbarComponentRegistry.add("filter_component", {
    component: FilterComponent,
    isVisible: (env) => {
        return !env.model.getters.isReadonly() || env.model.getters.getGlobalFilters().length;
    },
});

cellMenuRegistry.add("use_global_filter", {
    name: _lt("Set as filter"),
    sequence: 175,
    action(env) {
        const cell = env.model.getters.getActiveCell();
        const filters = env.model.getters.getFiltersMatchingPivot(cell.content);
        env.model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
    },
    isVisible: (env) => {
        const cell = env.model.getters.getActiveCell();
        if (!cell) {
            return false;
        }
        const filters = env.model.getters.getFiltersMatchingPivot(cell.content);
        return filters.length > 0;
    },
});
