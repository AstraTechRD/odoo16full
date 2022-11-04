/** @odoo-module **/

import Dialog from "web.Dialog";
import dom from "web.dom";
import OwlDialog from "web.OwlDialog";
import Popover from "web.Popover";
import session from "web.session";
import makeTestEnvironment from "web.test_env";
import testUtils from "web.test_utils";
import Widget from "web.Widget";

import { useBackButton } from "web_mobile.hooks";
import { BackButtonEventMixin } from "web_mobile.mixins";
import mobile from "web_mobile.core";
/*import UserPreferencesFormView from "web_mobile.UserPreferencesFormView";*/

import { createWebClient, doAction } from '@web/../tests/webclient/helpers';
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { mount, getFixture, destroy, patchWithCleanup, clickSave} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

const { Component, useState, xml } = owl;

const { createParent } = testUtils;

const MY_IMAGE =
    "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";
const BASE64_SVG_IMAGE =
    "PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHdpZHRoPScxNzUnIGhlaWdodD0nMTAwJyBmaWxsPScjMDAwJz48cG9seWdvbiBwb2ludHM9JzAsMCAxMDAsMCA1MCw1MCcvPjwvc3ZnPg==";
const BASE64_PNG_HEADER = "iVBORw0KGg";

let target;
let serverData;

QUnit.module("web_mobile", {
    async beforeEach() {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        name: { string: "name", type: "char" },
                        avatar_1920: {},
                        parent_id: { string: "Parent", type: "many2one", relation: "partner" },
                        sibling_ids: {
                            string: "Sibling",
                            type: "many2many",
                            relation: "partner",
                        },
                        phone: {},
                        mobile: {},
                        email: {},
                        street: {},
                        street2: {},
                        city: {},
                        state_id: {},
                        zip: {},
                        country_id: {},
                        website: {},
                        function: {},
                        title: {},
                        date: { string: "A date", type: "date" },
                        datetime: { string: "A datetime", type: "datetime" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "coucou1",
                        },
                        {
                            id: 2,
                            name: "coucou2",
                        },
                        {
                            id: 11,
                            name: "coucou3",
                            avatar_1920: "image",
                            parent_id: 1,
                            phone: "phone",
                            mobile: "mobile",
                            email: "email",
                            street: "street",
                            street2: "street2",
                            city: "city",
                            state_id: "state_id",
                            zip: "zip",
                            country_id: "country_id",
                            website: "website",
                            function: "function",
                            title: "title",
                        },
                    ],
                },
                users: {
                    fields: {
                        name: { string: "name", type: "char" },
                    },
                    records: [],
                },
            },
        };
        setupViewRegistries();
    },
}, function () {
    QUnit.module("core", function () {
        QUnit.test("BackButtonManager", async function (assert) {
            assert.expect(13);

            patchWithCleanup(mobile.methods, {
                overrideBackButton({ enabled }) {
                    assert.step(`overrideBackButton: ${enabled}`);
                },
            });

            const { BackButtonManager, BackButtonListenerError } = mobile;
            const manager = new BackButtonManager();
            const DummyWidget = Widget.extend({
                _onBackButton(ev) {
                    assert.step(`${ev.type} event`);
                },
            });
            const dummy = new DummyWidget();

            manager.addListener(dummy, dummy._onBackButton);
            assert.verifySteps(["overrideBackButton: true"]);

            // simulate 'backbutton' event triggered by the app
            await testUtils.dom.triggerEvent(document, "backbutton");
            assert.verifySteps(["backbutton event"]);

            manager.removeListener(dummy);
            assert.verifySteps(["overrideBackButton: false"]);
            await testUtils.dom.triggerEvent(document, "backbutton");
            assert.verifySteps([], "shouldn't trigger any handler");

            manager.addListener(dummy, dummy._onBackButton);
            assert.throws(
                () => {
                    manager.addListener(dummy, dummy._onBackButton);
                },
                BackButtonListenerError,
                "should raise an error if adding a listener twice"
            );
            assert.verifySteps(["overrideBackButton: true"]);

            manager.removeListener(dummy);
            assert.throws(
                () => {
                    manager.removeListener(dummy);
                },
                BackButtonListenerError,
                "should raise an error if removing a non-registered listener"
            );
            assert.verifySteps(["overrideBackButton: false"]);

            dummy.destroy();
        });
    });

    QUnit.module("BackButtonEventMixin");

    QUnit.test("widget should receive a backbutton event", async function (assert) {
        assert.expect(5);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        const DummyWidget = Widget.extend(BackButtonEventMixin, {
            _onBackButton(ev) {
                assert.step(`${ev.type} event`);
            },
        });
        const backButtonEvent = new Event("backbutton");
        const dummy = new DummyWidget();
        dummy.appendTo($("<div>"));

        // simulate 'backbutton' event triggered by the app
        document.dispatchEvent(backButtonEvent);
        // waiting nextTick to match testUtils.dom.triggerEvents() behavior
        await testUtils.nextTick();

        assert.verifySteps([], "shouldn't have register handle before attached to the DOM");

        dom.append($("qunit-fixture"), dummy.$el, {
            in_DOM: true,
            callbacks: [{ widget: dummy }],
        });

        // simulate 'backbutton' event triggered by the app
        document.dispatchEvent(backButtonEvent);
        await testUtils.nextTick();

        dom.detach([{ widget: dummy }]);

        assert.verifySteps(
            ["overrideBackButton: true", "backbutton event", "overrideBackButton: false"],
            "should have enabled/disabled the back-button override"
        );

        dummy.destroy();
    });

    QUnit.test("multiple widgets should receive backbutton events in the right order", async function (assert) {
        assert.expect(6);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        const DummyWidget = Widget.extend(BackButtonEventMixin, {
            init(parent, { name }) {
                this._super.apply(this, arguments);
                this.name = name;
            },
            _onBackButton(ev) {
                assert.step(`${this.name}: ${ev.type} event`);
                dom.detach([{ widget: this }]);
            },
        });
        const backButtonEvent = new Event("backbutton");
        const dummy1 = new DummyWidget(null, { name: "dummy1" });
        dom.append($("qunit-fixture"), dummy1.$el, {
            in_DOM: true,
            callbacks: [{ widget: dummy1 }],
        });

        const dummy2 = new DummyWidget(null, { name: "dummy2" });
        dom.append($("qunit-fixture"), dummy2.$el, {
            in_DOM: true,
            callbacks: [{ widget: dummy2 }],
        });

        const dummy3 = new DummyWidget(null, { name: "dummy3" });
        dom.append($("qunit-fixture"), dummy3.$el, {
            in_DOM: true,
            callbacks: [{ widget: dummy3 }],
        });

        // simulate 'backbutton' events triggered by the app
        document.dispatchEvent(backButtonEvent);
        // waiting nextTick to match testUtils.dom.triggerEvents() behavior
        await testUtils.nextTick();
        document.dispatchEvent(backButtonEvent);
        await testUtils.nextTick();
        document.dispatchEvent(backButtonEvent);
        await testUtils.nextTick();

        assert.verifySteps([
            "overrideBackButton: true",
            "dummy3: backbutton event",
            "dummy2: backbutton event",
            "dummy1: backbutton event",
            "overrideBackButton: false",
        ]);

        dummy1.destroy();
        dummy2.destroy();
        dummy3.destroy();
    });

    QUnit.module("useBackButton");

    QUnit.test("component should receive a backbutton event", async function (assert) {
        assert.expect(5);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        class DummyComponent extends Component {
            setup() {
                this._backButtonHandler = useBackButton(this._onBackButton);
            }

            _onBackButton(ev) {
                assert.step(`${ev.type} event`);
            }
        }
        DummyComponent.template = xml`<div/>`;
        
        const target = getFixture();
        const env = makeTestEnv();

        const dummy = await mount(DummyComponent, target, { env });

        // simulate 'backbutton' event triggered by the app
        await testUtils.dom.triggerEvent(document, "backbutton");
        assert.verifySteps(
            ["overrideBackButton: true", "backbutton event"],
            "should have enabled/disabled the back-button override"
        );

        destroy(dummy);
        assert.verifySteps(["overrideBackButton: false"]);
    });

    QUnit.test("multiple components should receive backbutton events in the right order", async function (assert) {
        assert.expect(6);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        class DummyComponent extends Component {
            setup() {
                this._backButtonHandler = useBackButton(this._onBackButton);
            }

            _onBackButton(ev) {
                assert.step(`${this.props.name}: ${ev.type} event`);
                // unmounting is not supported anymore
                // A real business case equivalent to this is to have a Parent component
                // doing a foreach on some reactive object which contains the list of dummy components
                // and calling a callback props.onBackButton right here that removes the element from the list
                destroy(this);
            }
        }
        DummyComponent.template = xml`<div/>`;

        const props1 = { name: "dummy1" };
        const props2 = { name: "dummy2" };
        const props3 = { name: "dummy3" };
        const target = getFixture();
        const env = makeTestEnv();

        await mount(DummyComponent, target, { props: props1, env });
        await mount(DummyComponent, target, { props: props2, env });
        await mount(DummyComponent, target, { props: props3, env });

        // simulate 'backbutton' events triggered by the app
        await testUtils.dom.triggerEvent(document, "backbutton");
        await testUtils.dom.triggerEvent(document, "backbutton");
        await testUtils.dom.triggerEvent(document, "backbutton");

        assert.verifySteps([
            "overrideBackButton: true",
            "dummy3: backbutton event",
            "dummy2: backbutton event",
            "dummy1: backbutton event",
            "overrideBackButton: false",
        ]);

    });

    QUnit.test("component should receive a backbutton event: custom activation", async function (assert) {
        assert.expect(10);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        class DummyComponent extends Component {
            setup() {
                this._backButtonHandler = useBackButton(
                    this._onBackButton,
                    this.shouldActivateBackButton.bind(this)
                );
                this.state = useState({
                    show: this.props.show,
                });
            }

            toggle() {
                this.state.show = !this.state.show;
            }

            shouldActivateBackButton() {
                return this.state.show;
            }

            _onBackButton(ev) {
                assert.step(`${ev.type} event`);
            }
        }
        DummyComponent.template = xml`<button class="dummy" t-esc="state.show" t-on-click="toggle"/>`;

        const target = getFixture();
        const env = makeTestEnv();

        const dummy = await mount(DummyComponent, target, { props: { show: false }, env });

        assert.verifySteps([], "shouldn't have enabled backbutton mount");
        await testUtils.dom.click(target.querySelector(".dummy"));
        // simulate 'backbutton' event triggered by the app
        await testUtils.dom.triggerEvent(document, "backbutton");
        await testUtils.dom.click(target.querySelector(".dummy"));
        assert.verifySteps(
            [
                "overrideBackButton: true",
                "backbutton event",
                "overrideBackButton: false",
            ],
            "should have enabled/disabled the back-button override"
        );
        destroy(dummy);

        // enabled at mount
        const dummy2 = await mount(DummyComponent, target, { props: { show: true }, env });
        assert.verifySteps(
            ["overrideBackButton: true"],
            "shouldn have enabled backbutton at mount"
        );
        // simulate 'backbutton' event triggered by the app
        await testUtils.dom.triggerEvent(document, "backbutton");
        destroy(dummy2);

        assert.verifySteps(
            ["backbutton event", "overrideBackButton: false"],
            "should have disabled the back-button override during unmount"
        );
    });

    QUnit.module("Dialog");

    QUnit.test("dialog is closable with backbutton event", async function (assert) {
        assert.expect(7);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        testUtils.mock.patch(Dialog, {
            close: function () {
                assert.step("close");
                return this._super.apply(this, arguments);
            },
        });

        const parent = await createParent({
            data: this.data,
            archs: {
                "partner,false,form": `
            <form>
                <sheet>
                    <field name="name"/>
                </sheet>
           </form>
        `,
            },
        });

        const backButtonEvent = new Event("backbutton");
        const dialog = new Dialog(parent, {
            res_model: "partner",
            res_id: 1,
        }).open();
        await dialog.opened().then(() => {
            assert.step("opened");
        });
        assert.containsOnce(document.body, ".modal", "should have a modal");

        // simulate 'backbutton' event triggered by the app waiting
        document.dispatchEvent(backButtonEvent);
        // nextTick to match testUtils.dom.triggerEvents() behavior
        await testUtils.nextTick();

        // The goal of this assert is to check that our event called the
        // opened/close methods on Dialog.
        assert.verifySteps(
            ["overrideBackButton: true", "opened", "close", "overrideBackButton: false"],
            "should have open/close dialog"
        );
        assert.containsNone(document.body, ".modal", "modal should be closed");

        parent.destroy();
    });

    QUnit.module("OwlDialog");

    QUnit.test("dialog is closable with backbutton event", async function (assert) {
        assert.expect(7);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        class Parent extends Component {
            setup() {
                this.state = useState({ display: true });
            }
            _onDialogClosed() {
                this.state.display = false;
                assert.step("dialog_closed");
            }
        }

        Parent.components = { OwlDialog };
        Parent.template = xml`
    <div>
        <OwlDialog
            t-if="state.display"
            onClosed="() => this._onDialogClosed()">
            Some content
        </OwlDialog>
    </div>`;

        const target = getFixture();
        const env = await makeTestEnvironment();

        await mount(Parent, target, { env });

        assert.containsOnce(document.body, ".o_dialog");
        assert.verifySteps(["overrideBackButton: true"]);
        // simulate 'backbutton' event triggered by the app
        await testUtils.dom.triggerEvent(document, "backbutton");
        assert.verifySteps(["dialog_closed", "overrideBackButton: false"]);
        assert.containsNone(document.body, ".o_dialog", "should have been closed");
    });

    QUnit.module("Popover");

    QUnit.test("popover is closable with backbutton event", async function (assert) {
        assert.expect(7);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        class Parent extends Component {}

        Parent.components = { Popover };
        Parent.template = xml`
    <div>
        <Popover>
            <t t-set="opened">
                Some content
            </t>
            <button id="target">
                Show me
            </button>
        </Popover>
    </div>`;

        const target = getFixture();
        const env = makeTestEnv();

        await mount(Parent, target, { env });

        assert.containsNone(document.body, ".o_popover");
        await testUtils.dom.click(document.querySelector("#target"));
        assert.containsOnce(document.body, ".o_popover");
        assert.verifySteps(["overrideBackButton: true"]);
        // simulate 'backbutton' event triggered by the app
        await testUtils.dom.triggerEvent(document, "backbutton");
        assert.verifySteps(["overrideBackButton: false"]);
        assert.containsNone(document.body, ".o_popover", "should have been closed");

    });

    QUnit.module("ControlPanel");

    QUnit.test("mobile search: close with backbutton event", async function (assert) {
        assert.expect(7);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        const actions = {
            1: {
                id: 1,
                name: "Yes",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
            },
        };

        const views = {
            "partner,false,list": '<tree><field name="foo"/></tree>',
            "partner,false,search": `
        <search>
            <filter string="Active" name="my_projects" domain="[('boolean_field', '=', True)]"/>
            <field name="foo" string="Foo"/>
        </search>`,
        };

        const models = {
            partner: {
                fields: {
                    foo: { string: "Foo", type: "char" },
                    boolean_field: { string: "I am a boolean", type: "boolean" },
                },
                records: [{ id: 1, display_name: "First record", foo: "yop" }],
            },
        };
        const serverData = {actions, models, views};

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 1);

        // the mobile search is portaled in body, not in the fixture
        assert.containsNone(document.body, ".o_mobile_search");

        // open the search view
        await testUtils.dom.click(
            target.querySelector("button.o_enable_searchview")
        );
        // open it in full screen
        await testUtils.dom.click(
            target.querySelector(".o_toggle_searchview_full")
        );

        assert.containsOnce(document.body, ".o_mobile_search");
        assert.verifySteps(["overrideBackButton: true"]);

        // simulate 'backbutton' event triggered by the app
        await testUtils.dom.triggerEvent(target, "backbutton");
        assert.containsNone(target, ".o_mobile_search");
        assert.verifySteps(["overrideBackButton: false"]);
    });

    QUnit.module("UpdateDeviceAccountControllerMixin");

    QUnit.test("controller should call native updateAccount method when saving record", async function (assert) {
        assert.expect(4);
        patchWithCleanup(mobile.methods, {
            updateAccount( options ) {
                const { avatar, name, username } = options;
                assert.ok("should call updateAccount");
                assert.ok(avatar.startsWith(BASE64_PNG_HEADER), "should have a PNG base64 encoded avatar");
                assert.strictEqual(name, "Marc Demo");
                assert.strictEqual(username, "demo");
                return Promise.resolve();
            }
        });

        patchWithCleanup(session, {
            url(path) {
                if (path === '/web/image') {
                    return `data:image/png;base64,${MY_IMAGE}`;
                }
                return this._super(...arguments);
            },
            username: "demo",
            name: "Marc Demo",
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData: serverData,
            arch: `
                <form js_class="res_users_preferences_form">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>`,
        });
        await clickSave(target);
    });

    QUnit.test("controller should call native updateAccount method with SVG avatar when saving record", async function (assert) {
        assert.expect(4);

        patchWithCleanup(mobile.methods, {
            updateAccount( options ) {
                const { avatar, name, username } = options;
                assert.ok("should call updateAccount");
                assert.ok(avatar.startsWith(BASE64_PNG_HEADER), "should have a PNG base64 encoded avatar");
                assert.strictEqual(name, "Marc Demo");
                assert.strictEqual(username, "demo");
                return Promise.resolve();
            }
        });

        patchWithCleanup(session, {
            url(path) {
                if (path === '/web/image') {
                    return `data:image/svg+xml;base64,${BASE64_SVG_IMAGE}`;
                }
                return this._super(...arguments);
            },
            username: "demo",
            name: "Marc Demo",
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData: serverData,
            arch: `
                <form js_class="res_users_preferences_form">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>`,
        });

        await clickSave(target);
    });

    QUnit.test("UserPreferencesFormView should call native updateAccount method when saving record", async function (assert) {
        assert.expect(4);

        patchWithCleanup(mobile.methods, {
            updateAccount( options ) {
                const { avatar, name, username } = options;
                assert.ok("should call updateAccount");
                assert.ok(avatar.startsWith(BASE64_PNG_HEADER), "should have a PNG base64 encoded avatar");
                assert.strictEqual(name, "Marc Demo");
                assert.strictEqual(username, "demo");
                return Promise.resolve();
            }
        });

        patchWithCleanup(session, {
            url(path) {
                if (path === '/web/image') {
                    return `data:image/png;base64,${MY_IMAGE}`;
                }
                return this._super(...arguments);
            },
            username: "demo",
            name: "Marc Demo",
        });

        await makeView({
            type: "form",
            resModel: "users",
            serverData: serverData,
            arch: `
                <form js_class="res_users_preferences_form">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>`,
        });

        await clickSave(target);
    });
});
