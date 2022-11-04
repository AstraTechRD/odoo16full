/** @odoo-module  */

import { selectCell, setCellContent } from "@spreadsheet/../tests/utils/commands";
import { getCellFormula } from "@spreadsheet/../tests/utils/getters";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/utils/pivot";

/**
 * Get the computed value that would be autofilled starting from the given xc.
 * The starting xc should contains a Pivot formula
 */
 export function getPivotAutofillValue(model, xc, { direction, steps }) {
    const content = getCellFormula(model, xc);
    const column = ["left", "right"].includes(direction);
    const increment = ["left", "top"].includes(direction) ? -steps : steps;
    return model.getters.getPivotNextAutofillValue(content, column, increment);
}


QUnit.module("spreadsheet > pivot_autofill", {}, () => {
    QUnit.test("Autofill pivot values", async function (assert) {
        assert.expect(28);

        const { model } = await createSpreadsheetWithPivot();

        // From value to value
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "C4")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B4", { direction: "top", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "right", steps: 1 }),
            getCellFormula(model, "D3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "left", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 2 }),
            getCellFormula(model, "C5")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 3 }),
            ""
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "right", steps: 4 }),
            ""
        );
        // From value to header
        assert.strictEqual(
            getPivotAutofillValue(model, "B4", { direction: "left", steps: 1 }),
            getCellFormula(model, "A4")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B4", { direction: "top", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B4", { direction: "top", steps: 2 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B4", { direction: "top", steps: 3 }),
            getCellFormula(model, "B1")
        );
        // From header to header
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "right", steps: 1 }),
            getCellFormula(model, "C3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "right", steps: 2 }),
            getCellFormula(model, "D3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "left", steps: 1 }),
            getCellFormula(model, "A3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B1", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "top", steps: 1 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A4", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A5")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A4", { direction: "top", steps: 1 }),
            getCellFormula(model, "A3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A4", { direction: "bottom", steps: 2 }),
            ""
        );
        assert.strictEqual(getPivotAutofillValue(model, "A4", { direction: "top", steps: 3 }), "");
        // From header to value
        assert.strictEqual(
            getPivotAutofillValue(model, "B2", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B2", { direction: "bottom", steps: 2 }),
            getCellFormula(model, "B4")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B2", { direction: "bottom", steps: 4 }),
            ""
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "right", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "right", steps: 5 }),
            getCellFormula(model, "F3")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "right", steps: 6 }),
            ""
        );
        // From total row header to value
        assert.strictEqual(
            getPivotAutofillValue(model, "A5", { direction: "right", steps: 1 }),
            getCellFormula(model, "B5")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A5", { direction: "right", steps: 5 }),
            getCellFormula(model, "F5")
        );
    });

    QUnit.test("Autofill with pivot positions", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        setCellContent(model, "C3", `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",1)`);
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "left", steps: 1 }),
            `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",0)`
        );
        /** Would be negative => just copy the value */
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "left", steps: 2 }),
            `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",1)`
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "right", steps: 1 }),
            `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",2)`
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "right", steps: 10 }),
            `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",11)`
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "top", steps: 1 }),
            `=ODOO.PIVOT(1,"probability","#bar",0,"#foo",1)`
        );
        /** Would be negative => just copy the value */
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "top", steps: 2 }),
            `=ODOO.PIVOT(1,"probability","#bar",1,"#foo",1)`
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", { direction: "bottom", steps: 1 }),
            `=ODOO.PIVOT(1,"probability","#bar",2,"#foo",1)`
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "C3", {
                direction: "bottom",
                steps: 10,
            }),
            `=ODOO.PIVOT(1,"probability","#bar",11,"#foo",1)`
        );
    });

    QUnit.test("Autofill pivot values with date in rows", async function (assert) {
        assert.expect(6);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A4").replace("10/2016", "05/2016")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "A5", { direction: "bottom", steps: 1 }),
            '=ODOO.PIVOT.HEADER(1,"date:month","01/2017")'
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B4").replace("10/2016", "05/2016")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B5", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B5").replace("12/2016", "01/2017")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B5", { direction: "top", steps: 1 }),
            getCellFormula(model, "B4").replace("10/2016", "11/2016")
        );
        assert.strictEqual(getPivotAutofillValue(model, "F6", { direction: "top", steps: 1 }), "");
    });

    QUnit.test("Autofill pivot values with date in cols", async function (assert) {
        assert.expect(3);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="row"/>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "B1", { direction: "right", steps: 1 }),
            getCellFormula(model, "B1").replace("01/20/2016", "01/21/2016")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B2", { direction: "right", steps: 1 }),
            getCellFormula(model, "B2").replace("01/20/2016", "01/21/2016")
        );
        assert.strictEqual(
            getPivotAutofillValue(model, "B3", { direction: "right", steps: 1 }),
            getCellFormula(model, "B3").replace("01/20/2016", "01/21/2016")
        );
    });

    QUnit.test("Autofill pivot values with date (day)", async function (assert) {
        assert.expect(1);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="day" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A3").replace("01/20/2016", "01/21/2016")
        );
    });

    QUnit.test("Autofill pivot values with date (month)", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            `=ODOO.PIVOT.HEADER(1,"date:month","05/2016")`
        );
    });

    QUnit.test("Autofill pivot values with date (quarter)", async function (assert) {
        assert.expect(1);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="quarter" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A3").replace("2/2016", "3/2016")
        );
    });

    QUnit.test("Autofill pivot values with date (year)", async function (assert) {
        assert.expect(1);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A3").replace("2016", "2017")
        );
    });

    QUnit.test("Autofill pivot values with date (no defined interval)", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(
            getPivotAutofillValue(model, "A3", { direction: "bottom", steps: 1 }),
            `=ODOO.PIVOT.HEADER(1,"date","05/2016")`
        );
    });

    QUnit.test("Tooltip of pivot formulas", async function (assert) {
        assert.expect(8);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "A3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "B3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "E3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "F3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "B1")), [
            { value: 1 },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "B2")), [
            { value: 1 },
            { value: "Probability" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(`=ODOO.PIVOT.HEADER("1")`, true), [
            { value: "Total" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(`=ODOO.PIVOT.HEADER("1")`, false), [
            { value: "Total" },
        ]);
    });

    QUnit.test("Tooltip of pivot formulas with 2 measures", async function (assert) {
        assert.expect(3);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="name" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "A3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "B3")), [
            { value: "2016" },
        ]);
        assert.deepEqual(model.getters.getTooltipFormula(getCellFormula(model, "C3"), true), [
            { value: "None" },
            { value: "Foo" },
        ]);
    });

    QUnit.test("Tooltip of empty pivot formula is empty", async function (assert) {
        assert.expect(1);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="name" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });
        selectCell(model, "A3");
        model.dispatch("AUTOFILL_SELECT", { col: 10, row: 10 });
        assert.equal(model.getters.getAutofillTooltip(), undefined);
    });

    QUnit.test(
        "Autofill content which contains pivots but which is not a pivot",
        async function (assert) {
            assert.expect(2);
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="date" interval="year" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            const a3 = getCellFormula(model, "A3").replace("=", "");
            const content = `=${a3} + ${a3}`;
            setCellContent(model, "F6", content);
            assert.strictEqual(
                getPivotAutofillValue(model, "F6", { direction: "bottom", steps: 1 }),
                content
            );
            assert.strictEqual(
                getPivotAutofillValue(model, "F6", { direction: "right", steps: 1 }),
                content
            );
        }
    );
});
