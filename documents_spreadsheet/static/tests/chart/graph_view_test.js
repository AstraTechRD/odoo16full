/** @odoo-module */

import { patchGraphSpreadsheet } from "@spreadsheet_edition/assets/graph_view/graph_view";
import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import { click, patchWithCleanup, triggerEvent } from "@web/../tests/helpers/utils";
import { patch, unpatch } from "@web/core/utils/patch";
import { GraphController } from "@web/views/graph/graph_controller";
import {
    createSpreadsheetFromGraphView,
    spawnGraphViewForSpreadsheet,
} from "../utils/chart_helpers";
import { getSpreadsheetActionModel } from "../utils/webclient_helpers";

function beforeEach() {
    patch(GraphController.prototype, "graph_spreadsheet", patchGraphSpreadsheet);
}

function afterEach() {
    unpatch(GraphController.prototype, "graph_spreadsheet");
}

QUnit.module("documents_spreadsheet > graph view", { beforeEach, afterEach }, () => {
    QUnit.test("simple chart insertion", async (assert) => {
        const { model } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
    });

    QUnit.test("The chart mode is the selected one", async (assert) => {
        const { model } = await createSpreadsheetFromGraphView({
            actions: async (target) => {
                await click(target, ".fa-pie-chart");
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_pie");
    });

    QUnit.test("The chart order is the selected one when selecting desc", async (assert) => {
        const { model } = await createSpreadsheetFromGraphView({
            actions: async (target) => {
                await click(target, ".fa-sort-amount-desc");
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).metaData.order, "DESC");
    });

    QUnit.test("The chart order is the selected one when selecting asc", async (assert) => {
        const { model } = await createSpreadsheetFromGraphView({
            actions: async (target) => {
                await click(target, ".fa-sort-amount-asc");
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).metaData.order, "ASC");
    });

    QUnit.test("Chart name can be changed from the dialog", async (assert) => {
        await spawnGraphViewForSpreadsheet();

        let spreadsheetAction;
        patchWithCleanup(SpreadsheetAction.prototype, {
            setup() {
                this._super();
                spreadsheetAction = this;
            },
        });
        await click(document.body.querySelector(".o_graph_insert_spreadsheet"));
        /** @type {HTMLInputElement} */
        const name = document.body.querySelector(".o_spreadsheet_name");
        name.value = "New name";
        await triggerEvent(name, null, "input");
        await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
        const model = getSpreadsheetActionModel(spreadsheetAction);
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.equal(model.getters.getChart(chartId).title, "New name");
    });
});
