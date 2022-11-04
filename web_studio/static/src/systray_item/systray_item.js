/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, useRef } = owl;

class StudioSystray extends Component {
    setup() {
        this.hm = useService("home_menu");
        this.studio = useService("studio");
        this.rootRef = useRef("root");
        this.env.bus.on("ACTION_MANAGER:UI-UPDATED", this, (mode) => {
            if (mode !== "new" && this.rootRef.el) {
                this.rootRef.el.classList.toggle("o_disabled", this.buttonDisabled);
            }
        });
    }
    get buttonDisabled() {
        return !this.studio.isStudioEditable();
    }
    _onClick() {
        this.studio.open();
    }
}
StudioSystray.template = "web_studio.SystrayItem";

export const systrayItem = {
    Component: StudioSystray,
    isDisplayed: (env) => env.services.user.isSystem,
};

registry.category("systray").add("StudioSystrayItem", systrayItem, { sequence: 1 });
