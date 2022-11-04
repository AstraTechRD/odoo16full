/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { ControllerNotFoundError } from "@web/webclient/actions/action_service";
import { HomeMenu } from "./home_menu";

const { Component, onMounted, onWillUnmount, xml } = owl;

export const homeMenuService = {
    dependencies: ["action", "router"],
    start(env) {
        let hasHomeMenu = false; // true iff the HomeMenu is currently displayed
        let hasBackgroundAction = false; // true iff there is an action behind the HomeMenu
        const mutex = new Mutex(); // used to protect against concurrent toggling requests

        class HomeMenuAction extends Component {
            setup() {
                this.router = useService("router");
                this.menus = useService("menu");
                this.homeMenuProps = {
                    apps: computeAppsAndMenuItems(this.menus.getMenuAsTree("root")).apps,
                };
                onMounted(() => this.onMounted());
                onWillUnmount(this.onWillUnmount);
            }
            async onMounted() {
                const { breadcrumbs } = this.env.config;
                hasHomeMenu = true;
                hasBackgroundAction = breadcrumbs.length > 0;
                this.router.pushState({ menu_id: undefined }, { lock: false, replace: true });
                this.env.bus.trigger("HOME-MENU:TOGGLED");
            }
            onWillUnmount() {
                hasHomeMenu = false;
                hasBackgroundAction = false;
                const currentMenuId = this.menus.getCurrentApp();
                if (currentMenuId) {
                    this.router.pushState({ menu_id: currentMenuId.id }, { lock: true });
                }
                this.env.bus.trigger("HOME-MENU:TOGGLED");
            }
        }
        HomeMenuAction.components = { HomeMenu };
        HomeMenuAction.target = "current";
        HomeMenuAction.template = xml`<HomeMenu t-props="homeMenuProps"/>`;

        registry.category("actions").add("menu", HomeMenuAction);

        env.bus.on("HOME-MENU:TOGGLED", null, () => {
            document.body.classList.toggle("o_home_menu_background", hasHomeMenu);
        });

        return {
            get hasHomeMenu() {
                return hasHomeMenu;
            },
            get hasBackgroundAction() {
                return hasBackgroundAction;
            },
            async toggle(show) {
                return mutex.exec(async () => {
                    show = show === undefined ? !hasHomeMenu : Boolean(show);
                    if (show !== hasHomeMenu) {
                        if (show) {
                            await env.services.action.doAction("menu");
                        } else {
                            try {
                                await env.services.action.restore();
                            } catch (err) {
                                if (!(err instanceof ControllerNotFoundError)) {
                                    throw err;
                                }
                            }
                        }
                    }
                    // hack: wait for a tick to ensure that the url has been updated before
                    // switching again
                    return new Promise((r) => setTimeout(r));
                });
            },
        };
    },
};

registry.category("services").add("home_menu", homeMenuService);
