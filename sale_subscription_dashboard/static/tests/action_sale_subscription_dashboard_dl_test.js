/** @odoo-module */
import { mockDownload } from "@web/../tests/helpers/utils";
import { createWebClient, getActionManagerServerData, doAction } from "@web/../tests/webclient/helpers";

let serverData;
QUnit.module("Sale Subscription Dashboard Download Reports", {
    beforeEach: function () {
        serverData = getActionManagerServerData();
    },
}, function () {
    QUnit.test("can execute sale subscription dashboard report download actions", async function (assert) {
        assert.expect(5);
        serverData.actions[1] = {
            id: 1,
            data: {
                model: "sale.order",
                output_format: "pdf",
            },
            type: 'ir_actions_sale_subscription_dashboard_download',
        };
        mockDownload((params) => {
            assert.step(params.url);
            assert.deepEqual(params.data, {
                model: 'sale.order',
                output_format: 'pdf',
            }, "should give the correct data");
            return Promise.resolve();
        });
        const webClient = await createWebClient({
            serverData,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
            },
        });
        await doAction(webClient, 1);

        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/salesman_subscription_reports",
        ]);
    });
});
