/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { click, mockDownload, nextTick } from "@web/../tests/helpers/utils";
import { createSpreadsheet } from "../spreadsheet_test_utils";

const { createEmptyWorkbookData, getMenuChildren } = spreadsheet.helpers;
const { topbarMenuRegistry } = spreadsheet.registries;

QUnit.module("documents_spreadsheet > Topbar Menu Items", {}, function () {
    QUnit.test("Can create a new spreadsheet from File menu", async function (assert) {
        const serverData = getBasicServerData();
        const spreadsheet = serverData.models["documents.document"].records[1];
        const { env } = await createSpreadsheet({
            spreadsheetId: spreadsheet.id,
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "create" && args.model === "documents.document") {
                    assert.step("create");
                    assert.deepEqual(
                        JSON.parse(args.args[0].raw),
                        createEmptyWorkbookData("Sheet1"),
                        "It should be an empty spreadsheet"
                    );
                    assert.equal(
                        args.args[0].name,
                        "Untitled spreadsheet",
                        "It should have the default name"
                    );
                }
            },
        });
        const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
        const newSpreadsheet = file.children.find((item) => item.id === "new_sheet");
        newSpreadsheet.action(env);
        assert.verifySteps(["create"]);
    });

    QUnit.test("Can download xlsx file", async function (assert) {
        mockDownload((options) => {
            assert.step(options.url);
            assert.ok(options.data.zip_name);
            assert.ok(options.data.files);
        });
        const { env } = await createSpreadsheet();
        const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
        const download = file.children.find((item) => item.id === "download");
        await download.action(env);
        assert.verifySteps(["/spreadsheet/xlsx"]);
    });

    QUnit.test("Can make a copy", async function (assert) {
        const serverData = getBasicServerData();
        const spreadsheet = serverData.models["documents.document"].records[1];
        const { env, model } = await createSpreadsheet({
            spreadsheetId: spreadsheet.id,
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "copy" && args.model === "documents.document") {
                    assert.step("copy");
                    assert.equal(
                        args.kwargs.default.raw,
                        JSON.stringify(model.exportData()),
                        "It should copy the data"
                    );
                    assert.equal(
                        args.kwargs.default.spreadsheet_snapshot,
                        false,
                        "It should reset the snapshot"
                    );
                    return 1;
                }
            },
        });
        const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
        const makeCopy = file.children.find((item) => item.id === "make_copy");
        makeCopy.action(env);
        assert.verifySteps(["copy"]);
    });

    QUnit.test("Lazy load currencies", async function (assert) {
        const { env } = await createSpreadsheet({
            mockRPC: async function (route, args) {
                if (args.method === "search_read" && args.model === "res.currency") {
                    assert.step("currencies-loaded");
                    return [
                        {
                            decimalPlaces: 2,
                            name: "Euro",
                            code: "EUR",
                            symbol: "€",
                            position: "after",
                        },
                    ];
                }
            },
        });
        assert.verifySteps([]);
        const root = topbarMenuRegistry.getAll().find((item) => item.id === "format");
        const numbers = getMenuChildren(root, env)
            .find((item) => item.id === "format_number");
        const customCurrencies = getMenuChildren(numbers, env)
            .find((item) => item.id === "format_custom_currency");
        await customCurrencies.action(env);
        await nextTick();
        await click(document.querySelector(".o-sidePanelClose"));
        await customCurrencies.action(env);
        await nextTick();
        assert.verifySteps(["currencies-loaded"]);
    });
});
