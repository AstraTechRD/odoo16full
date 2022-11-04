/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { userService } from "@web/core/user_service";
import { PhoneField } from "@web/views/fields/phone/phone_field";

import DialingPanel from "voip.DialingPanel";
import { voipService } from "@voip/voip_service";

import { start, startServer } from "@mail/../tests/helpers/test_utils";

import { click, clickSave, editInput, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module('voip', (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
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
            },
        };
        setupViewRegistries();
    });

    QUnit.module('PhoneField');

    QUnit.test('PhoneField in readonly form view on normal screens', async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form edit="0">
                    <sheet>
                        <group>
                            <field name="foo" widget="phone"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_field_phone a.o_form_uri");
        assert.strictEqual(target.querySelector(".o_field_phone a").textContent, "yop");
        assert.hasAttrValue(target.querySelector(".o_field_phone a"), "href", "tel:yop");
    });

    QUnit.test('PhoneField in form view on normal screens', async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" widget="phone"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, 'input[type="tel"]');
        assert.strictEqual(target.querySelector('input[type="tel"]').value, "yop");

        // change value in edit mode
        await editInput(target, "input[type='tel']", "new");

        // save
        await clickSave(target);
        assert.strictEqual(target.querySelector("input[type='tel']").value, "new");
    });

    QUnit.test('phone field in editable list view on normal screens', async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `<tree editable="bottom"><field name="foo" widget="phone"/></tree>`,
        });

        assert.containsN(target, 'tbody td:not(.o_list_record_selector)', 5);
        assert.strictEqual(target.querySelector('tbody td:not(.o_list_record_selector)').innerText, 'yop\nSMS');
        assert.containsN(target, 'div.o_field_phone.o_field_widget a.o_form_uri', 5);
        assert.hasAttrValue(target.querySelector("a"), 'href', 'tel:yop');

        // Edit a line and check the result
        await click(target.querySelector(".o_data_cell"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        assert.strictEqual(target.querySelector(".o_data_cell input").value, "yop");
        await editInput(target, ".o_data_cell input", "new");

        // save
        await click(target.querySelector(".o_list_button_save"));
        assert.containsNone(target, ".o_selected_row");
        assert.strictEqual(target.querySelector('tbody td:not(.o_list_record_selector)').innerText, 'new\nSMS');
        assert.containsN(target, 'div.o_field_phone.o_field_widget a.o_form_uri', 5);
        assert.hasAttrValue(target.querySelector("a"), 'href', 'tel:new');
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

        registry.category("services").add("voip", voipService);
        registry.category("services").remove("user");
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

        await openView({
            res_id: resPartnerId1,
            res_model: 'res.partner',
            views: [[false, 'form']],
        });

        await click(document.querySelector('.o_field_phone a'));
        assert.containsOnce(document.body, ".o_form_readonly", "form view should not change to edit mode from click on phone link");
        assert.verifySteps([
            "hasGroup: base.group_user",
            "call made"
        ], "should have called click handler of phone link only once");
    });
});
