/** @odoo-module */

import { click, getFixture, triggerEvent } from "@web/../tests/helpers/utils";
import { createBasicChart } from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheet } from "../spreadsheet_test_utils";
import { createSpreadsheetFromGraphView, openChartSidePanel } from "../utils/chart_helpers";
import { patch, unpatch } from "@web/core/utils/patch";
import { GraphController } from "@web/views/graph/graph_controller";
import { patchGraphSpreadsheet } from "@spreadsheet_edition/assets/graph_view/graph_view";

function beforeEach() {
    patch(GraphController.prototype, "graph_spreadsheet", patchGraphSpreadsheet);
}

function afterEach() {
    unpatch(GraphController.prototype, "graph_spreadsheet");
}

QUnit.module("documents_spreadsheet > chart side panel", { beforeEach, afterEach }, () => {
    QUnit.test("Open a chart panel", async (assert) => {
        const { model, env } = await createSpreadsheetFromGraphView();
        await openChartSidePanel(model, env);
        const target = getFixture();
        assert.ok(target.querySelector(".o-sidePanel .o-sidePanelBody .o-chart"));
    });

    QUnit.test("From an Odoo chart, can only change to an Odoo chart", async (assert) => {
        const { model, env } = await createSpreadsheetFromGraphView();
        await openChartSidePanel(model, env);
        const target = getFixture();
        /** @type {NodeListOf<HTMLOptionElement>} */
        const options = target.querySelectorAll(".o-type-selector option");
        assert.strictEqual(options.length, 3);
        assert.strictEqual(options[0].value, "odoo_bar");
        assert.strictEqual(options[1].value, "odoo_line");
        assert.strictEqual(options[2].value, "odoo_pie");
    });

    QUnit.test(
        "From a spreadsheet chart, can only change to a spreadsheet chart",
        async (assert) => {
            const { model, env } = await createSpreadsheet();
            createBasicChart(model, "1");
            await openChartSidePanel(model, env);
            const target = getFixture();
            /** @type {NodeListOf<HTMLOptionElement>} */
            const options = target.querySelectorAll(".o-type-selector option");
            assert.strictEqual(options.length, 5);
            assert.strictEqual(options[0].value, "bar");
            assert.strictEqual(options[1].value, "gauge");
            assert.strictEqual(options[2].value, "line");
            assert.strictEqual(options[3].value, "pie");
            assert.strictEqual(options[4].value, "scorecard");
        }
    );

    QUnit.test("Change odoo chart type", async (assert) => {
        const { model, env } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_bar");
        await openChartSidePanel(model, env);
        const target = getFixture();
        /** @type {HTMLSelectElement} */
        const select = target.querySelector(".o-type-selector");
        select.value = "odoo_pie";
        await triggerEvent(select, null, "change");
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_pie");
        select.value = "odoo_line";
        await triggerEvent(select, null, "change");
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_line");
        assert.strictEqual(model.getters.getChart(chartId).verticalAxisPosition, "left");
        assert.strictEqual(model.getters.getChart(chartId).stacked, false);
        select.value = "odoo_bar";
        await triggerEvent(select, null, "change");
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_bar");
        assert.strictEqual(model.getters.getChart(chartId).stacked, false);
    });

    QUnit.test("stacked line chart", async (assert) => {
        const { model, env } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        await openChartSidePanel(model, env);
        const target = getFixture();
        /** @type {HTMLSelectElement} */
        const select = target.querySelector(".o-type-selector");
        select.value = "odoo_line";
        await triggerEvent(select, null, "change");

        // checked by default
        assert.strictEqual(model.getters.getChart(chartId).stacked, true);
        assert.containsOnce(target, ".o_checkbox input:checked", "checkbox should be checked");

        // uncheck
        await click(target, ".o_checkbox input:checked");
        assert.strictEqual(model.getters.getChart(chartId).stacked, false);
        assert.containsNone(
            target,
            ".o_checkbox input:checked",
            "checkbox should no longer be checked"
        );

        // check
        await click(target, ".o_checkbox input");
        assert.strictEqual(model.getters.getChart(chartId).stacked, true);
        assert.containsOnce(target, ".o_checkbox input:checked", "checkbox should be checked");
    });

    QUnit.test("Change the title of a chart", async (assert) => {
        const { model, env } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_bar");
        await openChartSidePanel(model, env);
        const target = getFixture();
        await click(target, ".o-panel-design");
        /** @type {HTMLInputElement} */
        const input = target.querySelector(".o-chart-title input");
        input.value = "bla";
        await triggerEvent(input, null, "change");
        assert.strictEqual(model.getters.getChart(chartId).title, "bla");
    });
});
