/** @odoo-module */

import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { getBasicData } from "@spreadsheet/../tests/utils/data";
import { prepareWebClientForSpreadsheet } from "../utils/webclient_helpers";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { createSpreadsheet } from "../spreadsheet_test_utils";
import { selectCell } from "@spreadsheet/../tests/utils/commands";
import { dom } from "web.test_utils";

const { createEmptyWorkbookData } = spreadsheet.helpers;

let target;

QUnit.module(
    "documents_spreadsheet > Spreadsheet Client Action",
    {
        beforeEach: function () {
            target = getFixture();
        },
    },
    function () {
        QUnit.test("open spreadsheet with deprecated `active_id` params", async function (assert) {
            assert.expect(4);
            await prepareWebClientForSpreadsheet();
            const webClient = await createWebClient({
                serverData: { models: getBasicData() },
                mockRPC: async function (route, args) {
                    if (args.method === "join_spreadsheet_session") {
                        assert.step("spreadsheet-loaded");
                        assert.equal(args.args[0], 1, "It should load the correct spreadsheet");
                    }
                },
            });
            await doAction(webClient, {
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    active_id: 1,
                },
            });
            assert.containsOnce(target, ".o-spreadsheet", "It should have opened the spreadsheet");
            assert.verifySteps(["spreadsheet-loaded"]);
        });

        QUnit.test("open spreadsheet action with spreadsheet creation", async function (assert) {
            await prepareWebClientForSpreadsheet();
            const webClient = await createWebClient({
                serverData: { models: getBasicData() },
                mockRPC: async function (route, args) {
                    if (args.method === "create" && args.model === "documents.document") {
                        assert.step("create_sheet");
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
                        assert.equal(
                            args.args[0].folder_id,
                            1,
                            "It should be in the correct folder"
                        );
                    }
                },
            });
            await doAction(webClient, {
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    alwaysCreate: true,
                    createFromTemplateId: null,
                    createInFolderId: 1,
                },
            });
            assert.verifySteps(["create_sheet"]);
        });

        QUnit.test("breadcrumb is rendered in control panel", async function (assert) {
            assert.expect(4);

            const actions = {
                1: {
                    id: 1,
                    name: "Documents",
                    res_model: "documents.document",
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                },
            };
            const views = {
                "documents.document,false,list": '<tree><field name="name"/></tree>',
                "documents.document,false,search": "<search></search>",
            };
            const serverData = { actions, models: getBasicData(), views };
            await prepareWebClientForSpreadsheet();
            const webClient = await createWebClient({
                serverData,
                legacyParams: { withLegacyMockServer: true },
            });
            await doAction(webClient, 1);
            await doAction(webClient, {
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    spreadsheet_id: 1,
                },
            });
            const breadcrumbItems = $(target).find(".breadcrumb-item");
            assert.equal(
                breadcrumbItems[0].querySelector("a").innerText,
                "Documents",
                "It should display the breadcrumb"
            );
            assert.equal(
                breadcrumbItems[1].querySelector("input").value,
                "My spreadsheet",
                "It should display the spreadsheet title"
            );
            assert.ok(
                breadcrumbItems[1].querySelector(".o_spreadsheet_favorite"),
                "It should display the favorite toggle button"
            );
            assert.equal(
                breadcrumbItems.length,
                2,
                "The breadcrumb should only contain two list items"
            );
        });

        QUnit.test("Can open a spreadsheet in readonly", async function (assert) {
            const { model } = await createSpreadsheet({
                mockRPC: async function (route, args) {
                    if (args.method === "join_spreadsheet_session") {
                        return {
                            raw: "{}",
                            name: "name",
                            revisions: [],
                            isReadonly: true,
                        };
                    }
                },
            });
            assert.ok(model.getters.isReadonly());
        });

        QUnit.test("dialog window not normally displayed", async function (assert) {
            assert.expect(1);
            await createSpreadsheet();
            const dialog = document.querySelector(".o_dialog");
            assert.equal(dialog, undefined, "Dialog should not normally be displayed ");
        });

        QUnit.test("edit text window", async function (assert) {
            assert.expect(4);
            const { env } = await createSpreadsheet();
            env.editText("testTitle", () => {}, {
                error: "testErrorText",
                placeholder: "testPlaceholder",
            });
            await nextTick();
            const dialog = document.querySelector(".o_dialog");
            assert.ok(dialog !== undefined, "Dialog can be opened");
            assert.equal(
                document.querySelector(".modal-title").textContent,
                "testTitle",
                "Can set dialog title"
            );
            assert.equal(
                document.querySelector(".o_dialog_error_text").textContent,
                "testErrorText",
                "Can set dialog error text"
            );
            assert.equal(
                document.querySelectorAll(".modal-footer button").length,
                2,
                "Edit text have 2 buttons"
            );
        });

        QUnit.test("notify user window", async function (assert) {
            const { env } = await createSpreadsheet();
            env.notifyUser({ text: "this is a notification", tag: "notif" });
            await nextTick();
            const dialog = document.querySelector(".o_dialog");
            assert.ok(dialog !== undefined, "Dialog can be opened");
            const notif = document.querySelector("div.o_notification");
            assert.ok(notif !== undefined, "the notification exists");
            assert.equal(
                notif.querySelector("div.o_notification_content").textContent,
                "this is a notification",
                "Can set dialog content"
            );
            assert.ok(
                notif.classList.contains("border-warning"),
                "NotifyUser generates a warning notification"
            );
        });

        QUnit.test("raise error window", async function (assert) {
            assert.expect(4);
            const { env } = await createSpreadsheet();
            env.raiseError("this is a notification");
            await nextTick();
            const dialog = document.querySelector(".o_dialog");
            assert.ok(dialog !== undefined, "Dialog can be opened");
            assert.equal(
                document.querySelector(".modal-body div").textContent,
                "this is a notification",
                "Can set dialog content"
            );
            assert.equal(
                document.querySelector(".o_dialog_error_text"),
                null,
                "NotifyUser have no error text"
            );
            assert.equal(
                document.querySelectorAll(".modal-footer button").length,
                1,
                "NotifyUser have 1 button"
            );
        });

        QUnit.test("Grid has still the focus after a dialog", async function (assert) {
            assert.expect(1);

            const { model, env } = await createSpreadsheet();
            selectCell(model, "F4");
            env.raiseError("Notification");
            await nextTick();
            await dom.click(document.body.querySelector(".modal-footer .btn-primary"));
            await nextTick();
            assert.strictEqual(document.activeElement.className, "o-grid o-two-columns");
        });
    }
);
