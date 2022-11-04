/** @odoo-module **/

import { voipService } from "@voip/voip_service";
import { registry } from "@web/core/registry";
import { voipLegacyCompatibilityService } from "@voip/js/legacy_compatibility";

registry.category('services').add("voip", voipService);
registry.category('services').add("voip_legacy", voipLegacyCompatibilityService);
