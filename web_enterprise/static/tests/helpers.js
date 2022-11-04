/** @odoo-module */

import { createWebClient } from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";
import { legacyServiceProvider } from "@web_enterprise/legacy/legacy_service_provider";
import { WebClientEnterprise } from "@web_enterprise/webclient/webclient";

export function createEnterpriseWebClient(params) {
    params.WebClientClass = WebClientEnterprise;
    registry.category("services").add("enterprise_legacy_service_provider", legacyServiceProvider);
    return createWebClient(params);
}
