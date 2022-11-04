/* @odoo-module */

import { registry } from "@web/core/registry";
import { CohortController } from "./cohort_controller";
import { CohortRenderer } from "./cohort_renderer";
import { CohortArchParser } from "./cohort_arch_parser";
import { CohortModel } from "./cohort_model";

const cohortView = {
    type: "cohort",
    display_name: "Cohort",
    icon: "oi oi-view-cohort",
    multiRecord: true,
    buttonTemplate: "web_cohort.CohortView.Buttons",
    searchMenuTypes: ["filter", "comparison", "favorite"],
    Model: CohortModel,
    ArchParser: CohortArchParser,
    Controller: CohortController,
    Renderer: CohortRenderer,

    props: (genericProps, view) => {
        let modelParams;
        if (genericProps.state) {
            modelParams = genericProps.state.metaData;
        } else {
            const { arch, fields, resModel } = genericProps;
            const { ArchParser } = view;
            const archInfo = new ArchParser().parse(arch, fields);
            modelParams = {
                dateStart: archInfo.dateStart,
                dateStartString: archInfo.dateStartString,
                dateStop: archInfo.dateStop,
                dateStopString: archInfo.dateStopString,
                fieldAttrs: archInfo.fieldAttrs,
                fields: fields,
                interval: archInfo.interval,
                measure: archInfo.measure,
                mode: archInfo.mode,
                resModel: resModel,
                timeline: archInfo.timeline,
                title: archInfo.title,
            };
        }

        return {
            ...genericProps,
            modelParams,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
        };
    },
};

registry.category("views").add("cohort", cohortView);
