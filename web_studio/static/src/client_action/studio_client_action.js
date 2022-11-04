/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { cleanDomFromBootstrap } from "@web/legacy/utils";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { ComponentAdapter } from "web.OwlCompatibility";
import { AppCreatorWrapper } from "./app_creator/app_creator";
import { Editor } from "./editor/editor";
import { StudioNavbar } from "./navbar/navbar";
import { StudioHomeMenu } from "./studio_home_menu/studio_home_menu";

const { Component, onWillStart, onMounted, onPatched, onWillUnmount } = owl;

export class StudioClientAction extends Component {
    setup() {
        this.studio = useService("studio");
        useBus(this.studio.bus, "UPDATE", () => {
            this.render(true);
            cleanDomFromBootstrap();
        });

        this.menus = useService("menu");
        this.actionService = useService("action");
        this.homeMenuProps = {
            apps: computeAppsAndMenuItems(this.menus.getMenuAsTree("root")).apps,
        };
        useBus(this.env.bus, "MENUS:APP-CHANGED", () => {
            this.homeMenuProps = {
                apps: computeAppsAndMenuItems(this.menus.getMenuAsTree("root")).apps,
            };
            this.render(true);
        });

        this.AppCreatorWrapper = AppCreatorWrapper; // to remove

        onWillStart(this.onWillStart);
        onMounted(this.onMounted);
        onPatched(this.onPatched);
        onWillUnmount(this.onWillUnmount);
    }

    onWillStart() {
        return this.studio.ready;
    }

    onMounted() {
        this.studio.pushState();
        document.body.classList.add("o_in_studio"); // FIXME ?
    }

    onPatched() {
        this.studio.pushState();
    }

    onWillUnmount() {
        document.body.classList.remove("o_in_studio");
    }

    async onNewAppCreated({ action_id, menu_id }) {
        await this.menus.reload();
        this.menus.setCurrentMenu(menu_id);
        const action = await this.actionService.loadAction(action_id);
        this.studio.setParams({
            mode: this.studio.MODES.EDITOR,
            editorTab: "views",
            action,
            viewType: "form",
        });
    }
}
StudioClientAction.template = "web_studio.StudioClientAction";
StudioClientAction.components = {
    StudioNavbar,
    StudioHomeMenu,
    Editor,
    ComponentAdapter: class extends ComponentAdapter {
        setup() {
            super.setup();
            this.env = Component.env;
        }
    },
};
StudioClientAction.target = "fullscreen";

registry.category("lazy_components").add("StudioClientAction", StudioClientAction);
// force: true to bypass the studio lazy loading action next time and just use this one directly
registry.category("actions").add("studio", StudioClientAction, { force: true });
