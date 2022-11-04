/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

import { spreadsheetLinkMenuCellService } from "@spreadsheet/ir_ui_menu/index";
import { registry } from "@web/core/registry";
import { createSpreadsheet } from "../../spreadsheet_test_utils";
import { click, getFixture, legacyExtraNextTick, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { getCell } from "@spreadsheet/../tests/utils/getters";
import { setCellContent, setSelection } from "@spreadsheet/../tests/utils/commands";
import { getMenuServerData } from "@spreadsheet/../tests/links/menu_data_utils";

const { registries, components } = spreadsheet;
const { cellMenuRegistry } = registries;
const { Grid } = components;

let target;

function labelInput() {
    return target.querySelectorAll(".o-link-editor input")[0];
}

function urlInput() {
    return target.querySelectorAll(".o-link-editor input")[1];
}

/**
 * Create a spreadsheet and open the menu selector to
 * insert a menu link in A1.
 * @param {object} params
 * @param {function} [params.mockRPC]
 */
async function openMenuSelector(params = {}) {
    const { webClient, env, model } = await createSpreadsheet({
        serverData: getMenuServerData(),
        mockRPC: params.mockRPC,
    });
    const insertLinkMenu = cellMenuRegistry.getAll().find((item) => item.id === "insert_link");
    await insertLinkMenu.action(env);
    await nextTick();
    await click(target, ".o-special-link");
    await click(target, ".o-menu-item[data-name='odooMenu']");
    return { webClient, env, model };
}

function beforeEach() {
    target = getFixture();
    registry.category("services").add("spreadsheetLinkMenuCell", spreadsheetLinkMenuCellService);
    patchWithCleanup(Grid.prototype, {
        setup() {
            this._super();
            this.hoveredCell = {col : 0, row : 0};
        },
    });
}

QUnit.module("spreadsheet > menu link ui", { beforeEach }, () => {
    QUnit.test("insert a new ir menu link", async function (assert) {
        const { model } = await openMenuSelector();
        await click(target, ".o_field_many2one input");
        assert.ok(target.querySelector("button.o-confirm").disabled);
        await click(document.querySelectorAll(".ui-menu-item")[0]);
        await click(document, "button.o-confirm");
        assert.equal(labelInput().value, "menu with xmlid", "The label should be the menu name");
        assert.equal(
            urlInput().value,
            "menu with xmlid",
            "The url displayed should be the menu name"
        );
        assert.ok(urlInput().disabled, "The url input should be disabled");
        await click(target, "button.o-save");
        const cell = getCell(model, "A1");
        assert.equal(
            cell.content,
            "[menu with xmlid](odoo://ir_menu_xml_id/test_menu)",
            "The content should be the complete markdown link"
        );
        assert.equal(
            target.querySelector(".o-link-tool a").text,
            "menu with xmlid",
            "The link tooltip should display the menu name"
        );
    });

    QUnit.test("fetch available menus", async function (assert) {
        const { env } = await openMenuSelector({
            mockRPC: function (route, args) {
                if (args.method === "name_search" && args.model === "ir.ui.menu") {
                    assert.step("fetch_menus");
                    assert.deepEqual(
                        args.kwargs.args,
                        [
                            ["action", "!=", false],
                            ["id", "in", [1, 2]],
                        ],
                        "user defined groupby should have precedence on action groupby"
                    );
                }
            },
        });
        assert.deepEqual(
            env.services.menu.getAll().map((menu) => menu.id),
            [1, 2, "root"]
        );
        await click(target, ".o_field_many2one input");
        assert.verifySteps(["fetch_menus"]);
    });

    QUnit.test(
        "insert a new ir menu link when the menu does not have an xml id",
        async function (assert) {
            const { model } = await openMenuSelector();
            await click(target, ".o_field_many2one input");
            assert.ok(target.querySelector("button.o-confirm").disabled);
            const item = document.querySelectorAll(".ui-menu-item")[1];
            // don't ask why it's needed and why it only works with a jquery event >:(
            $(item).trigger("mouseenter");
            await click(item);
            await click(target, "button.o-confirm");
            assert.equal(
                labelInput().value,
                "menu without xmlid",
                "The label should be the menu name"
            );
            assert.equal(
                urlInput().value,
                "menu without xmlid",
                "The url displayed should be the menu name"
            );
            assert.ok(urlInput().disabled, "The url input should be disabled");
            await click(target, "button.o-save");
            const cell = getCell(model, "A1");
            assert.equal(
                cell.content,
                "[menu without xmlid](odoo://ir_menu_id/2)",
                "The content should be the complete markdown link"
            );
            assert.equal(
                target.querySelector(".o-link-tool a").text,
                "menu without xmlid",
                "The link tooltip should display the menu name"
            );
        }
    );

    QUnit.test("cancel ir.menu selection", async function (assert) {
        await openMenuSelector();
        await click(target, ".o_field_many2one input");
        await click(document.querySelectorAll(".ui-menu-item")[0]);
        assert.containsOnce(target, ".o-ir-menu-selector");
        await click(target, ".modal-footer button.o-cancel");
        assert.containsNone(target, ".o-ir-menu-selector");
        assert.equal(labelInput().value, "", "The label should be empty");
        assert.equal(urlInput().value, "", "The url displayed should be the menu name");
    });

    QUnit.test("menu many2one field input is focused", async function (assert) {
        await openMenuSelector(this.serverData);
        assert.equal(
            document.activeElement,
            target.querySelector(".o_field_many2one input"),
            "the input should be focused"
        );
    });

    QUnit.test("ir.menu link keep breadcrumb", async function (assert) {
        const { model } = await createSpreadsheet({
            serverData: getMenuServerData(),
        });
        setCellContent(model, "A1", "[menu with xmlid](odoo://ir_menu_xml_id/test_menu)");
        setSelection(model, "A1");
        await nextTick();
        const link = document.querySelector("a.o-link");
        await click(link);
        await legacyExtraNextTick();
        const items = document.querySelectorAll(".breadcrumb-item");
        const [breadcrumb1, breadcrumb2] = Array.from(items).map((item) => item.innerText);
        assert.equal(breadcrumb1, "Untitled spreadsheet");
        assert.equal(breadcrumb2, "action1");
    });
});
