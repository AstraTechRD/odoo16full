/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { insertList } from "@spreadsheet_edition/bundle/list/list_init_callback";
import { InsertListSpreadsheetMenu } from "@spreadsheet_edition/assets/list_view/insert_list_spreadsheet_menu_owl";
import { selectCell, setCellContent } from "@spreadsheet/../tests/utils/commands";
import { getBasicData, getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { getCell, getCellFormula } from "@spreadsheet/../tests/utils/getters";
import { click, getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { toggleFavoriteMenu } from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { createSpreadsheetFromListView } from "../utils/list_helpers";
import { dom } from "web.test_utils";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";

const { getMenuChildren } = spreadsheet.helpers;
const { topbarMenuRegistry, cellMenuRegistry } = spreadsheet.registries;
const { toZone } = spreadsheet.helpers;

QUnit.module("document_spreadsheet > list view", {}, () => {
    QUnit.test("List export with a invisible field", async (assert) => {
        const { model } = await createSpreadsheetFromListView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,list": `
                        <tree string="Partners">
                            <field name="foo" invisible="1"/>
                            <field name="bar"/>
                        </tree>`,
                    "partner,false,search": "<search/>",
                },
            },
        });
        assert.deepEqual(model.getters.getListDefinition("1").columns, ["bar"]);
    });

    QUnit.test("List export with a widget handle", async (assert) => {
        const { model } = await createSpreadsheetFromListView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,list": `
                            <tree string="Partners">
                                <field name="foo" widget="handle"/>
                                <field name="bar"/>
                            </tree>`,
                    "partner,false,search": "<search/>",
                },
            },
        });
        assert.deepEqual(model.getters.getListDefinition("1").columns, ["bar"]);
    });

    QUnit.test("Open list properties properties", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView();

        const dataRoot = topbarMenuRegistry.getAll().find((item) => item.id === "data");
        const children = getMenuChildren(dataRoot, env);
        const openProperties = children.find((item) => item.id === "item_list_1");
        openProperties.action(env);
        await nextTick();
        const target = getFixture();
        let title = $(target).find(".o-sidePanelTitle")[0].innerText;
        assert.equal(title, "List properties");

        const sections = $(target).find(".o_side_panel_section");
        assert.equal(sections.length, 4, "it should have 4 sections");
        const [pivotName, pivotModel, domain] = sections;

        assert.equal(pivotName.children[0].innerText, "List Name");
        assert.equal(pivotName.children[1].innerText, "(#1) Partners");

        assert.equal(pivotModel.children[0].innerText, "Model");
        assert.equal(pivotModel.children[1].innerText, "Partner (partner)");

        assert.equal(domain.children[0].innerText, "Domain");
        assert.equal(domain.children[1].innerText, "Match all records");

        // opening from a non pivot cell
        model.dispatch("SELECT_ODOO_LIST", {});
        env.openSidePanel("LIST_PROPERTIES_PANEL", {
            listId: undefined,
        });
        await nextTick();
        title = $(target).find(".o-sidePanelTitle")[0].innerText;
        assert.equal(title, "List properties");

        assert.containsOnce(target, ".o_side_panel_select");
    });

    QUnit.test("Add list in an existing spreadsheet", async (assert) => {
        const { model } = await createSpreadsheetFromListView();
        const list = model.getters.getListDefinition("1");
        const fields = model.getters.getListDataSource("1").getFields();
        const callback = insertList.bind({ isEmptySpreadsheet: false })({
            list: list,
            threshold: 10,
            fields: fields,
        });
        model.dispatch("CREATE_SHEET", { sheetId: "42", position: 1 });
        const activeSheetId = model.getters.getActiveSheetId();
        assert.deepEqual(model.getters.getSheetIds(), [activeSheetId, "42"]);
        await callback(model);
        assert.strictEqual(model.getters.getSheetIds().length, 3);
        assert.deepEqual(model.getters.getSheetIds()[0], activeSheetId);
        assert.deepEqual(model.getters.getSheetIds()[1], "42");
    });

    QUnit.test("Verify absence of pivot properties on non-pivot cell", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView();
        selectCell(model, "Z26");
        const root = cellMenuRegistry.getAll().find((item) => item.id === "listing_properties");
        assert.notOk(root.isVisible(env));
    });

    QUnit.test("Re-insert a list correctly ask for lines number", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView();
        selectCell(model, "Z26");
        await doMenuAction(topbarMenuRegistry, ["data", "reinsert_list", "reinsert_list_1"], env);
        await nextTick();
        /** @type {HTMLInputElement} */
        const input = document.body.querySelector(".modal-body input");
        assert.ok(input);
        assert.strictEqual(input.type, "number");
    });

    QUnit.test("user related context is not saved in the spreadsheet", async function (assert) {
        assert.expect(1);
        setupViewRegistries();

        registry.category("favoriteMenu").add(
            "insert-list-spreadsheet-menu",
            {
                Component: InsertListSpreadsheetMenu,
                groupNumber: 4,
            },
            { sequence: 5 }
        );

        patchWithCleanup(ListRenderer.prototype, {
            getListForSpreadsheet() {
                const result = this._super(...arguments);
                assert.deepEqual(
                    result.list.context,
                    {
                        default_stage_id: 5,
                    },
                    "user related context is not stored in context"
                );
                return result;
            },
        });

        const context = {
            allowed_company_ids: [15],
            default_stage_id: 5,
            search_default_stage_id: 5,
            tz: "bx",
            lang: "FR",
            uid: 4,
        };
        const serverData = { models: getBasicData() };
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            context,
            arch: `
                <tree string="Partners">
                    <field name="bar"/>
                    <field name="product_id"/>
                </tree>
            `,
            config: {
                actionType: "ir.actions.act_window",
                getDisplayName: () => "Test",
                viewType: "list",
            },
        });
        const target = getFixture();
        await toggleFavoriteMenu(target);
        await click(target, ".o_insert_list_spreadsheet_menu");
        await click(target, ".modal button.btn-primary");
    });

    QUnit.test("Can see record of a list", async function (assert) {
        const { webClient, model } = await createSpreadsheetFromListView();
        const listId = model.getters.getListIds()[0];
        const dataSource = model.getters.getListDataSource(listId);
        const env = {
            ...webClient.env,
            model,
            services: {
                ...model.config.evalContext.env.services,
                action: {
                    doAction: (params) => {
                        assert.step(params.res_model);
                        assert.step(params.res_id.toString());
                    },
                },
            },
        };
        selectCell(model, "A2");
        const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
        await root.action(env);
        assert.verifySteps(["partner", dataSource.getIdFromPosition(0).toString()]);

        selectCell(model, "A3");
        await root.action(env);
        assert.verifySteps(["partner", dataSource.getIdFromPosition(1).toString()]);

        // From a cell inside a merge
        model.dispatch("ADD_MERGE", {
            sheetId: model.getters.getActiveSheetId(),
            target: [toZone("A3:B3")],
            force: true, // there are data in B3
        });
        selectCell(model, "B3");
        await root.action(env);
        assert.verifySteps(["partner", dataSource.getIdFromPosition(1).toString()]);
    });

    QUnit.test(
        "See record of list is only displayed on list formula with only one list formula",
        async function (assert) {
            const { webClient, model } = await createSpreadsheetFromListView();
            const env = {
                ...webClient.env,
                model,
                services: model.config.evalContext.env.services,
            };
            setCellContent(model, "A1", "test");
            setCellContent(model, "A2", `=ODOO.LIST("1","1","foo")`);
            setCellContent(model, "A3", `=ODOO.LIST("1","1","foo")+LIST("1","1","foo")`);
            const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");

            selectCell(model, "A1");
            assert.strictEqual(root.isVisible(env), false);
            selectCell(model, "A2");
            assert.strictEqual(root.isVisible(env), true);
            selectCell(model, "A3");
            assert.strictEqual(root.isVisible(env), false);
        }
    );

    QUnit.test("See records is visible even if the formula is lowercase", async function (assert) {
        const { env, model } = await createSpreadsheetFromListView();
        selectCell(model, "B2");
        const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
        assert.ok(root.isVisible(env));
        setCellContent(model, "B2", getCellFormula(model, "B2").replace("ODOO.LIST", "odoo.list"));
        assert.ok(root.isVisible(env));
    });

    QUnit.test("See records is not visible if the formula is in error", async function (assert) {
        const { env, model } = await createSpreadsheetFromListView();
        selectCell(model, "B2");
        const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
        assert.ok(root.isVisible(env));
        setCellContent(
            model,
            "B2",
            getCellFormula(model, "B2").replace(`ODOO.LIST(1`, `ODOO.LIST("5)`)
        ); //Invalid id
        assert.ok(getCell(model, "B2").evaluated.error.message);
        assert.notOk(root.isVisible(env));
    });

    QUnit.test("Update the list title from the side panel", async function (assert) {
        assert.expect(1);

        const { model, env } = await createSpreadsheetFromListView();
        // opening from a pivot cell
        const sheetId = model.getters.getActiveSheetId();
        const listA3 = model.getters.getListIdFromPosition(sheetId, 0, 2);
        model.dispatch("SELECT_ODOO_LIST", { listId: listA3 });
        env.openSidePanel("LIST_PROPERTIES_PANEL", {
            listId: listA3,
        });
        await nextTick();
        await click(document.body.querySelector(".o_sp_en_rename"));
        document.body.querySelector(".o_sp_en_name").value = "new name";
        await dom.triggerEvent(document.body.querySelector(".o_sp_en_name"), "input");
        await click(document.body.querySelector(".o_sp_en_save"));
        assert.equal(model.getters.getListName(listA3), "new name");
    });

    QUnit.test("Update the list domain from the side panel", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView();
        const [listId] = model.getters.getListIds();
        model.dispatch("SELECT_ODOO_LIST", { listId });
        env.openSidePanel("LIST_PROPERTIES_PANEL", {
            listId,
        });
        await nextTick();
        const fixture = getFixture();
        await click(fixture.querySelector(".o_edit_domain"));
        await click(fixture.querySelector(".o_domain_add_first_node_button"));
        await click(fixture.querySelector(".modal-footer .btn-primary"));
        assert.deepEqual(model.getters.getListDefinition(listId).domain, [["id", "=", 1]]);
        assert.equal(fixture.querySelector(".o_domain_selector_row").innerText, "ID\n= 1");
    });

    QUnit.test(
        "Inserting a list preserves the ascending sorting from the list",
        async function (assert) {
            const serverData = getBasicServerData();
            serverData.models.partner.fields.foo.sortable = true;
            const { model } = await createSpreadsheetFromListView({
                serverData,
                orderBy: [{ name: "foo", asc: true }],
                linesNumber: 4,
            });
            assert.ok(getCell(model, "A2").evaluated.value <= getCell(model, "A3").evaluated.value);
            assert.ok(getCell(model, "A3").evaluated.value <= getCell(model, "A4").evaluated.value);
            assert.ok(getCell(model, "A4").evaluated.value <= getCell(model, "A5").evaluated.value);
        }
    );

    QUnit.test(
        "Inserting a list preserves the descending sorting from the list",
        async function (assert) {
            const serverData = getBasicServerData();
            serverData.models.partner.fields.foo.sortable = true;
            const { model } = await createSpreadsheetFromListView({
                serverData,
                orderBy: [{ name: "foo", asc: false }],
                linesNumber: 4,
            });
            assert.ok(getCell(model, "A2").evaluated.value >= getCell(model, "A3").evaluated.value);
            assert.ok(getCell(model, "A3").evaluated.value >= getCell(model, "A4").evaluated.value);
            assert.ok(getCell(model, "A4").evaluated.value >= getCell(model, "A5").evaluated.value);
        }
    );

    QUnit.test(
        "Sorting from the list is displayed in the properties panel",
        async function (assert) {
            const serverData = getBasicServerData();
            serverData.models.partner.fields.foo.sortable = true;
            serverData.models.partner.fields.bar.sortable = true;
            const { model, env } = await createSpreadsheetFromListView({
                serverData,
                orderBy: [
                    { name: "foo", asc: true },
                    { name: "bar", asc: false },
                ],
                linesNumber: 4,
            });
            const sheetId = model.getters.getActiveSheetId();
            const listId = model.getters.getListIds(sheetId)[0];
            model.dispatch("SELECT_ODOO_LIST", { listId });
            env.openSidePanel("LIST_PROPERTIES_PANEL", {
                listId,
            });
            await nextTick();
            const fixture = getFixture();
            const sortingSection = fixture.querySelectorAll(".o_side_panel_section")[3];
            const barSortingText = sortingSection.querySelectorAll("div")[1].innerText;
            const fooSortingText = sortingSection.querySelectorAll("div")[2].innerText;
            assert.strictEqual(barSortingText, "Bar (descending)");
            assert.strictEqual(fooSortingText, "Foo (ascending)");
        }
    );

    QUnit.test("can refresh a sorted list in the properties panel", async function (assert) {
        const serverData = getBasicServerData();
        serverData.models.partner.fields.foo.sortable = true;
        serverData.models.partner.fields.bar.sortable = true;
        const { model, env } = await createSpreadsheetFromListView({
            serverData,
            orderBy: [{ name: "foo", asc: true }],
            linesNumber: 4,
        });
        const sheetId = model.getters.getActiveSheetId();
        const listId = model.getters.getListIds(sheetId)[0];
        model.dispatch("SELECT_ODOO_LIST", { listId });
        env.openSidePanel("LIST_PROPERTIES_PANEL", {
            listId,
        });
        await nextTick();
        const fixture = getFixture();
        const sortingSection = fixture.querySelectorAll(".o_side_panel_section")[3];
        assert.strictEqual(sortingSection.querySelectorAll("div")[1].innerText, "Foo (ascending)");
        await click(fixture, ".o_refresh_list");
        assert.strictEqual(sortingSection.querySelectorAll("div")[1].innerText, "Foo (ascending)");
    });
});
