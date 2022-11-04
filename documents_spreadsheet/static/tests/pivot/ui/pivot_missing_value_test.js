/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { nextTick } from "@web/../tests/helpers/utils";
import { dom } from "web.test_utils";
import { getBasicData } from "@spreadsheet/../tests/utils/data";
import { getCellFormula } from "@spreadsheet/../tests/utils/getters";
import { selectCell } from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheetFromPivotView } from "../../utils/pivot_helpers";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";

const { topbarMenuRegistry } = spreadsheet.registries;

const insertPivotCellPath = ["data", "insert_pivot_cell", "insert_pivot_cell_1"];

QUnit.module("documents_spreadsheet > Pivot missing values", {}, function () {
    QUnit.test("Open pivot dialog and insert a value, with UNDO/REDO", async function (assert) {
        assert.expect(4);

        const { model, env } = await createSpreadsheetFromPivotView();
        selectCell(model, "D8");
        const sheetId = model.getters.getActiveSheetId();
        await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
        await nextTick();
        assert.containsOnce(document.body, ".o_pivot_table_dialog");
        await dom.click(document.body.querySelectorAll(".o_pivot_table_dialog tr th")[1]);
        assert.equal(getCellFormula(model, "D8"), getCellFormula(model, "B1"));
        model.dispatch("REQUEST_UNDO");
        assert.equal(model.getters.getCell(sheetId, 3, 7), undefined);
        model.dispatch("REQUEST_REDO");
        assert.equal(getCellFormula(model, "D8"), getCellFormula(model, "B1"));
    });

    QUnit.test(
        "Insert missing value modal can show only the values not used in the current sheet",
        async function (assert) {
            assert.expect(4);

            const { model, env } = await createSpreadsheetFromPivotView();
            const missingValue = getCellFormula(model, "B3");
            selectCell(model, "B3");
            model.dispatch("DELETE_CONTENT", {
                sheetId: model.getters.getActiveSheetId(),
                target: model.getters.getSelectedZones(),
            });
            selectCell(model, "D8");
            await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
            await nextTick();
            assert.containsOnce(document.body, ".o_missing_value");
            await dom.click(document.body.querySelector("input#missing_values"));
            await nextTick();
            assert.containsOnce(document.body, ".o_missing_value");
            assert.containsN(document.body, ".o_pivot_table_dialog th", 4);
            await dom.click(document.body.querySelector(".o_missing_value"));
            assert.equal(getCellFormula(model, "D8"), missingValue);
        }
    );

    QUnit.test("Insert missing pivot value with two level of grouping", async function (assert) {
        assert.expect(4);

        const { model, env } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="product_id" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                    "partner,false,search": `<search/>`,
                },
            },
        });
        selectCell(model, "B5");
        model.dispatch("DELETE_CONTENT", {
            sheetId: model.getters.getActiveSheetId(),
            target: model.getters.getSelectedZones(),
        });
        selectCell(model, "D8");
        await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
        await nextTick();
        assert.containsOnce(document.body, ".o_missing_value");
        await dom.click(document.body.querySelector("input#missing_values"));
        await nextTick();
        assert.containsOnce(document.body, ".o_missing_value");
        assert.containsN(document.body, ".o_pivot_table_dialog td", 1);
        assert.containsN(document.body, ".o_pivot_table_dialog th", 4);
    });

    QUnit.test(
        "Insert missing value modal can show only the values not used in the current sheet with multiple levels",
        async function (assert) {
            assert.expect(4);

            const { model, env } = await createSpreadsheetFromPivotView({
                serverData: {
                    models: getBasicData(),
                    views: {
                        "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="product_id" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                        "partner,false,search": `<search/>`,
                    },
                },
            });
            const missingValue = getCellFormula(model, "C4");
            selectCell(model, "C4");
            model.dispatch("DELETE_CONTENT", {
                sheetId: model.getters.getActiveSheetId(),
                target: model.getters.getSelectedZones(),
            });
            selectCell(model, "J10");
            await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
            await nextTick();
            assert.containsOnce(document.body, ".o_missing_value");
            await dom.click(document.body.querySelector("input#missing_values"));
            await nextTick();
            assert.containsOnce(document.body, ".o_missing_value");
            assert.containsN(document.body, ".o_pivot_table_dialog th", 5);
            await dom.click(document.body.querySelector(".o_missing_value"));
            assert.equal(getCellFormula(model, "J10"), missingValue);
        }
    );

    QUnit.test(
        "Insert missing pivot value give the focus to the canvas when model is closed",
        async function (assert) {
            assert.expect(2);

            const { model, env } = await createSpreadsheetFromPivotView({
                serverData: {
                    models: getBasicData(),
                    views: {
                        "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="product_id" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                        "partner,false,search": `<search/>`,
                    },
                },
            });
            selectCell(model, "D8");
            await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
            await nextTick();
            assert.containsOnce(document.body, ".o_pivot_table_dialog");
            await dom.click(document.body.querySelectorAll(".o_pivot_table_dialog tr th")[1]);
            assert.strictEqual(document.activeElement.className, "o-grid o-two-columns");
        }
    );

    QUnit.test("One col header as missing value should be displayed", async function (assert) {
        assert.expect(1);

        const { model, env } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="product_id" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                    "partner,false,search": `<search/>`,
                },
            },
        });
        selectCell(model, "B1");
        model.dispatch("DELETE_CONTENT", {
            sheetId: model.getters.getActiveSheetId(),
            target: model.getters.getSelectedZones(),
        });
        await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
        await nextTick();
        await dom.click(document.body.querySelector("input#missing_values"));
        await nextTick();
        assert.containsOnce(document.body, ".o_missing_value");
    });

    QUnit.test("One row header as missing value should be displayed", async function (assert) {
        assert.expect(1);

        const { model, env } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="product_id" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                    "partner,false,search": `<search/>`,
                },
            },
        });
        selectCell(model, "A3");
        model.dispatch("DELETE_CONTENT", {
            sheetId: model.getters.getActiveSheetId(),
            target: model.getters.getSelectedZones(),
        });
        await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
        await nextTick();
        await dom.click(document.body.querySelector("input#missing_values"));
        await nextTick();
        assert.containsOnce(document.body, ".o_missing_value");
    });

    QUnit.test(
        "A missing col in the total measures with a pivot of two GB of cols",
        async function (assert) {
            assert.expect(2);

            const { model, env } = await createSpreadsheetFromPivotView({
                serverData: {
                    models: getBasicData(),
                    views: {
                        "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="bar" type="col"/>
                                <field name="product_id" type="col"/>
                                <field name="probability" type="measure"/>
                                <field name="foo" type="measure"/>
                            </pivot>`,
                        "partner,false,search": `<search/>`,
                    },
                },
            });
            await nextTick();
            await nextTick();
            selectCell(model, "F4");
            model.dispatch("DELETE_CONTENT", {
                sheetId: model.getters.getActiveSheetId(),
                target: model.getters.getSelectedZones(),
            });
            await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
            await nextTick();
            await dom.click(document.body.querySelector("input#missing_values"));
            await nextTick();
            assert.containsOnce(document.body, ".o_missing_value");
            assert.containsN(document.body, ".o_pivot_table_dialog th", 5);
        }
    );
});
