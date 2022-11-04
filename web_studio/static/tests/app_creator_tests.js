/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import {
    click,
    findChildren,
    getFixture,
    nextTick,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { AppCreatorWrapper } from "@web_studio/client_action/app_creator/app_creator";
import { IconCreator } from "@web_studio/client_action/icon_creator/icon_creator";
import testUtils from "web.test_utils";

const { Component } = owl;
const sampleIconUrl = "/web_enterprise/Parent.src/img/default_icon_app.png";

const createAppCreator = async ({ env, rpc, state, onNewAppCreated }) => {
    onNewAppCreated = onNewAppCreated || (() => {});
    const cleanUp = await testUtils.mock.addMockEnvironmentOwl(Component, {
        debug: QUnit.config.debug,
        env,
        mockRPC: rpc,
    });
    const target = getFixture();
    const wrapper = new AppCreatorWrapper(null, { onNewAppCreated });
    await wrapper.prependTo(target);
    const { component } = findChildren(wrapper.appCreatorComponent);
    if (state) {
        Object.assign(component.state, state);
        await nextTick();
    }
    registerCleanup(() => {
        wrapper.destroy();
        cleanUp();
    });
    return { state: component.state, target };
};

const editInput = async (el, selector, value) => {
    const target = el.querySelector(selector);
    target.value = value;
    await triggerEvent(target, null, "input");
};

QUnit.module("Studio", (hooks) => {
    hooks.beforeEach(() => {
        IconCreator.enableTransitions = false;
        registerCleanup(() => {
            IconCreator.enableTransitions = true;
        });
    });

    QUnit.module("AppCreator");

    QUnit.test("app creator: standard flow with model creation", async (assert) => {
        assert.expect(39);

        const { state, target } = await createAppCreator({
            env: {
                services: {
                    ui: {
                        block: () => assert.step("UI blocked"),
                        unblock: () => assert.step("UI unblocked"),
                    },
                    async httpRequest(route) {
                        if (route === "/web/binary/upload_attachment") {
                            assert.step(route);
                            return `[{ "id": 666 }]`;
                        }
                    },
                    http: {
                        async post(route) {
                            if (route === "/web/binary/upload_attachment") {
                                assert.step(route);
                                return `[{ "id": 666 }]`;
                            }
                        },
                    },
                },
            },
            onNewAppCreated: () => assert.step("new-app-created"),
            async rpc(route, params) {
                if (route === "/web_studio/create_new_app") {
                    const { app_name, menu_name, model_choice, model_id, model_options } = params;
                    assert.strictEqual(app_name, "Kikou", "App name should be correct");
                    assert.strictEqual(menu_name, "Petite Perruche", "Menu name should be correct");
                    assert.notOk(model_id, "Should not have a model id");
                    assert.strictEqual(model_choice, "new", "Model choice should be 'new'");
                    assert.deepEqual(
                        model_options,
                        ["use_partner", "use_sequence", "use_mail", "use_active"],
                        "Model options should include the defaults and 'use_partner'"
                    );
                }
                if (route === "/web/dataset/call_kw/ir.attachment/read") {
                    assert.strictEqual(params.model, "ir.attachment");
                    return [{ datas: sampleIconUrl }];
                }
            },
        });

        // step: 'welcome'
        assert.strictEqual(state.step, "welcome", "Current step should be welcome");
        assert.containsNone(
            target,
            ".o_web_studio_app_creator_previous",
            "Previous button should not be rendered at step welcome"
        );
        assert.hasClass(
            target.querySelector(".o_web_studio_app_creator_next"),
            "is_ready",
            "Next button should be ready at step welcome"
        );

        // go to step: 'app'
        await click(target, ".o_web_studio_app_creator_next");

        assert.strictEqual(state.step, "app", "Current step should be app");
        assert.containsOnce(
            target,
            ".o_web_studio_icon_creator .o_web_studio_selectors",
            "Icon creator should be rendered in edit mode"
        );

        // Icon creator interactions
        const icon = target.querySelector(".o_app_icon i");

        // Initial state: take default values
        assert.strictEqual(
            target.querySelector(".o_app_icon").style.backgroundColor,
            "rgb(52, 73, 94)",
            "default background color: #34495e"
        );
        assert.strictEqual(icon.style.color, "rgb(241, 196, 15)", "default color: #f1c40f");
        assert.hasClass(icon, "fa fa-diamond", "default icon class: diamond");

        await click(target.getElementsByClassName("o_web_studio_selector")[0]);

        assert.containsOnce(target, ".o_web_studio_palette", "the first palette should be open");

        await triggerEvent(target, ".o_web_studio_palette", "mouseleave");

        assert.containsNone(
            target,
            ".o_web_studio_palette",
            "leaving palette with mouse should close it"
        );

        await click(target.querySelectorAll(".o_web_studio_selectors > .o_web_studio_selector")[0]);
        await click(target.querySelectorAll(".o_web_studio_selectors > .o_web_studio_selector")[1]);

        assert.containsOnce(
            target,
            ".o_web_studio_palette",
            "opening another palette should close the first"
        );

        await click(target.querySelectorAll(".o_web_studio_palette div")[2]);
        await click(target.querySelectorAll(".o_web_studio_selectors > .o_web_studio_selector")[2]);
        await click(target.querySelectorAll(".o_web_studio_icons_library div")[43]);

        await triggerEvent(target, ".o_web_studio_icons_library", "mouseleave");

        assert.containsNone(
            target,
            ".o_web_studio_palette",
            "no palette should be visible anymore"
        );

        assert.strictEqual(
            target.querySelectorAll(".o_web_studio_selector")[1].style.backgroundColor,
            "rgb(0, 222, 201)", // translation of #00dec9
            "color selector should have changed"
        );
        assert.strictEqual(
            icon.style.color,
            "rgb(0, 222, 201)",
            "icon color should also have changed"
        );

        assert.hasClass(
            target.querySelector(".o_web_studio_selector i"),
            "fa fa-heart",
            "class selector should have changed"
        );
        assert.hasClass(icon, "fa fa-heart", "icon class should also have changed");

        // Click and upload on first link: upload a file
        // mimic the event triggered by the upload (jquery)
        // we do not use the triggerEvent helper as it requires the element to be visible,
        // which isn't the case here (and this is valid)
        target.querySelector(".o_web_studio_upload input").dispatchEvent(new Event("change"));
        await nextTick();

        assert.strictEqual(
            state.iconData.uploaded_attachment_id,
            666,
            "attachment id should have been given by the RPC"
        );
        assert.strictEqual(
            target.querySelector(".o_web_studio_uploaded_image").style.backgroundImage,
            `url("data:image/png;base64,${sampleIconUrl}")`,
            "icon should take the updated attachment data"
        );

        // try to go to step 'model'
        await click(target, ".o_web_studio_app_creator_next");

        const appNameInput = target.querySelector('input[name="appName"]').parentNode;

        assert.strictEqual(
            state.step,
            "app",
            "Current step should not be update because the input is not filled"
        );
        assert.hasClass(
            appNameInput,
            "o_web_studio_app_creator_field_warning",
            "Input should be in warning mode"
        );

        await editInput(target, 'input[name="appName"]', "Kikou");
        assert.doesNotHaveClass(
            appNameInput,
            "o_web_studio_app_creator_field_warning",
            "Input shouldn't be in warning mode anymore"
        );

        // step: 'model'
        await click(target, ".o_web_studio_app_creator_next");

        assert.strictEqual(state.step, "model", "Current step should be model");

        assert.containsNone(
            target,
            ".o_web_studio_selectors",
            "Icon creator should be rendered in readonly mode"
        );

        // try to go to next step
        await click(target, ".o_web_studio_app_creator_next");

        assert.hasClass(
            target.querySelector('input[name="menuName"]').parentNode,
            "o_web_studio_app_creator_field_warning",
            "Input should be in warning mode"
        );

        await editInput(target, 'input[name="menuName"]', "Petite Perruche");

        // go to next step (model configuration)
        await click(target, ".o_web_studio_app_creator_next");
        assert.strictEqual(
            state.step,
            "model_configuration",
            "Current step should be model_configuration"
        );
        assert.containsOnce(
            target,
            'input[name="use_active"]',
            "Debug options should be visible without debug mode"
        );
        // check an option
        await click(target, 'input[name="use_partner"]');
        assert.containsOnce(
            target,
            'input[name="use_partner"]:checked',
            "Option should have been checked"
        );

        // go back then go forward again
        await click(target, ".o_web_studio_model_configurator_previous");
        await click(target, ".o_web_studio_app_creator_next");
        // options should have been reset
        assert.containsNone(
            target,
            'input[name="use_partner"]:checked',
            "Options should have been reset by going back then forward"
        );

        // check the option again, we want to test it in the RPC
        await click(target, 'input[name="use_partner"]');

        await click(target, ".o_web_studio_model_configurator_next");

        assert.verifySteps([
            "/web/binary/upload_attachment",
            "UI blocked",
            "new-app-created",
            "UI unblocked",
        ]);
    });

    QUnit.test("app creator: has 'lines' options to auto-create a one2many", async (assert) => {
        assert.expect(7);

        const { target } = await createAppCreator({
            env: {
                services: {
                    ui: { block: () => {}, unblock: () => {} },
                },
            },
            rpc: async (route, params) => {
                if (route === "/web_studio/create_new_app") {
                    const { app_name, menu_name, model_choice, model_id, model_options } = params;
                    assert.strictEqual(app_name, "testApp", "App name should be correct");
                    assert.strictEqual(menu_name, "testMenu", "Menu name should be correct");
                    assert.notOk(model_id, "Should not have a model id");
                    assert.strictEqual(model_choice, "new", "Model choice should be 'new'");
                    assert.deepEqual(
                        model_options,
                        ["lines", "use_sequence", "use_mail", "use_active"],
                        "Model options should include the defaults and 'lines'"
                    );
                }
            },
        });

        await click(target, ".o_web_studio_app_creator_next");
        await editInput(target, "input[id='appName']", "testApp");
        await click(target, ".o_web_studio_app_creator_next");
        await editInput(target, "input[id='menuName']", "testMenu");
        await click(target, ".o_web_studio_app_creator_next");

        assert.containsOnce(
            target,
            ".o_web_studio_model_configurator_option input[type='checkbox'][name='lines'][id='lines']"
        );
        assert.strictEqual(
            target.querySelector("label[for='lines']").textContent,
            "LinesAdd details to your records with an embedded list view"
        );

        await click(
            target,
            ".o_web_studio_model_configurator_option input[type='checkbox'][name='lines']"
        );
        await click(target, ".o_web_studio_model_configurator_next");
    });

    QUnit.test("app creator: debug flow with existing model", async (assert) => {
        assert.expect(16);

        const { state, target } = await createAppCreator({
            env: {
                isDebug: () => true,
                services: {
                    ui: { block: () => {}, unblock: () => {} },
                },
            },
            async rpc(route, params) {
                assert.step(route);
                switch (route) {
                    case "/web/dataset/call_kw/ir.model/name_search": {
                        assert.strictEqual(
                            params.model,
                            "ir.model",
                            "request should target the right model"
                        );
                        return [[69, "The Value"]];
                    }
                    case "/web_studio/create_new_app": {
                        assert.strictEqual(
                            params.model_id,
                            69,
                            "model id should be the one provided"
                        );
                    }
                }
            },
            state: {
                menuName: "Kikou",
                step: "model",
            },
        });

        let buttonNext = target.querySelector("button.o_web_studio_app_creator_next");

        assert.hasClass(buttonNext, "is_ready");

        await editInput(target, 'input[name="menuName"]', "Petite Perruche");
        // check the 'new model' radio
        await click(target, 'input[name="model_choice"][value="new"]');

        // go to next step (model configuration)
        await click(target, ".o_web_studio_app_creator_next");
        assert.strictEqual(
            state.step,
            "model_configuration",
            "Current step should be model_configuration"
        );
        assert.containsOnce(
            target,
            'input[name="use_active"]',
            "Debug options should be visible in debug mode"
        );
        // go back, we want the 'existing model flow'
        await click(target, ".o_web_studio_model_configurator_previous");

        // since we came back, we need to update our buttonNext ref - the querySelector is not live
        buttonNext = target.querySelector("button.o_web_studio_app_creator_next");

        // check the 'existing model' radio
        await click(target, 'input[name="model_choice"][value="existing"]');

        assert.doesNotHaveClass(
            target.querySelector(".o_web_studio_app_creator_model"),
            "o_web_studio_app_creator_field_warning"
        );
        assert.doesNotHaveClass(buttonNext, "is_ready");
        assert.containsOnce(
            target,
            ".o_field_many2one",
            "There should be a many2one to select a model"
        );

        await click(buttonNext);

        assert.hasClass(
            target.querySelector(".o_web_studio_app_creator_model"),
            "o_web_studio_app_creator_field_warning"
        );
        assert.doesNotHaveClass(buttonNext, "is_ready");

        await click(target, ".o_field_many2one input");
        await click(document.querySelector(".ui-menu-item-wrapper"));

        assert.strictEqual(target.querySelector(".o_field_many2one input").value, "The Value");

        assert.doesNotHaveClass(
            target.querySelector(".o_web_studio_app_creator_model"),
            "o_web_studio_app_creator_field_warning"
        );
        assert.hasClass(buttonNext, "is_ready");

        await click(buttonNext);

        assert.verifySteps([
            "/web/dataset/call_kw/ir.model/name_search",
            "/web_studio/create_new_app",
        ]);
    });

    QUnit.test('app creator: navigate through steps using "ENTER"', async (assert) => {
        assert.expect(12);

        const { state, target } = await createAppCreator({
            env: {
                services: {
                    ui: {
                        block: () => assert.step("UI blocked"),
                        unblock: () => assert.step("UI unblocked"),
                    },
                },
            },
            onNewAppCreated: () => assert.step("new-app-created"),
            async rpc(route, { app_name, menu_name, model_id }) {
                if (route === "/web_studio/create_new_app") {
                    assert.strictEqual(app_name, "Kikou", "App name should be correct");
                    assert.strictEqual(menu_name, "Petite Perruche", "Menu name should be correct");
                    assert.notOk(model_id, "Should not have a model id");
                }
            },
        });

        // step: 'welcome'
        assert.strictEqual(state.step, "welcome", "Current step should be set to 1");

        // go to step 'app'
        await triggerEvent(document, null, "keydown", { key: "Enter" });
        assert.strictEqual(state.step, "app", "Current step should be set to app");

        // try to go to step 'model'
        await triggerEvent(document, null, "keydown", { key: "Enter" });
        assert.strictEqual(
            state.step,
            "app",
            "Current step should not be update because the input is not filled"
        );

        await editInput(target, 'input[name="appName"]', "Kikou");

        // go to step 'model'
        await triggerEvent(document, null, "keydown", { key: "Enter" });
        assert.strictEqual(state.step, "model", "Current step should be model");

        // try to create app
        await triggerEvent(document, null, "keydown", { key: "Enter" });
        assert.hasClass(
            target.querySelector('input[name="menuName"]').parentNode,
            "o_web_studio_app_creator_field_warning",
            "a warning should be displayed on the input"
        );

        await editInput(target, 'input[name="menuName"]', "Petite Perruche");
        await triggerEvent(document, null, "keydown", { key: "Enter" });
        await triggerEvent(document, null, "keydown", { key: "Enter" });

        assert.verifySteps(["UI blocked", "new-app-created", "UI unblocked"]);
    });
});
