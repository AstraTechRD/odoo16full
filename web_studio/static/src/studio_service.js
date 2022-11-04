/** @odoo-module **/
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { getCookie, setCookie } from "web.utils.cookies";
import { delay } from "web.concurrency";
import legacyBus from "web_studio.bus";
import { resetViewCompilerCache } from "@web/views/view_compiler";

const { EventBus } = owl;

const URL_VIEW_KEY = "_view_type";
const URL_ACTION_KEY = "_action";
const URL_TAB_KEY = "_tab";
const URL_MODE_KEY = "mode";

export const MODES = {
    EDITOR: "editor",
    HOME_MENU: "home_menu",
    APP_CREATOR: "app_creator",
};

export class NotEditableActionError extends Error {}

export const SUPPORTED_VIEW_TYPES = [
    "activity",
    "calendar",
    "cohort",
    "dashboard",
    "form",
    "gantt",
    "graph",
    "kanban",
    "list",
    "map",
    "pivot",
    "search",
];

export const studioService = {
    dependencies: ["action", "home_menu", "router", "user"],
    async start(env, { user }) {
        function _getCurrentAction() {
            const currentController = env.services.action.currentController;
            return currentController ? currentController.action : null;
        }

        function _isStudioEditable(action) {
            if (action.type === "ir.actions.client") {
                // home_menu is somehow customizable (app creator)
                return action.tag === "menu" ? true : false;
            }
            if (action.type === "ir.actions.act_window" && action.xml_id) {
                if (
                    action.res_model.indexOf("settings") > -1 &&
                    action.res_model.indexOf("x_") !== 0
                ) {
                    return false; // settings views aren't editable; but x_settings is
                }
                if (action.res_model === "board.board") {
                    return false; // dashboard isn't editable
                }
                if (action.view_mode === "qweb") {
                    // Apparently there is a QWebView that allows to
                    // implement ActWindow actions that are completely custom
                    // but not editable by studio
                    return false;
                }
                return action.res_model ? true : false;
            }
            return false;
        }

        function isViewEditable(view) {
            return view && SUPPORTED_VIEW_TYPES.includes(view);
        }

        const bus = new EventBus();
        let inStudio = false;

        const state = {
            studioMode: null,
            editedViewType: null,
            editedAction: null,
            editedControllerState: null,
            editorTab: "views",
            x2mEditorPath: [],
            editedReport: null,
        };

        async function _loadParamsFromURL() {
            const currentHash = env.services.router.current.hash;
            user.removeFromContext("studio");
            if (currentHash.action === "studio") {
                user.updateContext({ studio: 1 });
                state.studioMode = currentHash[URL_MODE_KEY];
                state.editedViewType = currentHash[URL_VIEW_KEY] || null;
                state.editorTab = currentHash[URL_TAB_KEY] || null;

                const editedActionId = currentHash[URL_ACTION_KEY];
                const additionalContext = {};
                if (state.studioMode === MODES.EDITOR) {
                    if (currentHash.active_id) {
                        additionalContext.active_id = currentHash.active_id;
                    }
                    if (editedActionId) {
                        state.editedAction = await env.services.action.loadAction(
                            editedActionId,
                            additionalContext
                        );
                    } else {
                        state.editedAction = null;
                    }
                }
                if (!state.editedAction || !_isStudioEditable(state.editedAction)) {
                    state.studioMode = state.studioMode || MODES.HOME_MENU;
                    state.editedAction = null;
                    state.editedViewType = null;
                    state.editorTab = null;
                }
            }
        }

        let studioProm = _loadParamsFromURL();
        env.bus.on("ROUTE_CHANGE", null, async () => {
            studioProm = _loadParamsFromURL();
        });

        async function _openStudio(targetMode, action = false, viewType = false) {
            if (!targetMode) {
                throw new Error("mode is mandatory");
            }

            const options = {};
            if (targetMode === MODES.EDITOR) {
                let controllerState;
                if (!action) {
                    // systray open
                    const currentController = env.services.action.currentController;
                    if (currentController) {
                        action = currentController.action;
                        viewType = currentController.view.type;
                        controllerState = Object.assign({}, currentController.getLocalState());
                        const { resIds } = currentController.getGlobalState() || {};
                        if (resIds) {
                            controllerState.resIds = resIds;
                        }
                    }
                }
                if (!_isStudioEditable(action)) {
                    throw new NotEditableActionError();
                }
                if (action !== state.editedAction) {
                    options.clearBreadcrumbs = true;
                }
                state.editedAction = action;
                const vtype = viewType || action.views[0][1]; // fallback on first view of action
                state.editedViewType = isViewEditable(vtype) ? vtype : null;
                state.editorTab = "views";
                state.editedControllerState = controllerState || {};
            }
            if (inStudio) {
                options.stackPosition = "replaceCurrentAction";
            }
            state.studioMode = targetMode;
            user.updateContext({ studio: 1 });
            // LPE: we don't manage errors during do action.....
            const res = await env.services.action.doAction("studio", options);
            // force color_scheme light
            if (getCookie("color_scheme") === "dark") {
                // ensure studio is fully loaded
                await delay(0);
                setCookie("color_scheme", "light");
                browser.location.reload();
            }
            return res;
        }

        async function open(mode = false, actionId = false) {
            if (!mode && inStudio) {
                throw new Error("can't already be in studio");
            }
            if (!mode) {
                mode = env.services.home_menu.hasHomeMenu ? MODES.HOME_MENU : MODES.EDITOR;
            }
            let action;
            if (actionId) {
                action = await env.services.action.loadAction(actionId);
            }
            resetViewCompilerCache();
            return _openStudio(mode, action);
        }

        async function leave() {
            if (!inStudio) {
                throw new Error("leave when not in studio???");
            }
            resetViewCompilerCache();
            env.bus.trigger("CLEAR-CACHES");
            const options = {
                stackPosition: "replacePreviousAction", // If target is menu, then replaceCurrent, see comment above why we cannot do this
            };
            let actionId;
            if (state.studioMode === MODES.EDITOR) {
                actionId = state.editedAction.id;
                options.additionalContext = state.editedAction.context;
                options.viewType = state.editedViewType;
                if (state.editedControllerState) {
                    options.props = { resId: state.editedControllerState.currentId };
                }
            } else {
                actionId = "menu";
            }
            user.removeFromContext("studio");
            await env.services.action.doAction(actionId, options);
            // force rendering of the main navbar to allow adaptation of the size
            env.bus.trigger("MENUS:APP-CHANGED");
            state.studioMode = null;
            state.x2mEditorPath = [];
        }

        async function reload(params = {}) {
            resetViewCompilerCache();
            env.bus.trigger("CLEAR-CACHES");
            const action = await env.services.action.loadAction(state.editedAction.id);
            setParams({ action, ...params });
        }

        function toggleHomeMenu() {
            if (!inStudio) {
                throw new Error("is it possible?");
            }
            let targetMode;
            if (state.studioMode === MODES.APP_CREATOR || state.studioMode === MODES.EDITOR) {
                targetMode = MODES.HOME_MENU;
            } else {
                targetMode = MODES.EDITOR;
            }
            const action = targetMode === MODES.EDITOR ? state.editedAction : null;
            if (targetMode === MODES.EDITOR && !action) {
                throw new Error("this button should not be clickable/visible");
            }
            const viewType = targetMode === MODES.EDITOR ? state.editedViewType : null;
            return _openStudio(targetMode, action, viewType);
        }

        function pushState() {
            const hash = { action: "studio" };
            hash[URL_MODE_KEY] = state.studioMode;
            hash[URL_ACTION_KEY] = undefined;
            hash[URL_VIEW_KEY] = undefined;
            hash[URL_TAB_KEY] = undefined;
            if (state.studioMode === MODES.EDITOR) {
                hash[URL_ACTION_KEY] = JSON.stringify(state.editedAction.id);
                hash[URL_VIEW_KEY] = state.editedViewType || undefined;
                hash[URL_TAB_KEY] = state.editorTab;
            }
            if (
                state.editedAction &&
                state.editedAction.context &&
                state.editedAction.context.active_id
            ) {
                hash.active_id = state.editedAction.context.active_id;
            }
            env.services.router.pushState(hash, { replace: true });
        }

        function setParams(params = {}) {
            if ("mode" in params) {
                state.studioMode = params.mode;
            }
            if ("viewType" in params) {
                state.editedViewType = params.viewType || null;
                state.x2mEditorPath = [];
            }
            if ("action" in params) {
                state.editedAction = params.action || null;
            }
            if ("editorTab" in params) {
                state.editorTab = params.editorTab;
                state.x2mEditorPath = [];
                if (!("viewType" in params)) {
                    // clean me
                    state.editedViewType = null;
                }
                if (!("editedReport" in params)) {
                    state.editedReport = null;
                }
            }
            if ("editedReport" in params) {
                state.editedReport = params.editedReport;
            }
            if ("x2mEditorPath" in params) {
                state.x2mEditorPath = params.x2mEditorPath;
            }
            if (state.editorTab !== "reports") {
                state.editedReport = null;
            }
            bus.trigger("UPDATE");
        }
        legacyBus.on("STUDIO_ENTER_X2M", null, (newX2mPath) => {
            const x2mEditorPath = state.x2mEditorPath.slice();
            x2mEditorPath.push(newX2mPath);
            setParams({ x2mEditorPath });
        });

        env.bus.on("ACTION_MANAGER:UI-UPDATED", null, (mode) => {
            if (mode === "new") {
                return;
            }
            const action = _getCurrentAction();
            inStudio = action.tag === "studio";
        });

        const legacyBusTrigger = legacyBus.trigger.bind(legacyBus);
        const busTrigger = bus.trigger.bind(bus);
        function mappedTrigger(...args) {
            legacyBusTrigger(...args);
            busTrigger(...args);
        }
        legacyBus.trigger = mappedTrigger;
        bus.trigger = mappedTrigger;

        return {
            MODES,
            bus,
            isStudioEditable() {
                const action = _getCurrentAction();
                return action ? _isStudioEditable(action) : false;
            },
            open,
            reload,
            pushState,
            leave,
            toggleHomeMenu,
            setParams,
            get ready() {
                return studioProm;
            },
            get mode() {
                return state.studioMode;
            },
            get editedAction() {
                return state.editedAction;
            },
            get editedViewType() {
                return state.editedViewType;
            },
            get editedControllerState() {
                return state.editedControllerState;
            },
            get editedReport() {
                return state.editedReport;
            },
            get editorTab() {
                return state.editorTab;
            },
            get x2mEditorPath() {
                return state.x2mEditorPath;
            },
        };
    },
};

registry.category("services").add("studio", studioService);
