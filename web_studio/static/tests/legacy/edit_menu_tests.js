odoo.define('web_studio.EditMenu_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
const { prepareWowlFormViewDialogs } = require("@web/../tests/views/helpers");

var EditMenu = require('web_studio.EditMenu');

QUnit.module('Studio', {
    beforeEach: function () {
        this.data = {
            'ir.ui.menu': {
                fields: {},
                records: [{
                    id: 1,
                    name: 'Menu 1',
                }, {
                    id: 2,
                    name: 'Menu 2',
                }, {
                    id: 21,
                    name: 'Submenu 1',
                }, {
                    id: 22,
                    name: 'Submenu 2',
                }]
            }
        };
        this.menu_data = {
            childrenTree: [
                {
                    id: 1,
                    name: 'Menu 1',
                    parent_id: false,
                    childrenTree: [],
                }, {
                    id: 2,
                    name: 'Menu 2',
                    parent_id: false,
                    childrenTree: [
                        {
                            childrenTree: [],
                            id: 21,
                            name: 'Submenu 1',
                            parent_id: 2,

                        }, {
                            childrenTree: [],
                            id: 21,
                            name: 'Submenu 2',
                            parent_id: 2,
                        },
                    ],
                },
            ],
        };
        this.archs = {
          'ir.ui.menu,false,form':
                '<form>'+
                    '<sheet>' +
                        '<field name="name"/>' +
                    '</sheet>' +
                '</form>'
        };
    }
}, function () {

    QUnit.module('EditMenu');

    QUnit.test('edit menu behavior', async function(assert) {
        assert.expect(3);

        var $target = $('#qunit-fixture');

        var edit_menu = new EditMenu.MenuItem(null, this.menu_data, 2);
        await edit_menu.appendTo($target);

        await testUtils.mock.addMockEnvironment(edit_menu, {
            data: this.data,
            archs: this.archs,
        });
        assert.strictEqual($('.o_web_studio_edit_menu_modal').length, 0,
            "there should not be any modal in the dom");
        assert.containsOnce(edit_menu, '.o_web_edit_menu',
            "there should be an edit menu link");

        // open the dialog to edit the menu
        await testUtils.dom.click(edit_menu.$('.o_web_edit_menu'));
        assert.strictEqual($('.o_web_studio_edit_menu_modal').length, 1,
            "there should be a modal in the dom");

        edit_menu.destroy();
    });

    QUnit.test('edit menu dialog', async function(assert) {
        assert.expect(23);

        const dialog = new EditMenu.Dialog(null, this.menu_data, 2);
        dialog.open();
        await dialog.opened();

        let customizeCalls = 0;

        await testUtils.mock.addMockEnvironment(dialog, {
            data: this.data,
            archs: this.archs,
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/ir.ui.menu/customize") {
                    if (customizeCalls === 0) {
                        assert.deepEqual(args.kwargs, {
                            to_delete: [],
                            to_move: {
                                2: { sequence: 1 },
                                21: { parent_menu_id: 2, sequence: 0 },
                            },
                        });
                    }
                    customizeCalls++;
                    return Promise.reject();
                }
                return this._super(route, args);
            },
        });

        await prepareWowlFormViewDialogs({ models: this.data, views: this.archs });

        const $modal = $('.modal');
        assert.containsOnce(dialog, 'ul.oe_menu_editor',
            "there should be the list of menus");
        assert.containsOnce(dialog, 'ul.oe_menu_editor > li',
            "there should be only one main menu");
        assert.strictEqual(dialog.$('ul.oe_menu_editor > li').data('menu-id'), 2,
            "the main menu should have the menu-id 2");
        assert.containsOnce(dialog, 'ul.oe_menu_editor > li > div button.js_edit_menu',
            "there should be a button to edit the menu");
        assert.containsOnce(dialog, 'ul.oe_menu_editor > li > div button.js_delete_menu',
            "there should be a button to remove the menu");
        assert.containsN(dialog, 'ul.oe_menu_editor > li > ul > li', 2,
            "there should be two submenus");
        assert.containsOnce($modal, '.js_add_menu',
            "there should be a link to add new menu");

        // open the dialog to create a new menu
        await testUtils.dom.click($modal.find('.js_add_menu'));
        await testUtils.nextTick();
        assert.strictEqual($('.o_web_studio_add_menu_modal').length, 1,
            "there should be a modal in the dom");
        assert.strictEqual($('.o_web_studio_add_menu_modal input[name="name"]').length, 1,
            "there should be an input for the name in the dialog");
        await testUtils.dom.click($('.o_web_studio_add_menu_modal .o_field_widget[name="model_choice"] [data-value="new"]'));
        assert.isNotVisible($('.o_web_studio_add_menu_modal .o_field_many2one'),
            "there should be no visible many2one for the model in the dialog");
        // Define a name for new model
        $('input[name="name"]').val("new_model");
        await testUtils.dom.click($('.o_web_studio_add_menu_modal .btn-primary'));
        assert.containsOnce($, '.o_web_studio_model_configurator input[name="use_partner"]',
            "the ModelConfigurator should show the available model options");
        await testUtils.dom.click($('.o_web_studio_model_configurator .o_web_studio_model_configurator_previous'));
        assert.containsNone($, '.o_web_studio_model_configurator',
            "the ModelConfigurator should be gone");
        await testUtils.dom.click($('.o_web_studio_add_menu_modal .o_field_widget[name="model_choice"] [data-value="existing"]'));
        assert.strictEqual($('.o_web_studio_add_menu_modal .o_field_many2one').filter(':visible').length, 1,
            "there should be a visible many2one for the model in the dialog");

        // add menu and close the modal
        await testUtils.fields.editInput($('.o_web_studio_add_menu_modal input[name="name"]'), "AA");
        await testUtils.dom.click($('.o_web_studio_add_menu_modal .btn-primary'));
        await testUtils.dom.click($('.o_web_studio_add_menu_modal .btn-secondary'));

        // move submenu above root menu
        await testUtils.dom.dragAndDrop(dialog.$('li li .input-group:first'), dialog.$('.input-group:first'));
        assert.strictEqual(dialog.to_move[2].sequence, dialog.to_move[21].sequence + 1,
            "Root menu is after moved submenu");

        // open the dialog to edit the menu
        await testUtils.dom.click(dialog.$('.js_edit_menu:nth(1)'));
        assert.strictEqual($('.o_dialog .o_form_view').length, 1,
            "there should be a form view dialog in the dom");
        assert.strictEqual($('.o_dialog .o_form_view .o_field_widget[name="name"] input').val(), "Menu 2",
            "the edited menu should be menu 2");
        // confirm the edition
        assert.strictEqual(customizeCalls, 0, "current changes have not been saved");
        await testUtils.dom.click($('.o_dialog .o_form_button_save'));
        assert.strictEqual(customizeCalls, 1, "current changes are saved after editing a menu");

        // delete the last menu
        await testUtils.dom.click(dialog.$('.js_delete_menu:nth(2)'));
        assert.containsNone(dialog, 'ul.oe_menu_editor > li > ul > li',
            "there should be no submenu after deletion");
        assert.strictEqual(dialog.to_delete.length, 1,
            "there should be one menu to delete");

        await testUtils.dom.click(dialog.$('.js_delete_menu:first'));
        await testUtils.dom.click(dialog.$('.js_delete_menu:first'));
        await testUtils.dom.click($modal.find('footer .btn-primary'));
        assert.containsN($(document), '.modal', 2,
            "should have 2 dialogs");
        assert.strictEqual($('.modal:not(.o_inactive_modal) .modal-title').text(), "Alert",
            "should have alert dialog if we delete all menus");

        dialog.destroy();
    });
});
});
