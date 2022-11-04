/* @odoo-module */

import { XMLParser } from "@web/core/utils/xml";
import { _t } from "@web/core/l10n/translation";
import { INTERVALS, MODES, TIMELINES } from "./cohort_model";
import { sprintf } from "@web/core/utils/strings";

export class CohortArchParser extends XMLParser {
    parse(arch, fields) {
        const archInfo = {
            fieldAttrs: {},
        };
        this.visitXML(arch, (node) => {
            switch (node.tagName) {
                case "cohort": {
                    const title = node.getAttribute("string");
                    if (title) {
                        archInfo.title = title;
                    }
                    const dateStart = node.getAttribute("date_start");
                    if (dateStart) {
                        archInfo.dateStart = dateStart;
                        archInfo.dateStartString = fields[dateStart].string;
                    } else {
                        throw new Error(_t('Cohort view has not defined "date_start" attribute.'));
                    }
                    const dateStop = node.getAttribute("date_stop");
                    if (dateStop) {
                        archInfo.dateStop = dateStop;
                        archInfo.dateStopString = fields[dateStop].string;
                    } else {
                        throw new Error(_t('Cohort view has not defined "date_stop" attribute.'));
                    }
                    const mode = node.getAttribute("mode") || "retention";
                    if (mode && MODES.includes(mode)) {
                        archInfo.mode = mode;
                    } else {
                        throw new Error(
                            sprintf(
                                "The argument %s is not a valid mode. Here are the modes: %s",
                                mode,
                                MODES
                            )
                        );
                    }
                    const timeline = node.getAttribute("timeline") || "forward";
                    if (timeline && TIMELINES.includes(timeline)) {
                        archInfo.timeline = timeline;
                    } else {
                        throw new Error(
                            sprintf(
                                "The argument %s is not a valid timeline. Here are the timelines: %s",
                                timeline,
                                TIMELINES
                            )
                        );
                    }
                    archInfo.measure = node.getAttribute("measure") || "__count";
                    const interval = node.getAttribute("interval") || "day";
                    if (interval && interval in INTERVALS) {
                        archInfo.interval = interval;
                    } else {
                        throw new Error(
                            sprintf(
                                "The argument %s is not a valid interval. Here are the intervals: %s",
                                interval,
                                INTERVALS
                            )
                        );
                    }
                    break;
                }
                case "field": {
                    const fieldName = node.getAttribute("name"); // exists (rng validation)

                    archInfo.fieldAttrs[fieldName] = {};
                    if (node.hasAttribute("string")) {
                        archInfo.fieldAttrs[fieldName].string = node.getAttribute("string");
                    }
                    const modifiers = JSON.parse(node.getAttribute("modifiers") || "{}");
                    if (modifiers.invisible === true) {
                        archInfo.fieldAttrs[fieldName].isInvisible = true;
                        break;
                    }
                }
            }
        });
        return archInfo;
    }
}
