/** @odoo-module */

import { ViewButton } from "@web/views/view_button/view_button";
import { ViewCompiler } from "@web/views/view_compiler";
import { patch } from "@web/core/utils/patch";

import { StudioApproval } from "@web_studio/approval/studio_approval";
import { useApproval } from "@web_studio/approval/approval_hook";

patch(ViewCompiler.prototype, "web_studio.ViewCompilerApproval", {
    compileButton(el, params) {
        const button = this._super(...arguments);
        const studioApproval = el.getAttribute("studio_approval") === "True";
        if (studioApproval) {
            button.setAttribute("studioApproval", studioApproval);
        }
        return button;
    },
});

patch(ViewButton.prototype, "web_studio.ViewButtonApproval", {
    setup() {
        this._super(...arguments);
        if (this.props.studioApproval) {
            const { type, name } = this.props.clickParams;
            const action = type === "action" && name;
            const method = type === "object" && name;
            this.approval = useApproval({
                record: this.props.record,
                action,
                method,
            });

            const onClickViewButton = this.env.onClickViewButton;
            owl.useSubEnv({
                onClickViewButton: (params) => {
                    params.beforeExecute = async () => this.approval.checkApproval();
                    onClickViewButton(params);
                },
            });
        }
    },
});

ViewButton.props.push("studioApproval?");
ViewButton.components = Object.assign(ViewButton.components || {}, { StudioApproval });
