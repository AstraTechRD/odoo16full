/** @odoo-module */

import { doAction } from "@web/../tests/webclient/helpers";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { fields, dom } from "web.test_utils";
import { createSpreadsheet } from "../spreadsheet_test_utils";
import { getBasicData, getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { createSpreadsheetFromPivotView } from "../utils/pivot_helpers";

let target;

QUnit.module(
    "documents_spreadsheet > Spreadsheet Control Panel",
    {
        beforeEach: function () {
            target = getFixture();
        },
    },
    function () {
        QUnit.test("spreadsheet with generic untitled name is styled", async function (assert) {
            assert.expect(4);
            await createSpreadsheet();
            const input = target.querySelector(".breadcrumb-item input");
            assert.hasClass(input, "o-spreadsheet-untitled", "It should be styled as untitled");
            await fields.editInput(input, "My");
            assert.doesNotHaveClass(
                input,
                "o-spreadsheet-untitled",
                "It should not be styled as untitled"
            );
            await fields.editInput(input, "Untitled spreadsheet");
            assert.hasClass(input, "o-spreadsheet-untitled", "It should be styled as untitled");
            await fields.editInput(input, "");
            assert.hasClass(input, "o-spreadsheet-untitled", "It should be styled as untitled");
        });

        QUnit.test("untitled spreadsheet", async function (assert) {
            assert.expect(3);
            await createSpreadsheet({ spreadsheetId: 2 });
            const input = target.querySelector(".breadcrumb-item input");
            assert.hasClass(input, "o-spreadsheet-untitled", "It should be styled as untitled");
            assert.equal(input.value, "", "It should be empty");
            assert.equal(
                input.placeholder,
                "Untitled spreadsheet",
                "It should display a placeholder"
            );
            await nextTick();
        });

        QUnit.test("input width changes when content changes", async function (assert) {
            assert.expect(2);
            await createSpreadsheet();
            const input = target.querySelector(".breadcrumb-item input");
            await fields.editInput(input, "My");
            let width = input.offsetWidth;
            await fields.editInput(input, "My title");
            assert.ok(width < input.offsetWidth, "It should have grown to fit content");
            width = input.offsetWidth;
            await fields.editInput(input, "");
            assert.ok(width < input.offsetWidth, "It should have the size of the placeholder text");
        });

        QUnit.test("changing the input saves the name", async function (assert) {
            assert.expect(1);
            const serverData = getBasicServerData();
            await createSpreadsheet({ spreadsheetId: 2, serverData });
            const input = target.querySelector(".breadcrumb-item input");
            await fields.editAndTrigger(input, "My spreadsheet", ["change"]);
            assert.equal(
                serverData.models["documents.document"].records[1].name,
                "My spreadsheet",
                "It should have updated the name"
            );
        });

        QUnit.test("trailing white spaces are trimmed", async function (assert) {
            assert.expect(2);
            await createSpreadsheet();
            const input = target.querySelector(".breadcrumb-item input");
            await fields.editInput(input, "My spreadsheet  ");
            const width = input.offsetWidth;
            await dom.triggerEvent(input, "change");
            assert.equal(input.value, "My spreadsheet", "It should not have trailing white spaces");
            assert.ok(width > input.offsetWidth, "It should have resized");
        });

        QUnit.test("focus sets the placeholder as value and select it", async function (assert) {
            assert.expect(4);
            await createSpreadsheet({ spreadsheetId: 2 });
            const input = target.querySelector(".breadcrumb-item input");
            assert.equal(input.value, "", "It should be empty");
            await dom.triggerEvent(input, "focus");
            assert.equal(
                input.value,
                "Untitled spreadsheet",
                "Placeholder should have become the input value"
            );
            assert.equal(input.selectionStart, 0, "It should have selected the value");
            assert.equal(
                input.selectionEnd,
                input.value.length,
                "It should have selected the value"
            );
        });
        QUnit.test("only white spaces show the placeholder", async function (assert) {
            assert.expect(2);
            await createSpreadsheet();
            const input = target.querySelector(".breadcrumb-item input");
            await fields.editInput(input, "  ");
            const width = input.offsetWidth;
            await dom.triggerEvent(input, "change");
            assert.equal(input.value, "", "It should be empty");
            assert.ok(width < input.offsetWidth, "It should have the placeholder size");
        });

        QUnit.test("toggle favorite", async function (assert) {
            assert.expect(5);
            await createSpreadsheet({
                spreadsheetId: 1,
                mockRPC: async function (route, args) {
                    if (args.method === "toggle_favorited" && args.model === "documents.document") {
                        assert.step("favorite_toggled");
                        assert.deepEqual(args.args[0], [1], "It should write the correct document");
                        return true;
                    }
                    if (route.includes("dispatch_spreadsheet_message")) {
                        return Promise.resolve();
                    }
                },
            });
            assert.containsNone(target, ".favorite_button_enabled");
            const favorite = target.querySelector(".o_spreadsheet_favorite");
            await dom.click(favorite);
            assert.containsOnce(target, ".favorite_button_enabled");
            assert.verifySteps(["favorite_toggled"]);
        });

        QUnit.test("already favorited", async function (assert) {
            assert.expect(1);
            await createSpreadsheet({ spreadsheetId: 2 });
            assert.containsOnce(
                target,
                ".favorite_button_enabled",
                "It should already be favorited"
            );
        });

        QUnit.test("Spreadsheet action is named in breadcrumb", async function (assert) {
            assert.expect(3);
            const { webClient } = await createSpreadsheetFromPivotView();
            await doAction(webClient, {
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "pivot"]],
            });
            await nextTick();
            const items = target.querySelectorAll(".breadcrumb-item");
            const [breadcrumb1, breadcrumb2, breadcrumb3] = Array.from(items).map(
                (item) => item.innerText
            );
            assert.equal(breadcrumb1, "pivot view");
            assert.equal(breadcrumb2, "Untitled spreadsheet");
            assert.equal(breadcrumb3, "Partner");
        });

        QUnit.test(
            "Spreadsheet action is named in breadcrumb with the updated name",
            async function (assert) {
                assert.expect(3);
                const { webClient } = await createSpreadsheetFromPivotView({
                    serverData: {
                        models: getBasicData(),
                        views: {
                            "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="bar" type="col"/>
                                <field name="foo" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                            "partner,false,search": `<search/>`,
                        },
                    },
                });
                const input = target.querySelector(".breadcrumb-item input");
                await fields.editAndTrigger(input, "My awesome spreadsheet", ["change"]);
                await doAction(webClient, {
                    name: "Partner",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "pivot"]],
                });
                await nextTick();
                const items = target.querySelectorAll(".breadcrumb-item");
                const [breadcrumb1, breadcrumb2, breadcrumb3] = Array.from(items).map(
                    (item) => item.innerText
                );
                assert.equal(breadcrumb1, "pivot view");
                assert.equal(breadcrumb2, "My awesome spreadsheet");
                assert.equal(breadcrumb3, "Partner");
            }
        );
    }
);
