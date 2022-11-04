/** @odoo-module */

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

import { formView } from "@web/views/form/form_view";
import { UpdateDeviceAccountControllerMixin } from "web_mobile.mixins";
import { Record, RelationalModel } from "@web/views/basic_relational_model";

export class ResUsersPreferenceRecord extends Record {}
export class ResUsersPreferenceModel extends RelationalModel {}
ResUsersPreferenceModel.Record = ResUsersPreferenceRecord;

patch(
    ResUsersPreferenceRecord.prototype,
    "res_users_controller_mobile_mixin",
    UpdateDeviceAccountControllerMixin
);

registry.category("views").add("res_users_preferences_form", {
    ...formView,
    Model: ResUsersPreferenceModel,
});
