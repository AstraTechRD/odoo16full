/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, "web_studio.MockServer", {
    performRPC(route, args) {
        if (route === "/web_studio/activity_allowed") {
            return Promise.resolve(this.mockActivityAllowed());
        }
        if (route === "/web_studio/get_studio_view_arch") {
            return Promise.resolve(this.mockGetStudioViewArch());
        }
        if (route === "/web_studio/chatter_allowed") {
            return Promise.resolve(this.mockChatterAllowed());
        }
        if (route === "/web_studio/get_default_value") {
            return Promise.resolve(this.mockGetDefaultValue());
        }
        if (route === "/web_studio/get_studio_action") {
            return Promise.resolve(this.mockGetStudioAction(args));
        }
        if (route === "/web_studio/edit_view") {
            return Promise.resolve(this.mockEditView(args));
        }
        return this._super(...arguments);
    },

    mockActivityAllowed() {
        return false;
    },

    mockChatterAllowed() {
        return false;
    },

    mockGetStudioViewArch() {
        return {
            studio_view_id: false,
            studio_view_arch: "<data/>",
        };
    },

    mockGetDefaultValue() {
        return {};
    },

    mockGetStudioAction(args) {
        if (args.action_name === "reports") {
            return {
                name: "Reports",
                res_model: "ir.actions.report",
                target: "current",
                type: "ir.actions.act_window",
                views: [[false, "kanban"]],
            };
        }
    },

    mockEditView(args) {
        const viewId = args.view_id;
        if (!viewId) {
            throw new Error(
                "To use the 'edit_view' mocked controller, you should specify a unique id on the view you are editing"
            );
        }
        const uniqueViewKey = Object.keys(this.archs)
            .map((k) => k.split(","))
            .filter(([model, vid, vtype]) => vid === `${viewId}`);

        if (!uniqueViewKey.length) {
            throw new Error(`No view with id "${viewId}" in edit_view`);
        }
        if (uniqueViewKey.length > 1) {
            throw new Error(
                `There are multiple views with id "${viewId}", and probably for different models.`
            );
        }
        const [modelName, , viewType] = uniqueViewKey[0];

        const view = this.getView(modelName, [viewId, viewType], {
            context: args.context,
            options: {},
        });
        const models = {};
        for (const modelName of Object.keys(view.models)) {
            models[modelName] = this.mockFieldsGet(modelName);
        }
        return {
            views: {
                [viewType]: view,
            },
            models,
            studio_view_id: false,
        };
    },
});
