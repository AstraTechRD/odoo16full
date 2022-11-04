/* @odoo-module */

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { download } from "@web/core/network/download";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { useModel } from "@web/views/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupView } from "@web/views/view_hook";

const { Component, useRef } = owl;

export class CohortController extends Component {
    setup() {
        this.actionService = useService("action");
        this.model = useModel(this.props.Model, owl.toRaw(this.props.modelParams));

        useSetupView({
            rootRef: useRef("root"),
            getLocalState: () => {
                return { metaData: this.model.metaData };
            },
            getContext: () => this.getContext(),
        });
    }

    getContext() {
        const { measure, interval } = this.model.metaData;
        return { cohort_measure: measure, cohort_interval: interval };
    }

    /**
     * @param {Object} row
     */
    onRowClicked(row) {
        if (row.value === undefined) {
            return;
        }

        const context = Object.assign({}, this.model.searchParams.context);
        const domain = row.domain;
        const views = {};
        for (const [viewId, viewType] of this.env.config.views || []) {
            views[viewType] = viewId;
        }
        function getView(viewType) {
            return [context[`${viewType}_view_id`] || views[viewType] || false, viewType];
        }
        const actionViews = [getView("list"), getView("form")];
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: this.model.metaData.title,
            res_model: this.model.metaData.resModel,
            views: actionViews,
            view_mode: "list",
            target: "current",
            context: context,
            domain: domain,
        });
    }

    /**
     * Export cohort data in Excel file
     */
    async downloadExcel() {
        const {
            title,
            resModel,
            interval,
            measure,
            measures,
            dateStartString,
            dateStopString,
            timeline,
        } = this.model.metaData;
        const { domains } = this.model.searchParams;
        const data = {
            title: title,
            model: resModel,
            interval_string: this.model.intervals[interval].toString(), // intervals are lazy-translated
            measure_string: measures[measure].string,
            date_start_string: dateStartString,
            date_stop_string: dateStopString,
            timeline: timeline,
            rangeDescription: domains[0].description,
            report: this.model.data[0],
            comparisonRangeDescription: domains[1] && domains[1].description,
            comparisonReport: this.model.data[1],
        };
        this.env.services.ui.block();
        try {
            // FIXME: [SAD/JPP] some data seems to be missing from the export in master. (check the python)
            await download({
                url: "/web/cohort/export",
                data: { data: JSON.stringify(data) },
            });
        } finally {
            this.env.services.ui.unblock();
        }
    }

    /**
     * @param {Object} payload
     */
    onDropDownSelected(payload) {
        this.model.updateMetaData(payload);
    }

    /**
     * @param {Object} param0
     * @param {string} param0.measure
     */
    onMeasureSelected({ measure }) {
        this.model.updateMetaData({ measure });
    }
}

CohortController.template = "web_cohort.CohortView";
CohortController.components = { Dropdown, DropdownItem, Layout };
CohortController.props = {
    ...standardViewProps,
    Model: Function,
    modelParams: Object,
    Renderer: Function,
    buttonTemplate: String,
};
