odoo.define('account_reports/static/tests/account_reports_tests', function (require) {
    "use strict";

    const LegacyControlPanel = require('web.ControlPanel');
    const { ControlPanel } = require("@web/search/control_panel/control_panel");
    const testUtils = require("web.test_utils");
    const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');
    const { legacyExtraNextTick, getFixture, patchWithCleanup, destroy } = require("@web/../tests/helpers/utils");

    const { dom } = testUtils;
    const { onMounted, onWillUnmount } = owl;

    let target = getFixture();
    QUnit.module('Account Reports', {
        beforeEach: function () {
            this.models = {
                partner: {
                    fields: {
                        display_name: {string: "Displayed name", type: "char"},
                    },
                    records: [
                        {id: 1, display_name: "Genda Swami"},
                    ],
                }
            };
            this.views = {
                'partner,false,form': '<form><field name="display_name"/></form>',
                'partner,false,search': '<search></search>',
            };
            this.actions = {
                42: {
                    id: 42,
                    name: "Account reports",
                    tag: 'account_report',
                    type: 'ir.actions.client',
                    params: {
                        options: {
                            buttons: [],
                            search_bar: false,
                        }
                    }
                }
            };
            this.mockRPC = function (route) {
                if (route === '/web/dataset/call_kw/account.report/get_report_informations') {
                    return Promise.resolve({
                        options: {
                            buttons: [],
                            search_bar: false,
                        },
                        main_html: '<a action="go_to_details">Go to detail view</a>',
                    });
                } else if (route === '/web/dataset/call_kw/account.report/dispatch_report_action') {
                    return Promise.resolve({
                        type: "ir.actions.act_window",
                        res_id: 1,
                        res_model: "partner",
                        views: [
                            [false, "form"],
                        ],
                    });
                } else if (route === '/web/dataset/call_kw/account.report/get_html_footnotes') {
                    return Promise.resolve("");
                }
            }
            target = getFixture();
        }
    }, () => {
        QUnit.test("mounted is called once when returning on 'Account Reports' from breadcrumb", async function(assert) {
            // This test can be removed as soon as we don't mix legacy and owl layers anymore.
            assert.expect(7);

            let mountCount = 0;
            patchWithCleanup(ControlPanel.prototype, {
                setup() {
                    this._super();
                    onMounted(() => {
                        mountCount = mountCount + 1;
                        this.__uniqueId = mountCount;
                        assert.step(`mounted ${this.__uniqueId}`);
                    });
                    onWillUnmount(() => {
                        assert.step(`willUnmount ${this.__uniqueId}`);
                    });
                },
            });
            patchWithCleanup(LegacyControlPanel.prototype, {
                setup() {
                    this._super();
                    onMounted(() => {
                        mountCount = mountCount + 1;
                        this.__uniqueId = mountCount;
                        assert.step(`mounted ${this.__uniqueId} (legacy)`);
                    });

                    onWillUnmount(() => {
                        assert.step(`willUnmount ${this.__uniqueId} (legacy)`);
                    });
                }
            });

            const serverData = {models: this.models, views: this.views, actions: this.actions};
            const webClient = await createWebClient({
                serverData,
                mockRPC: this.mockRPC,
            });

            await doAction(webClient, 42);
            await dom.click($(target).find('a[action="go_to_details"]'));
            await legacyExtraNextTick();
            await dom.click($(target).find('.breadcrumb-item:first'));
            await legacyExtraNextTick();
            destroy(webClient);

            assert.verifySteps([
                'mounted 1 (legacy)',
                'willUnmount 1 (legacy)',
                'mounted 2',
                'willUnmount 2',
                'mounted 3 (legacy)',
                'willUnmount 3 (legacy)',
            ]);
        });

        QUnit.test("recomputeHeader is unregistered when leaving the 'Account Reports' view", async function (assert) {
            assert.expect(1);

            const serverData = {models: this.models, views: this.views, actions: this.actions};
            const webClient = await createWebClient({
                serverData,
                mockRPC: this.mockRPC,
            });

            await doAction(webClient, 42);
            await dom.click($(target).find('a[action="go_to_details"]'));
            await legacyExtraNextTick();
            $(window).trigger('resize');
            assert.ok(true);
        });
    });

});
