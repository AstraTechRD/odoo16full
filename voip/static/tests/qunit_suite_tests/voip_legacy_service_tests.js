/** @odoo-module **/

import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { getFixture } from "@web/../tests/helpers/utils";

import { voipLegacyCompatibilityService } from "@voip/js/legacy_compatibility";

const serviceRegistry = registry.category("services");

QUnit.module("voip", (hooks) => {
    hooks.beforeEach(() => {
        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add("voip_legacy", voipLegacyCompatibilityService);
        serviceRegistry.add("voip", {
            start() {
                return {
                    canCall: false,
                    call: () => {}
                }
            }
        })
    });

    QUnit.module("voipLegacyCompatibilityService");

    QUnit.test("can display a notification on 'voip-call' event", async function (assert) {
        serviceRegistry.add("voip", {
            start() {
                return {
                    canCall: true,
                    call: () => {assert.step("call made")}
                }
            }
        }, { force: true});

        await makeTestEnv();
        const fixture = getFixture();
        fixture.dispatchEvent(new CustomEvent("voip-call", {
            bubbles: true,
            detail: { number: "046546876655" },
        }));
        assert.verifySteps(["call made"]);
    });
});
