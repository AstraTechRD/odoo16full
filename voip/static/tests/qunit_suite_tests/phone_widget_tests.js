odoo.define('voip.tests', function (require) {
"use strict";

const { start, startServer } = require('@mail/../tests/helpers/test_utils');

const { registry } = require("@web/core/registry");
const { voipService } = require("@voip/voip_service");
const { userService } = require("@web/core/user_service");
const { browser } = require("@web/core/browser/browser");
const DialingPanel = require("voip.DialingPanel");
const { PhoneField } = require("@web/views/fields/phone/phone_field");

var config = require('web.config');
var FormView = require('web.FormView');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

const { nextTick } = require("@web/../tests/helpers/utils");
const { patchWithCleanup } = require("@web/../tests/helpers/utils");

var createView = testUtils.createView;

QUnit.module('voip', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char", default: "My little Foo Value", searchable: true},
                },
                records: [
                    {id: 1, foo: "yop"},
                    {id: 2, foo: "blip"},
                    {id: 4, foo: "abc"},
                    {id: 3, foo: "gnap"},
                    {id: 5, foo: "blop"},
                ],
            },
        };
    },
}, function () {

    QUnit.module('PhoneWidget');

    QUnit.test('phone field in form view on normal screens', async function (assert) {
        assert.expect(7);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" widget="phone"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            config: {
                device: {
                    size_class: config.device.SIZES.MD,
                }
            },
        });

        var $phoneLink = form.$('div.o_form_uri.o_field_phone.o_field_widget > a');
        assert.strictEqual($phoneLink.length, 1,
            "should have a anchor with correct classes");
        assert.strictEqual($phoneLink.text(), 'yop',
            "value should be displayed properly");
        assert.hasAttrValue($phoneLink, 'href', 'tel:yop',
            "should have proper tel prefix");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, 'input[type="text"].o_field_widget',
            "should have an input for the phone field");
        assert.strictEqual(form.$('input[type="text"].o_field_widget').val(), 'yop',
            "input should contain field value in edit mode");

        // change value in edit mode
        await testUtils.fields.editInput(form.$('input[type="text"].o_field_widget'), 'new');

        // save
        await testUtils.form.clickSave(form);
        $phoneLink = form.$('div.o_form_uri.o_field_phone.o_field_widget > a');
        assert.strictEqual($phoneLink.text(), 'new',
            "new value should be displayed properly");
        assert.hasAttrValue($phoneLink, 'href', 'tel:new',
            "should still have proper tel prefix");

        form.destroy();
    });

    QUnit.test('phone field in editable list view on normal screens', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"  widget="phone"/></tree>',
            config: {
                device: {
                    size_class: config.device.SIZES.MD,
                }
            },
        });

        assert.containsN(list, 'tbody td:not(.o_list_record_selector)', 5,
            "should have 5 cells");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'yopSMS',
            "value should be displayed properly");

        var $phoneLink = list.$('div.o_form_uri.o_field_phone.o_field_widget > a');
        assert.strictEqual($phoneLink.length, 5,
            "should have anchors with correct classes");
        assert.hasAttrValue($phoneLink.first(), 'href', 'tel:yop',
            "should have proper tel prefix");

        // Edit a line and check the result
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($cell);
        assert.hasClass($cell.parent(),'o_selected_row', 'should be set as edit mode');
        assert.strictEqual($cell.find('input').val(), 'yop',
            'should have the corect value in internal input');
        await testUtils.fields.editInput($cell.find('input'), 'new');

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        assert.doesNotHaveClass($cell.parent(), 'o_selected_row', 'should not be in edit mode anymore');
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'newSMS',
            "value should be properly updated");
        $phoneLink = list.$('div.o_form_uri.o_field_phone.o_field_widget > a');
        assert.strictEqual($phoneLink.length, 5,
            "should still have anchors with correct classes");
        assert.hasAttrValue($phoneLink.first(), 'href', 'tel:new',
            "should still have proper tel prefix");

        list.destroy();
    });

    QUnit.test("click on phone field link triggers call once", async function (assert) {
        assert.expect(5);

        const customUserService = {
            async start() {
                const user = await userService.start(...arguments);
                const hasGroup = (group) => {
                    assert.step(`hasGroup: ${group}`);
                    return true;
                }
                return Object.assign(user, { hasGroup });
            }
        }

        patchWithCleanup(browser, {
            navigator: {
                mediaDevices: {},
            }
        });

        patchWithCleanup(DialingPanel.prototype,  {
            callFromPhoneWidget() {
                assert.step("call made");
            }
        });

        patchWithCleanup(PhoneField.prototype, {
            onLinkClicked(ev) {
                this._super(...arguments);
                assert.ok(ev.defaultPrevented);
            }
        });

        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv['res.partner'].create({
            phone: "+324567606798",
        });

        const views = {
            'res.partner,false,form': `
                <form string="Partners" edit="0">
                    <sheet>
                        <group>
                            <field name="phone" widget="phone"/>
                        </group>
                    </sheet>
                </form>
            `,
        };

        const { openView } = await start({
            services: {
                user: customUserService,
            },
            mockRPC(route, args) {
                if (args.method === "get_missed_call_info") {
                    return {};
                }
            },
            serverData: { views },
        });

        registry.category("services").add("voip", voipService);
        await nextTick();

        await openView({
            res_id: resPartnerId1,
            res_model: 'res.partner',
            views: [[false, 'form']],
        });

        await testUtils.dom.click(document.querySelector('.o_field_phone a'));
        assert.containsOnce(document.body, ".o_form_readonly", "form view should not change to edit mode from click on phone link");
        assert.verifySteps([
            "hasGroup: base.group_user",
            "call made"
        ], "should have called click handler of phone link only once");
    });

});
});
