/** @odoo-module **/

import { MrpMpsControlPanel } from '../search/mrp_mps_control_panel';
import { MrpMpsSearchModel } from '../search/mrp_mps_search_model';
import MpsLineComponent from '@mrp_mps/components/line';
import { MasterProductionScheduleModel } from '@mrp_mps/models/master_production_schedule_model';
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { getDefaultConfig } from "@web/views/view";
import { usePager } from "@web/search/pager_hook";
import { CallbackRecorder, useSetupAction } from "@web/webclient/actions/action_hook";

const { Component, onWillStart, useSubEnv, useChildSubEnv } = owl;

class MainComponent extends Component {
    //--------------------------------------------------------------------------
    // Lifecycle
    //--------------------------------------------------------------------------
    setup() {
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.viewService = useService("view");

        const { orm, action, dialog } = this;
        this.model = new MasterProductionScheduleModel(this.props, { orm, action, dialog });

        useSubEnv({
            manufacturingPeriods: [],
            model: this.model,
            __getContext__: new CallbackRecorder(),
            __getOrderBy__: new CallbackRecorder(),
            config: {
                ...getDefaultConfig(),
                offset: 0,
                limit: 20,
                mpsImportRecords: true,
            },
        });

        useSetupAction({
            getContext: () => {
                return this.props.action.context;
            },
        });

        this.SearchModel = new MrpMpsSearchModel(this.env, {
            user: useService("user"),
            orm: this.orm,
            view: useService("view"),
        });
        useChildSubEnv({
            searchModel: this.SearchModel,
        });

        useBus(this.SearchModel, "update", () => {
            this.env.config.offset = 0;
            this.env.config.limit = 20;
            this.model.load(this.SearchModel.domain, this.env.config.offset, this.env.config.limit);
        });

        onWillStart(async () => {
            this.env.config.setDisplayName(this.env._t("Master Production Schedule"));
            const views = await this.viewService.loadViews(
                {
                    resModel: "mrp.production.schedule",
                    context: this.props.action.context,
                    views: [[false, "search"]],
                }
            );
            await this.SearchModel.load({
                resModel: "mrp.production.schedule",
                context: this.props.action.context,
                orderBy: "id",
                searchMenuTypes: ['filter', 'favorite'],
                searchViewArch: views.views.search.arch,
                searchViewId: views.views.search.id,
                searchViewFields: views.fields,
                loadIrFilters: true
            });
            this.model.on('update', this, () => this.render(true));
            const domain = this.props.action.domain || this.SearchModel.domain;
            await this.model.load(domain, this.env.config.offset, this.env.config.limit);
        });

        usePager(() => {
            return {
                offset: this.env.config.offset,
                limit: this.env.config.limit,
                total: this.model.data.count,
                onUpdate: async ({ offset, limit }) => {
                    this.env.config.offset = offset;
                    this.env.config.limit = limit;
                    this.model.load(this.SearchModel.domain, offset, limit);
                    this.render(true);
                },
            };
        });
    }

    get lines() {
        return this.model.data.production_schedule_ids;
    }

    get manufacturingPeriods() {
        return this.model.data.dates;
    }

    get groups() {
        return this.model.data.groups[0];
    }

    get isSelected() {
        return this.model.selectedRecords.size === this.lines.length;
    }

    toggleSelection() {
        this.model.toggleSelection();
    }

}

MainComponent.template = 'mrp_mps.mrp_mps';
MainComponent.components = {
    MrpMpsControlPanel,
    MpsLineComponent,
    CheckBox,
};

registry.category("actions").add("mrp_mps_client_action", MainComponent);

export default MainComponent;
