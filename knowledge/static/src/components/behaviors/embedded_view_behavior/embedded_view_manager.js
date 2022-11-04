/** @odoo-module **/

import { CallbackRecorder } from "@web/webclient/actions/action_hook";
import { getDefaultConfig, View } from "@web/views/view";
import { PromptEmbeddedViewNameDialog } from "@knowledge/components/prompt_embedded_view_name_dialog/prompt_embedded_view_name_dialog";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { useService } from "@web/core/utils/hooks";

const {
    Component,
    onMounted,
    onWillStart,
    useSubEnv } = owl;

const EMBEDDED_VIEW_LIMITS = {
    kanban: 20,
    list: 40,
};

/**
 * Wrapper for the embedded view, manage the toolbar and the embedded view props
 */
export class EmbeddedViewManager extends Component {
    setup() {
        // allow access to the SearchModel exported state which contain facets
        this.__getGlobalState__ = new CallbackRecorder();

        this.actionService = useService('action');
        this.dialogService = useService('dialog');

        useOwnDebugContext(); // define a debug context when the developer mode is enable
        const config = {
            ...getDefaultConfig(),
            disableSearchBarAutofocus: true,
        };
        useSubEnv({
            config,
            __getGlobalState__: this.__getGlobalState__,
        });
        onWillStart(this.onWillStart.bind(this));
        onMounted(this.onMounted.bind(this));
    }

    /**
     * Extract the SearchModel state of the embedded view
     *
     * @returns {Object} globalState
     */
    getEmbeddedViewGlobalState() {
        const callbacks = this.__getGlobalState__.callbacks;
        let globalState;
        if (callbacks.length) {
            globalState = callbacks.reduce((res, callback) => {
                return { ...res, ...callback() };
            }, {});
        }
        return { searchModel: globalState && globalState.searchModel };
    }

    /**
     * Recover the action from its parsed state (attrs of the Behavior block)
     * and setup the embedded view props
     */
    onWillStart () {
        const { action, context, viewType } = this.props;
        this.env.config.setDisplayName(action.display_name);
        this.env.config.views = action.views;
        const ViewProps = {
            resModel: action.res_model,
            context: context,
            domain: action.domain || [],
            type: viewType,
            loadIrFilters: true,
            loadActionMenus: true,
            globalState: { searchModel: context.knowledge_search_model_state },
            /**
             * @param {integer} recordId
             */
            selectRecord: recordId => {
                const [formViewId] = this.action.views.find((view) => {
                    return view[1] === 'form';
                }) || [false];
                this.actionService.doAction({
                    type: 'ir.actions.act_window',
                    res_model: action.res_model,
                    views: [[formViewId, 'form']],
                    res_id: recordId,
                });
            },
            createRecord: async () => {
                const [formViewId] = this.action.views.find((view) => {
                    return view[1] === 'form';
                }) || [false];
                this.actionService.doAction({
                    type: 'ir.actions.act_window',
                    res_model: action.res_model,
                    views: [[formViewId, 'form']],
                });
            },
        };
        if (action.search_view_id) {
            ViewProps.searchViewId = action.search_view_id[0];
        }
        if (this.props.viewType in EMBEDDED_VIEW_LIMITS) {
            ViewProps.limit = EMBEDDED_VIEW_LIMITS[this.props.viewType];
        }
        this.EmbeddedView = View;
        this.EmbeddedViewProps = ViewProps;
        this.action = action;
        this.props.onLoadStart();
    }

    onMounted () {
        this.props.onLoadEnd();
    }

    /**
     * Rename an embedded view
     */
    _onRenameBtnClick () {
        this.dialogService.add(PromptEmbeddedViewNameDialog, {
            isNew: false,
            defaultName: this.props.getTitle(),
            viewType: this.props.viewType,
            save: name => {
                this.props.setTitle(name);
            },
            close: () => {}
        });
    }

    /**
     * Open an embedded view (fullscreen)
     */
    _onOpenBtnClick () {
        if (this.action.type !== "ir.actions.act_window") {
            throw new Error('Can not open the view: The action is not an "ir.actions.act_window"');
        }
        this.action.globalState = this.getEmbeddedViewGlobalState();
        this.actionService.doAction(this.action, {
            viewType: this.props.viewType,
        });
    }
}

EmbeddedViewManager.template = 'knowledge.EmbeddedViewManager';
EmbeddedViewManager.props = {
    el: { type: HTMLElement },
    action: { type: Object },
    context: { type: Object },
    viewType: { type: String },
    onLoadStart: { type: Function },
    onLoadEnd: { type: Function },
    setTitle: { type: Function },
    getTitle: { type: Function },
    readonly: { type: Boolean },
};
