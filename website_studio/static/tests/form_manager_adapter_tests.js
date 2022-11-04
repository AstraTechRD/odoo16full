/** @odoo-module **/
import { click, getFixture, legacyExtraNextTick } from "@web/../tests/helpers/utils";
import { getActionManagerServerData } from "@web/../tests/webclient/helpers";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { openStudio, registerStudioDependencies } from "@web_studio/../tests/helpers";

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

let serverData;
let target;
QUnit.module("Website Studio", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = getActionManagerServerData();
        registerStudioDependencies();

        serverData.menus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: {
                id: 1,
                children: [],
                name: "Ponies",
                appID: 1,
                actionID: 8,
                xmlid: "app_1",
            },
        };
    });

    QUnit.test(
        "open list view with sample data gives empty list view in studio",
        async function (assert) {
            serverData.views["pony,false,list"] = `<tree sample="1"><field name="name"/></tree>`;

            await createEnterpriseWebClient({
                serverData,
                mockRPC: (route) => {
                    if (route === "/website_studio/get_forms") {
                        assert.step("/website_studio/get_forms");
                        return Promise.resolve([{ id: 1, name: "partner", url: "/partner" }]);
                    }
                },
            });
            // open app Ponies (act window action)
            await click(target, ".o_app[data-menu-xmlid=app_1]");
            await legacyExtraNextTick();
            await openStudio(target);

            const websiteItem = [...target.querySelectorAll(".o_web_studio_menu_item")].filter(
                (el) => el.textContent === "Website"
            )[0];
            await click(websiteItem);
            assert.containsN(target, ".o_website_studio_form .o_web_studio_thumbnail", 2);
            const websiteStudioForms = target.querySelectorAll(
                ".o_website_studio_form .o_web_studio_thumbnail"
            );
            assert.strictEqual(websiteStudioForms[0].dataset.newForm, "true");
            assert.strictEqual(websiteStudioForms[1].dataset.url, "/partner");

            assert.verifySteps(["/website_studio/get_forms"]);
        }
    );
});
