odoo.define('web.control_panel_mobile_tests', function (require) {
    "use strict";

    const FormView = require('web.FormView');
    const testUtils = require('web.test_utils');

    const cpHelpers = require('@web/../tests/search/helpers');
    const { browser } = require("@web/core/browser/browser");
    const { patchWithCleanup, getFixture } = require("@web/../tests/helpers/utils");
    const { createControlPanel, createView } = testUtils;

    const { createWebClient, doAction, getActionManagerServerData } = require('@web/../tests/webclient/helpers');

    let serverData;
    let target;

    QUnit.module('Control Panel', {
        beforeEach: function () {
            target = getFixture();
            this.actions = [{
                id: 1,
                name: "Yes",
                res_model: 'partner',
                type: 'ir.actions.act_window',
                views: [[false, 'list']],
            }];
            this.archs = {
                'partner,false,list': '<tree><field name="foo"/></tree>',
                'partner,false,search': `
                    <search>
                        <filter string="Active" name="my_projects" domain="[('boolean_field', '=', True)]"/>
                        <field name="foo" string="Foo"/>
                    </search>`,
            };
            this.data = {
                partner: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        boolean_field: { string: "I am a boolean", type: "boolean" },
                    },
                    records: [
                        { id: 1, display_name: "First record", foo: "yop" },
                    ],
                },
            };
            const actions = {};
            this.actions.forEach((act) => {
                actions[act.xml_id || act.id] = act;
            });
            serverData = getActionManagerServerData();
            Object.assign(serverData, { models: this.data, views: this.archs, actions });
            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
                clearTimeout: () => {},
            });
        },
    }, function () {

        QUnit.test('basic rendering', async function (assert) {
            assert.expect(2);

            const webClient = await createWebClient({serverData});

            await doAction(webClient, 1);

            assert.containsNone(target, '.o_control_panel .o_mobile_search',
                "search options are hidden by default");
            assert.containsOnce(target, '.o_control_panel .o_enable_searchview',
                "should display a button to toggle the searchview");
        });

        QUnit.test("control panel appears at top on scroll event", async function (assert) {
            assert.expect(12);

            const MAX_HEIGHT = 800;
            const MIDDLE_HEIGHT = 400;
            const DELTA_TEST = 20;

            const form = await createView({
                View: FormView,
                arch:
                    '<form>' +
                        '<sheet>' +
                            `<div style="height: ${2 * MAX_HEIGHT}px"></div>` +
                        '</sheet>' +
                    '</form>',
                data: this.data,
                model: 'partner',
                res_id: 1,
            });

            const controlPanelEl = document.querySelector('.o_control_panel');
            const controlPanelHeight = controlPanelEl.offsetHeight;

            // Force container to have a scrollbar
            controlPanelEl.parentElement.style.maxHeight = `${MAX_HEIGHT}px`;

            const scrollAndAssert = async (targetHeight, expectedTopValue, hasStickyClass) => {
                if (targetHeight !== null) {
                    controlPanelEl.parentElement.scrollTo(0, targetHeight);
                    await testUtils.nextTick();
                }
                const expectedPixelValue = `${expectedTopValue}px`;
                assert.strictEqual(controlPanelEl.style.top, expectedPixelValue,
                    `Top must be ${expectedPixelValue} (after scroll to ${targetHeight})`);

                if (hasStickyClass) {
                    assert.hasClass(controlPanelEl, 'o_mobile_sticky');
                } else {
                    assert.doesNotHaveClass(controlPanelEl, 'o_mobile_sticky');
                }
            }

            // Initial position (scrollTop: 0)
            await scrollAndAssert(null, 0, false);

            // Scroll down 800px (scrollTop: 800)
            await scrollAndAssert(MAX_HEIGHT, -controlPanelHeight, true);

            // Scoll up 20px (scrollTop: 780)
            await scrollAndAssert(MAX_HEIGHT - DELTA_TEST, -controlPanelHeight + DELTA_TEST, true);

            // Scroll up 380px (scrollTop: 400)
            await scrollAndAssert(MIDDLE_HEIGHT, 0, true);

            // Scroll down 200px (scrollTop: 800)
            await scrollAndAssert(MAX_HEIGHT, -controlPanelHeight, true);

            // Scroll up 400px (scrollTop: 0)
            await scrollAndAssert(0, -controlPanelHeight, false);

            form.destroy();
        });

        QUnit.test("mobile search: basic display", async function (assert) {
            assert.expect(4);

            const fields = {
                birthday: { string: "Birthday", type: "date", store: true, sortable: true },
            };
            const searchMenuTypes = ["filter", "groupBy", "comparison", "favorite"];
            const params = {
                cpModelConfig: {
                    arch: `
                        <search>
                            <filter name="birthday" date="birthday"/>
                        </search>`,
                    fields,
                    searchMenuTypes,
                },
                cpProps: { fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            // Toggle search bar controls
            await testUtils.dom.click(controlPanel.el.querySelector("button.o_enable_searchview"));
            // Open search view
            await testUtils.dom.click(controlPanel.el.querySelector("button.o_toggle_searchview_full"));

            // Toggle filter date
            // Note: 'document.body' is used instead of 'controlPanel' because the
            // search view is directly in the body.
            await cpHelpers.toggleFilterMenu(document);
            await cpHelpers.toggleMenuItem(document, "Birthday");
            await cpHelpers.toggleMenuItemOption(document, "Birthday", 0);

            assert.containsOnce(document.body, ".o_filter_menu");
            assert.containsOnce(document.body, ".o_group_by_menu");
            assert.containsOnce(document.body, ".o_comparison_menu");
            assert.containsOnce(document.body, ".o_favorite_menu");
        });

        QUnit.test('mobile search: activate a filter through quick search', async function (assert) {
            assert.expect(7);

            let searchRPCFlag = false;

            const mockRPC = (route, args) => {
                if (searchRPCFlag && args.method === "web_search_read") {
                    assert.deepEqual(args.kwargs.domain, [['foo', 'ilike', 'A']],
                        "domain should have been properly transferred to list view");
                }
            };

            const webClient = await createWebClient({serverData, mockRPC});

            await doAction(webClient, 1);

            assert.containsOnce(document.body, 'button.o_enable_searchview.oi-search',
                "should display a button to open the searchview");
            assert.containsNone(document.body, '.o_searchview_input_container',
                "Quick search input should be hidden");

            // open the search view
            await testUtils.dom.click(document.querySelector('button.o_enable_searchview'));

            assert.containsOnce(document.body, '.o_toggle_searchview_full',
                "should display a button to expand the searchview");
            assert.containsOnce(document.body, '.o_searchview_input_container',
                "Quick search input should now be visible");

            searchRPCFlag = true;

            // use quick search input (search view is directly put in the body)
            await cpHelpers.editSearch(document.body, "A");
            await cpHelpers.validateSearch(document.body);

            // close quick search
            await testUtils.dom.click(document.querySelector('button.o_enable_searchview.fa-arrow-left'));

            assert.containsNone(document.body, '.o_toggle_searchview_full',
                "Expand icon shoud be hidden");
            assert.containsNone(document.body, '.o_searchview_input_container',
                "Quick search input should be hidden");
        });

        QUnit.test('mobile search: activate a filter in full screen search view', async function (assert) {
            assert.expect(3);

            const webClient = await createWebClient({ serverData });

            await doAction(webClient, 1);

            assert.containsNone(document.body, '.o_mobile_search');

            // open the search view
            await testUtils.dom.click(target.querySelector('button.o_enable_searchview'));
            // open it in full screen
            await testUtils.dom.click(target.querySelector('.o_toggle_searchview_full'));

            assert.containsOnce(document.body, '.o_mobile_search');

            await cpHelpers.toggleFilterMenu(document.body);
            await cpHelpers.toggleMenuItem(document.body, "Active");

            // closing search view
            await testUtils.dom.click(
                [...document.querySelectorAll('.o_mobile_search_button')].find(
                    e => e.innerText.trim() === "FILTER"
                )
            );
            assert.containsNone(document.body, '.o_mobile_search');
        });
    });
});
