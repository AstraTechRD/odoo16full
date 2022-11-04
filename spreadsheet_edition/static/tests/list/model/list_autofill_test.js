/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";

import { getCellFormula, getCellValue } from "@spreadsheet/../tests/utils/getters";
import { autofill } from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheetWithList } from "@spreadsheet/../tests/utils/list";
import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";

/**
 * Get the computed value that would be autofilled starting from the given xc.
 * The starting xc should contains a List formula
 */
function getListAutofillValue(model, xc, { direction, steps }) {
    const content = getCellFormula(model, xc);
    const column = ["left", "right"].includes(direction);
    const increment = ["left", "top"].includes(direction) ? -steps : steps;
    return model.getters.getNextListValue(content, column, increment);
}

QUnit.module("spreadsheet > list autofill", {}, () => {
    QUnit.test("Autofill list values", async function (assert) {
        const { model } = await createSpreadsheetWithList();
        // From value to value
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "C4")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "right", steps: 1 }),
            getCellFormula(model, "D3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "left", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "bottom", steps: 2 }),
            getCellFormula(model, "C5")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "bottom", steps: 3 }),
            `=ODOO.LIST(1,5,"date")`
        );
        assert.strictEqual(getListAutofillValue(model, "C3", { direction: "right", steps: 4 }), "");
        // From value to header
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "left", steps: 1 }),
            getCellFormula(model, "A4")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 2 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 3 }),
            getCellFormula(model, "B1")
        );
        // From header to header
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "right", steps: 1 }),
            getCellFormula(model, "C3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "right", steps: 2 }),
            getCellFormula(model, "D3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "left", steps: 1 }),
            getCellFormula(model, "A3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B1", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "top", steps: 1 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A4", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A5")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A4", { direction: "top", steps: 1 }),
            getCellFormula(model, "A3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A4", { direction: "bottom", steps: 2 }),
            `=ODOO.LIST(1,5,"foo")`
        );
        assert.strictEqual(getListAutofillValue(model, "A4", { direction: "top", steps: 4 }), "");
        // From header to value
        assert.strictEqual(
            getListAutofillValue(model, "B2", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B2", { direction: "bottom", steps: 2 }),
            getCellFormula(model, "B4")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A3", { direction: "right", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A3", { direction: "right", steps: 5 }),
            getCellFormula(model, "F3")
        );
        assert.strictEqual(getListAutofillValue(model, "A3", { direction: "right", steps: 6 }), "");
    });

    QUnit.test("Autofill list correctly update the cache", async function (assert) {
        const { model } = await createSpreadsheetWithList({ linesNumber: 1 });
        autofill(model, "A2", "A3");
        assert.strictEqual(getCellValue(model, "A3"), "Loading...");
        await nextTick(); // Await for the batch collection of missing ids
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "A3"), 1);
    });

    QUnit.test("Tooltip of list formulas", async function (assert) {
        const { model } = await createSpreadsheetWithList();

        function getTooltip(xc, isColumn) {
            return model.getters.getTooltipListFormula(getCellFormula(model, xc), isColumn);
        }

        assert.strictEqual(getTooltip("A3", false), "Record #2");
        assert.strictEqual(getTooltip("A3", true), "Foo");
        assert.strictEqual(getTooltip("A1", false), "Foo");
        assert.strictEqual(getTooltip("A1", true), "Foo");
    });
});
