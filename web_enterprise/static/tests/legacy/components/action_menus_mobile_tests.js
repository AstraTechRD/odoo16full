odoo.define('web.action_menus_mobile_tests', function (require) {
    "use strict";

    const ActionMenus = require('web.ActionMenus');
    const Registry = require('web.Registry');
    const testUtils = require('web.test_utils');

    const { createComponent } = testUtils;

    QUnit.module('Components', {
        beforeEach() {
            this.action = {
                res_model: 'hobbit',
            };
            this.view = {
                type: 'form',
            };
            this.props = {
                activeIds: [23],
                context: {},
                items: {
                    action: [
                        { action: { id: 1 }, name: "What's taters, precious ?", id: 1 },
                    ],
                    print: [
                        { action: { id: 2 }, name: "Po-ta-toes", id: 2 },
                    ],
                },
            };
            // Patch the registry of the action menus
            this.actionMenusRegistry = ActionMenus.registry;
            ActionMenus.registry = new Registry();
        },
        afterEach() {
            ActionMenus.registry = this.actionMenusRegistry;
        },
    }, function () {

        QUnit.module('ActionMenus');

        QUnit.test('Auto close the print dropdown after click inside an item', async function (assert) {
            assert.expect(6);

            const actionMenus = await createComponent(ActionMenus, {
                env: {
                    device: {
                        isMobile: true
                    },
                    action: this.action,
                    view: this.view,
                },
                intercepts: {
                    'do-action': ev => assert.step('do-action'),
                },
                props: this.props,
                async mockRPC(route, args) {
                    switch (route) {
                        case '/web/action/load':
                            const expectedContext = {
                                active_id: 23,
                                active_ids: [23],
                                active_model: 'hobbit',
                            };
                            assert.deepEqual(args.context, expectedContext);
                            assert.step('load-action');
                            return {context: {}, flags: {}};
                        default:
                            return this._super(...arguments);

                    }
                },
            });
            await testUtils.controlPanel.toggleActionMenu(actionMenus, "Print");
            assert.containsOnce(actionMenus.el, '.dropdown-menu-start',
                "should display the dropdown menu");
            await testUtils.controlPanel.toggleMenuItem(actionMenus, "Po-ta-toes");
            assert.containsNone(actionMenus.el, '.dropdown-menu-start',
                "should not display the dropdown menu");
            assert.verifySteps(['load-action', 'do-action']);
        });
    });
});
