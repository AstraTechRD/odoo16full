odoo.define('web_studio.NewModeltests', function (require) {
"use strict";

const NewModel = require('web_studio.NewModel');
const testUtils = require('web.test_utils');

QUnit.module('Studio', function () {

    QUnit.module('NewModel');

    QUnit.test('Add New Model', async function (assert) {
        assert.expect(7);

        const $target = $('#qunit-fixture');

        const newModel = new NewModel.NewModelItem();
        await newModel.appendTo($target);

        testUtils.mock.addMockEnvironment(newModel, {
            mockRPC: function (route, args) {
                if (route === "/web_studio/create_new_menu") {
                    assert.strictEqual(args.menu_name, "ABCD", "Model name should be ABCD.")
                    return Promise.resolve();
                }
                return this._super(route, args);
            },
        });

        assert.containsNone($, '.o_web_studio_new_model_modal',
            "there should not be any modal in the dom");
        assert.containsOnce(newModel, '.o_web_create_new_model',
            "there should be an add new model link");

        await testUtils.dom.click($('.o_web_create_new_model'));
        assert.containsOnce($, '.o_web_studio_new_model_modal',
            "there should be a modal in the dom");
        const $modal = $('.modal');
        assert.containsOnce($modal, 'input[name="name"]',
            "there should be an input for the name in the dialog");

        await testUtils.fields.editInput($modal.find('input[name="name"]'), "ABCD");
        await testUtils.dom.click($modal.find('.btn-primary'));
        const $configuratorModal = $('.o_web_studio_model_configurator');
        assert.containsOnce($configuratorModal, 'input[name="use_partner"]',
            "the ModelConfigurator should show the available model options");

        await testUtils.dom.click($configuratorModal.find('.o_web_studio_model_configurator_next'));
        assert.containsNone($, '.o_web_studio_model_configurator',
            "the ModelConfigurator should be gone");

        newModel.destroy();
    });
});
});
