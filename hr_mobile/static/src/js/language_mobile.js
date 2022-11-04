/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { UpdateDeviceAccountControllerMixin } from "web_mobile.mixins";
import { EmployeeProfileRecord } from "@hr/views/profile_form_view";

patch(
    EmployeeProfileRecord.prototype,
    "employee_profile_include",
    UpdateDeviceAccountControllerMixin
);
