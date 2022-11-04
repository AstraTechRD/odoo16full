/** @odoo-module */

import { _t, _lt } from "web.core";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { REINSERT_LIST_CHILDREN } from "../list/list_actions";
import { INSERT_PIVOT_CELL_CHILDREN, REINSERT_PIVOT_CHILDREN } from "../pivot/pivot_actions";
const { topbarMenuRegistry } = spreadsheet.registries;
const { createFullMenuItem } = spreadsheet.helpers;

//--------------------------------------------------------------------------
// Spreadsheet context menu items
//--------------------------------------------------------------------------

topbarMenuRegistry.add("file", { name: _t("File"), sequence: 10 });
topbarMenuRegistry.addChild("new_sheet", ["file"], {
    name: _lt("New"),
    sequence: 10,
    isVisible: (env) => !env.isDashboardSpreadsheet,
    action: (env) => env.newSpreadsheet(),
});
topbarMenuRegistry.addChild("make_copy", ["file"], {
    name: _lt("Make a copy"),
    sequence: 20,
    isVisible: (env) => !env.isDashboardSpreadsheet,
    action: (env) => env.makeCopy(),
});
topbarMenuRegistry.addChild("save_as_template", ["file"], {
    name: _lt("Save as template"),
    sequence: 40,
    isVisible: (env) => !env.isDashboardSpreadsheet,
    action: (env) => env.saveAsTemplate(),
});
topbarMenuRegistry.addChild("download", ["file"], {
    name: _lt("Download"),
    sequence: 50,
    action: (env) => env.download(),
    isReadonlyAllowed: true,
});

topbarMenuRegistry.addChild("clear_history", ["file"], {
    name: _lt("Clear history"),
    sequence: 60,
    isVisible: (env) => env.debug,
    action: (env) => {
        env.model.session.snapshot(env.model.exportData());
        window.location.reload();
    },
});

topbarMenuRegistry.addChild("data_sources_data", ["data"], (env) => {
    const pivots = env.model.getters.getPivotIds();
    const children = pivots.map((pivotId, index) =>
        createFullMenuItem(`item_pivot_${pivotId}`, {
            name: env.model.getters.getPivotDisplayName(pivotId),
            sequence: 10 + index,
            action: (env) => {
                env.model.dispatch("SELECT_PIVOT", { pivotId: pivotId });
                env.openSidePanel("PIVOT_PROPERTIES_PANEL", {});
            },
            icon: "fa fa-table",
            separator: index === env.model.getters.getPivotIds().length - 1,
        })
    );
    const lists = env.model.getters.getListIds().map((listId, index) => {
        return createFullMenuItem(`item_list_${listId}`, {
            name: env.model.getters.getListDisplayName(listId),
            sequence: 10 + index + pivots.length,
            action: (env) => {
                env.model.dispatch("SELECT_ODOO_LIST", { listId: listId });
                env.openSidePanel("LIST_PROPERTIES_PANEL", {});
            },
            icon: "fa fa-list",
            separator: index === env.model.getters.getListIds().length - 1,
        });
    });
    return children.concat(lists).concat([
        createFullMenuItem(`refresh_all_data`, {
            name: _t("Refresh all data"),
            sequence: 1000,
            action: (env) => {
                env.model.dispatch("REFRESH_ALL_DATA_SOURCES");
            },
            separator: true,
        }),
        createFullMenuItem(`reinsert_pivot`, {
            name: _t("Re-insert pivot"),
            sequence: 1010,
            children: [REINSERT_PIVOT_CHILDREN],
            isVisible: (env) => env.model.getters.getPivotIds().length,
        }),
        createFullMenuItem(`insert_pivot_cell`, {
            name: _t("Insert pivot cell"),
            sequence: 1020,
            children: [INSERT_PIVOT_CELL_CHILDREN],
            isVisible: (env) => env.model.getters.getPivotIds().length,
            separator: true,
        }),
        createFullMenuItem(`reinsert_list`, {
            name: _t("Re-insert list"),
            sequence: 1021,
            children: [REINSERT_LIST_CHILDREN],
            isVisible: (env) => env.model.getters.getListIds().length,
        }),
    ]);
});
