/** @odoo-module **/
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { ModelConfigurator } from "@web_studio/client_action/model_configurator/model_configurator";
import { BG_COLORS, COLORS, ICONS } from "@web_studio/utils";
import { ComponentAdapter, ComponentWrapper, WidgetAdapterMixin } from "web.OwlCompatibility";
import { FieldMany2One } from "web.relational_fields";
import StandaloneFieldManagerMixin from "web.StandaloneFieldManagerMixin";
import Widget from "web.Widget";
import { IconCreator } from "../icon_creator/icon_creator";

const { Component, onWillStart, useExternalListener, useState } = owl;

class ModelSelector extends ComponentAdapter {
    constructor() {
        Object.assign(arguments[0], { Component: FieldMany2One });
        super(...arguments);
    }
    updateWidget() {}
    renderWidget() {}
    _trigger_up(ev) {
        if (ev.name === "field_changed" && this.props.onFieldChanged) {
            this.props.onFieldChanged(ev.data);
        }
        return super._trigger_up(...arguments);
    }
}

export const AppCreatorWrapper = Widget.extend(StandaloneFieldManagerMixin, WidgetAdapterMixin, {
    target: "fullscreen",
    /**
     * This widget is directly bound to its inner owl component and its sole purpose
     * is to instanciate it with the adequate properties: it will manually
     * mount the component when attached to the dom, will dismount it when detached
     * and destroy it when destroyed itself.
     * @constructor
     */
    init(parent, props) {
        this._super(...arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.appCreatorComponent = new ComponentWrapper(this, AppCreator, {
            ...props,
            model: this.model,
        });
    },

    async start() {
        Object.assign(this.el.style, {
            height: "100%",
            overflow: "auto",
        });
        await this._super(...arguments);
        return this.appCreatorComponent.mount(this.el);
    },

    destroy() {
        WidgetAdapterMixin.destroy.call(this);
        this._super();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Overriden to register widgets on the fly since they have been instanciated
     * by the Component.
     * @override
     */
    _onFieldChanged(ev) {
        const targetWidget = ev.data.__targetWidget;
        this._registerWidget(ev.data.dataPointID, targetWidget.name, targetWidget);
        StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);
    },
});

/**
 * App creator
 *
 * Action handling the complete creation of a new app. It requires the user
 * to enter an app name, to customize the app icon (@see IconCreator) and
 * to finally enter a menu name, with the option to bind the default app
 * model to an existing one.
 *
 * TODO: this component is bound to an action adapter since the action manager
 * cannot yet handle owl component. This file must be reviewed as soon as
 * the action manager is updated.
 * @extends Component
 */
class AppCreator extends Component {
    setup() {
        // TODO: Many2one component directly attached in XML. For now we have
        // to toggle it manually according to the state changes.
        this.state = useState({
            step: "welcome",
            appName: "",
            menuName: "",
            modelChoice: "new",
            modelOptions: [],
            modelId: false,
            iconData: {
                backgroundColor: BG_COLORS[5],
                color: COLORS[4],
                iconClass: ICONS[0],
                type: "custom_icon",
            },
        });
        this.debug = Boolean(AppCreator.env.isDebug());
        this.uiService = useService("ui");
        this.rpc = useService("rpc");

        useAutofocus();
        this.invalid = useState({
            appName: false,
            menuName: false,
            modelId: false,
        });
        useExternalListener(window, "keydown", this.onKeydown);

        onWillStart(() => this.onWillStart());
    }

    async onWillStart() {
        const recordId = await this.props.model.makeRecord("ir.actions.act_window", [
            {
                name: "model",
                relation: "ir.model",
                type: "many2one",
                domain: [
                    ["transient", "=", false],
                    ["abstract", "=", false],
                ],
            },
        ]);
        this.record = this.props.model.get(recordId);
    }

    //--------------------------------------------------------------------------
    // Getters
    //--------------------------------------------------------------------------

    /**
     * @returns {boolean}
     */
    get isReady() {
        return (
            this.state.step === "welcome" ||
            (this.state.step === "app" && this.state.appName) ||
            (this.state.step === "model" &&
                this.state.menuName &&
                (this.state.modelChoice === "new" ||
                    (this.state.modelChoice === "existing" && this.state.modelId)))
        );
    }

    //--------------------------------------------------------------------------
    // Protected
    //--------------------------------------------------------------------------

    /**
     * Switch the current step and clean all invalid keys.
     * @param {string} step
     */
    changeStep(step) {
        this.state.step = step;
        for (const key in this.invalid) {
            this.invalid[key] = false;
        }
    }

    /**
     * @returns {Promise}
     */
    async createNewApp() {
        this.uiService.block();
        const iconValue =
            this.state.iconData.type === "custom_icon"
                ? // custom icon data
                  [
                      this.state.iconData.iconClass,
                      this.state.iconData.color,
                      this.state.iconData.backgroundColor,
                  ]
                : // attachment
                  this.state.iconData.uploaded_attachment_id;

        try {
            const result = await this.rpc({
                route: "/web_studio/create_new_app",
                params: {
                    app_name: this.state.appName,
                    menu_name: this.state.menuName,
                    model_choice: this.state.modelChoice,
                    model_id: this.state.modelChoice && this.state.modelId,
                    model_options: this.state.modelOptions,
                    icon: iconValue,
                    context: this.env.session.user_context,
                },
            });
            this.props.onNewAppCreated(result);
        } catch (error) {
            if (!error || !(error instanceof Error)) {
                this.onPrevious();
            } else {
                throw error;
            }
        } finally {
            this.uiService.unblock();
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @param {Event} ev
     */
    onChecked(ev) {
        const modelChoice = ev.currentTarget.value;
        this.state.modelChoice = modelChoice;
        if (this.state.modelChoice === "new") {
            this.state.modelId = undefined;
        }
    }

    /**
     * @param {Object} detail
     */
    onModelIdChanged(detail) {
        if (this.state.modelChoice === "existing") {
            this.state.modelId = detail.changes.model.id;
            this.invalid.modelId = isNaN(this.state.modelId);
        } else {
            this.state.modelId = false;
            this.invalid.modelId = false;
        }
    }

    /**
     * @param {Object} icon
     */
    onIconChanged(icon) {
        for (const key in this.state.iconData) {
            delete this.state.iconData[key];
        }
        Object.assign(this.state.iconData, icon);
    }

    /**
     * @param {InputEvent} ev
     */
    onInput(ev) {
        const input = ev.currentTarget;
        if (this.invalid[input.id]) {
            this.invalid[input.id] = !input.value;
        }
        this.state[input.id] = input.value;
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        if (
            ev.key === "Enter" &&
            !(
                ev.target.classList &&
                ev.target.classList.contains("o_web_studio_app_creator_previous")
            )
        ) {
            ev.preventDefault();
            this.onNext();
        }
    }

    /**
     * Handle the confirmation of options in the modelconfigurator
     * @param {Object} options
     */
    onConfirmOptions(options) {
        this.state.modelOptions = Object.entries(options)
            .filter((opt) => opt[1].value)
            .map((opt) => opt[0]);
        return this.onNext();
    }

    async onNext() {
        switch (this.state.step) {
            case "welcome": {
                this.changeStep("app");
                break;
            }
            case "app": {
                if (!this.state.appName) {
                    this.invalid.appName = true;
                } else {
                    this.changeStep("model");
                }
                break;
            }
            case "model": {
                if (!this.state.menuName) {
                    this.invalid.menuName = true;
                }
                if (this.state.modelChoice === "existing" && !this.state.modelId) {
                    this.invalid.modelId = true;
                } else if (this.state.modelChoice === "new") {
                    this.invalid.modelId = false;
                }
                const isValid = Object.values(this.invalid).reduce(
                    (valid, key) => valid && !key,
                    true
                );
                if (isValid) {
                    if (this.state.modelChoice === "new") {
                        this.changeStep("model_configuration");
                    } else {
                        this.createNewApp();
                    }
                }
                break;
            }
            case "model_configuration": {
                // no validation for this step, every configuration is valid
                this.createNewApp();
                break;
            }
        }
    }

    async onPrevious() {
        switch (this.state.step) {
            case "app": {
                this.changeStep("welcome");
                break;
            }
            case "model": {
                this.changeStep("app");
                break;
            }
            case "model_configuration": {
                this.changeStep("model");
                break;
            }
        }
    }
}

AppCreator.components = { ModelSelector, IconCreator, ModelConfigurator };
AppCreator.props = {
    model: Object,
    onNewAppCreated: { type: Function },
};
AppCreator.template = "web_studio.AppCreator";
