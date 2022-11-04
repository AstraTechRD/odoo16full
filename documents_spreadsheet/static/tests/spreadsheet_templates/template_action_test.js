/** @odoo-module */

import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { jsonToBase64, base64ToJson } from "@spreadsheet_edition/bundle/helpers";
import { createSpreadsheetTemplate } from "../spreadsheet_test_utils";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import { getCellValue } from "@spreadsheet/../tests/utils/getters";
import { SpreadsheetTemplateAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_template/spreadsheet_template_action";

const { onMounted } = owl;
const { Model } = spreadsheet;

QUnit.module("documents_spreadsheet > template action", {}, () => {
    QUnit.test(
        "open template client action without collaborative indicators",
        async function (assert) {
            assert.expect(2);
            const webClient = await createWebClient({
                serverData: getBasicServerData(),
            });
            await doAction(webClient, {
                type: "ir.actions.client",
                tag: "action_open_template",
                params: { spreadsheet_id: 1 },
            });
            const target = getFixture();
            assert.containsNone(target, ".o_spreadsheet_sync_status");
            assert.containsNone(target, ".o_spreadsheet_number_users");
        }
    );

    QUnit.test("collaboration communication is disabled", async function (assert) {
        assert.expect(1);
        const webClient = await createWebClient({
            serverData: getBasicServerData(),
            mockRPC: async function (route) {
                if (route.includes("join_spreadsheet_session")) {
                    assert.ok(false, "it should not join a collaborative session");
                }
                if (route.includes("dispatch_spreadsheet_message")) {
                    assert.ok(false, "it should not dispatch collaborative revisions");
                }
            },
        });
        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "action_open_template",
            params: { spreadsheet_id: 1 },
        });
        assert.ok(true);
    });

    QUnit.test("open template with non Latin characters", async function (assert) {
        assert.expect(1);
        const model = new Model();
        setCellContent(model, "A1", "😃");
        const serverData = getBasicServerData();
        serverData.models["spreadsheet.template"].records = [
            {
                id: 99,
                name: "template",
                data: jsonToBase64(model.exportData()),
            },
        ];
        const { model: template } = await createSpreadsheetTemplate({
            serverData,
            spreadsheetId: 99,
        });
        assert.equal(
            getCellValue(template, "A1"),
            "😃",
            "It should show the smiley as a smiley 😉"
        );
    });

    QUnit.test(
        "create and edit template and create new spreadsheet from it",
        async function (assert) {
            assert.expect(4);
            const templateModel = new Model();
            setCellContent(templateModel, "A1", "Firstname");
            setCellContent(templateModel, "B1", "Lastname");
            const id = 101;
            const serverData = getBasicServerData();
            serverData.models["spreadsheet.template"].records = [
                {
                    id,
                    name: "template",
                    data: jsonToBase64(templateModel.exportData()),
                },
            ];
            let spreadSheetComponent;
            patchWithCleanup(SpreadsheetTemplateAction.prototype, {
                setup() {
                    this._super();
                    onMounted(() => {
                        spreadSheetComponent = this.spreadsheet;
                    });
                },
            });
            const { model, webClient } = await createSpreadsheetTemplate({
                serverData,
                spreadsheetId: id,
                mockRPC: function (route, args) {
                    if (args.model == "spreadsheet.template") {
                        if (args.method === "write") {
                            const model = base64ToJson(args.args[1].data);
                            assert.strictEqual(
                                typeof model,
                                "object",
                                "Model type should be object"
                            );
                            const { A1, B1 } = model.sheets[0].cells;
                            assert.equal(
                                `${A1.content} ${B1.content}`,
                                `Firstname Name`,
                                "A1 and B1 should be changed after update"
                            );
                        }
                    }
                },
            });

            setCellContent(model, "B1", "Name");
            await spreadSheetComponent.props.onSpreadsheetSaved(spreadSheetComponent.getSaveData());
            await doAction(webClient, {
                type: "ir.actions.client",
                tag: "action_open_template",
                params: { active_id: id },
            });
        }
    );
});
