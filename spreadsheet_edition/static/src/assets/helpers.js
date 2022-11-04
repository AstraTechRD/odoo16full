/** @odoo-module */

import { _t } from "@web/core/l10n/translation";

/**
 * Remove user specific info from the context
 * @param {Object} context
 * @returns {Object}
 */
 export function removeContextUserInfo(context) {
    context = { ...context };
    delete context.allowed_company_ids;
    delete context.tz;
    delete context.lang;
    delete context.uid;
    return context;
}

export const PERIODS = {
    day: _t("Day"),
    week: _t("Week"),
    month: _t("Month"),
    quarter: _t("Quarter"),
    year: _t("Year"),
};
