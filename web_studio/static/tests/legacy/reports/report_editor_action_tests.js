odoo.define('web_studio.ReportEditorAction_tests', function (require) {
    "use strict";

    const { controlPanel } = require('web.test_utils');
    const { getPagerValue, pagerNext } = controlPanel;

    const { getFixture } = require("@web/../tests/helpers/utils");
    const { doAction } = require("@web/../tests/webclient/helpers");
    const { openStudio, registerStudioDependencies,getReportServerData } = require("@web_studio/../tests/helpers");
    const { createEnterpriseWebClient } = require("@web_enterprise/../tests/helpers");

    let serverData;
    let target;
    QUnit.module('Studio', {
        beforeEach: function () {
            this.data = {
                foo: {
                    fields: {},
                    records: [{ id: 22 }, { id: 23 }],
                },
                "ir.actions.report": {
                    fields: { model: { type: "char" }, report_name: { type: "char" }, report_type:{ type: "char" }},
                    records: [{ id: 11, model: "foo", report_name: "foo_report", report_type: "pdf" }],
                },
                "ir.model": {
                    fields: {},
                },
            };
            const reportServerData = getReportServerData();
            const actions = {
                1: {
                    id: 1,
                    xml_id: "kikou.action",
                    name: 'Kikou Action',
                    res_model: 'foo',
                    type: 'ir.actions.act_window',
                    view_mode: 'list,form',
                    views: [[1, 'form']],
                }
            };
            const views = Object.assign({
                "foo,2,form": `<form><field name="display_name" /></form>`,
                "foo,false,search": `<search />`,
            }, reportServerData.views);
            serverData = {actions, models: this.data, views};
            Object.assign(serverData.models, reportServerData.models);
            registerStudioDependencies();
            target = getFixture();
        },
    }, function () {
        QUnit.module('ReportEditorAction');

        QUnit.test('use pager', async function (assert) {
            assert.expect(2);

            const reportHTML = `
                <html>
                    <head/>
                    <body>
                        <div id="wrapwrap">
                            <main>
                                <div class="page"/>
                            </main>
                        </div>
                    </body>
                </html>`;

            const mockRPC = (route, args) => {
                switch (route) {
                    case "/web_studio/get_report_views":
                        return { report_html: reportHTML };
                    case "/web_studio/get_widgets_available_options":
                    case "/web_studio/read_paperformat":
                        return {};
                }
            };

            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            await doAction(webClient, 1);
            await openStudio(target, {report: 11});

            assert.strictEqual(getPagerValue(target), "1");
            await pagerNext(target);
            assert.strictEqual(getPagerValue(target), "2");
        });
    });
});
