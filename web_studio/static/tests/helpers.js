/** @odoo-module */
import { legacyExtraNextTick, click } from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";

import { systrayItem } from "@web_studio/systray_item/systray_item";
import { ormService } from "@web/core/orm_service";
import { enterpriseSubscriptionService } from "@web_enterprise/webclient/home_menu/enterprise_subscription_service";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import { studioService } from "@web_studio/studio_service";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { resetViewCompilerCache } from "@web/views/view_compiler";

export function registerStudioDependencies() {
    const serviceRegistry = registry.category("services");
    registry.category("systray").add("StudioSystrayItem", systrayItem);
    serviceRegistry.add("orm", ormService);
    serviceRegistry.add("enterprise_subscription", enterpriseSubscriptionService);
    serviceRegistry.add("home_menu", homeMenuService);
    serviceRegistry.add("studio", studioService);
    registerCleanup(() => resetViewCompilerCache());
}

export async function openStudio(target, params = {}) {
    await click(target.querySelector(".o_main_navbar .o_web_studio_navbar_item a"));
    await legacyExtraNextTick();
    if (params.noEdit) {
        const studioTabViews = target.querySelector(".o_web_studio_menu_item a");
        await click(studioTabViews);
        const controlElm = target.querySelector(
            ".o_action_manager .o_web_studio_editor .o_web_studio_views"
        );
        if (!controlElm) {
            throw new Error("We should be in the Tab 'Views' but we are not");
        }
    }
    if (params.report) {
        const studioTabReport = target.querySelectorAll(".o_web_studio_menu_item a")[1];
        await click(studioTabReport);
        await legacyExtraNextTick();
        let controlElm = target.querySelector(
            ".o_action_manager .o_web_studio_editor .o_web_studio_report_kanban"
        );
        if (!controlElm) {
            throw new Error("We should be in the Tab 'Report' but we are not");
        }
        await click(controlElm.querySelector(`.o_kanban_record[data-id="${params.report}"`));
        await legacyExtraNextTick();
        controlElm = target.querySelector(
            ".o_action_manager .o_web_studio_editor .o_web_studio_report_editor_manager"
        );
        if (!controlElm) {
            throw new Error("We should be editing the first report that showed up");
        }
    }
}

export async function leaveStudio(target) {
    await click(target.querySelector(".o_studio_navbar .o_web_studio_leave a"));
    return legacyExtraNextTick();
}

export function getReportServerData() {
    const models = {
        "ir.actions.report": {
            fields: {
                model: { type: "char" },
                report_name: { type: "char" },
                report_type: { type: "char" },
            },
            records: [{ id: 11, model: "foo", report_name: "foo_report", report_type: "pdf" }],
        },
    };

    const views = {
        "ir.actions.report,false,kanban": `
            <kanban class="o_web_studio_report_kanban" js_class="studio_report_kanban">
                <field name="report_name"/>
                <field name="report_type"/>
                <field name="id"/>
                <templates>
                    <t t-name="kanban-box">
                        <div class="oe_kanban_global_click" t-att-data-id="record.id.value">
                            <div class="oe_kanban_details">
                                <field name="report_name" groups="base.group_no_one"/>
                            </div>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        "ir.actions.report,false,search": `<search />`,
    };

    return { models, views };
}
