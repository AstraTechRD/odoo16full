/** @odoo-module **/
import { ComponentAdapter } from "web.OwlCompatibility";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { NewViewDialog } from "@web_studio/client_action/editor/new_view_dialogs/new_view_dialog";
import { MapNewViewDialog } from "@web_studio/client_action/editor/new_view_dialogs/map_new_view_dialog";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import ActionEditor from "web_studio.ActionEditor";
import { ActionEditorMain } from "../../legacy/action_editor_main";

const { Component } = owl;

export class EditorAdapter extends ComponentAdapter {
    constructor(props) {
        // force dummy Component not to crash
        props.Component = Component;
        super(...arguments);
    }

    setup() {
        super.setup();
        this.studio = useService("studio");

        if (this.studio.editedViewType) {
            this.props.Component = ActionEditorMain;
        } else {
            this.props.Component = ActionEditor;
        }

        this.dialog = useService("dialog");
        this.user = useService("user");
        this.dialog = useService("dialog");
        this.viewService = useService("view");
        this.rpc = useService("rpc");
        this.wowlEnv = this.env;
        this.env = Component.env; // use the legacy env
    }

    _trigger_up(ev) {
        const { name, data } = ev;
        if (name === "studio_new_view") {
            return this._onNewView(data);
        }
        if (name === "studio_disable_view") {
            return this._onDisableView(data);
        }
        if (name === "studio_default_view") {
            return this._onSetDefaultView(data);
        }
        if (name === "studio_restore_default_view") {
            return this._onRestoreDefaultView(data);
        }
        if (name === "studio_edit_action") {
            return this._onEditAction(data);
        }
        return super._trigger_up(...arguments);
    }

    async _onNewView(data) {
        const viewType = data.view_type;
        const activityAllowed = await this.rpc("/web_studio/activity_allowed", {
            model: this.studio.editedAction.res_model,
        });
        if (viewType === "activity" && !activityAllowed) {
            this.env.services.notification.notify({
                title: false,
                type: "danger",
                message: this.env._t("Activity view unavailable on this model"),
            });
            return;
        }

        const viewMode = this.studio.editedAction.view_mode + "," + viewType;
        const viewAdded = await this.addViewType(this.studio.editedAction, viewType, {
            view_mode: viewMode,
        });
        if (viewAdded) {
            return this.studio.reload({ viewType });
        }
    }

    /**
     * @private
     * @param {Object} action
     * @param {String} view_type
     * @param {Object} args
     * @returns {Promise}
     */
    async addViewType(action, viewType, args) {
        let viewAdded = await this.rpc("/web_studio/add_view_type", {
            action_type: action.type,
            action_id: action.id,
            res_model: action.res_model,
            view_type: viewType,
            args: args,
            context: this.user.context,
        });

        if (viewAdded !== true) {
            viewAdded = new Promise((resolve) => {
                let DialogClass;
                const dialogProps = {
                    confirm: async () => {
                        await this.editAction(action, args);
                        resolve(true);
                    },
                    cancel: () => resolve(false),
                };
                if (["gantt", "calendar", "cohort"].includes(viewType)) {
                    DialogClass = NewViewDialog;
                    dialogProps.viewType = viewType;
                } else if (viewType === "map") {
                    DialogClass = MapNewViewDialog;
                } else {
                    this.dialog.add(AlertDialog, {
                        body: this.env._lt(
                            "Creating this type of view is not currently supported in Studio."
                        ),
                    });
                    resolve(false);
                }
                this.dialog.add(DialogClass, dialogProps);
            });
        }
        return viewAdded;
    }

    /**
     * @private
     * @param {OdooEvent} event
     */
    async _onEditAction(data) {
        const args = data.args;
        if (!args) {
            return;
        }
        await this.editAction(this.studio.editedAction, args);
        this.studio.reload();
    }

    /**
     * @private
     * @param {Object} action
     * @param {Object} args
     * @returns {Promise}
     */
    async editAction(action, args) {
        this.env.bus.trigger("clear_cache");
        const result = await this.rpc("/web_studio/edit_action", {
            action_type: action.type,
            action_id: action.id,
            args: args,
            context: this.user.context,
        });
        if (result !== true) {
            this.dialog.add(AlertDialog, {
                body: result,
            });
        }
    }

    /**
     * @private
     * @param {String} view_mode
     * @returns {Promise}
     */
    async _writeViewMode(viewMode) {
        await this.editAction(this.studio.editedAction, { view_mode: viewMode });
        this.studio.reload({ viewType: null });
    }

    _onDisableView(data) {
        const viewType = data.view_type;
        const viewMode = this.studio.editedAction.view_mode
            .split(",")
            .filter((m) => m !== viewType);

        if (!viewMode.length) {
            this.dialog.add(AlertDialog, {
                body: this.env._t("You cannot deactivate this view as it is the last one active."),
            });
        } else {
            this._writeViewMode(viewMode.toString());
        }
    }

    _onSetDefaultView(data) {
        const viewType = data.view_type;
        const actionViewModes = this.studio.editedAction.view_mode.split(",");

        const viewMode = actionViewModes.filter((vt) => vt !== viewType);
        viewMode.unshift(viewType);

        return this._writeViewMode(viewMode.toString());
    }

    _onRestoreDefaultView(data) {
        const message = this.env._t(
            "Are you sure you want to restore the default view?\r\nAll customization done with studio on this view will be lost."
        );
        const { context, views, res_model } = this.studio.editedAction;
        const viewType = data.view_type;

        const confirm = async () => {
            const newContext = Object.assign({}, context, {
                studio: true,
                lang: false,
            });
            this.env.bus.trigger("clear_cache");
            // To restore the default view from an inherited one, we need first to retrieve the default view id
            const result = await this.viewService.loadViews(
                {
                    resModel: res_model,
                    views,
                    context: newContext,
                },
                { loadIrFilters: true }
            );

            return this.rpc("/web_studio/restore_default_view", {
                view_id: result.views[viewType].id,
            });
        };

        this.dialog.add(ConfirmationDialog, {
            body: message,
            confirm,
        });
    }

    get widgetArgs() {
        const { editedAction, editedViewType, editedControllerState, x2mEditorPath } = this.studio;
        if (this.props.Component === ActionEditor) {
            return [editedAction];
        } else {
            return [
                {
                    action: editedAction,
                    viewType: editedViewType,
                    controllerState: editedControllerState,
                    x2mEditorPath: x2mEditorPath,
                    wowlEnv: this.wowlEnv,
                },
            ];
        }
    }
}

registry.category("actions").add("web_studio.action_editor", EditorAdapter);
