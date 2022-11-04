/** @odoo-module **/

import { FloatField } from '@web/views/fields/float/float_field';
import { registry } from '@web/core/registry';

export class MrpPlmUpdateQty extends FloatField {}

MrpPlmUpdateQty.displayName = "MRP PLM Update Quantity"
MrpPlmUpdateQty.template = "mrp_plm.UpdateQty"

registry.category('fields').add('plm_upd_qty', MrpPlmUpdateQty);