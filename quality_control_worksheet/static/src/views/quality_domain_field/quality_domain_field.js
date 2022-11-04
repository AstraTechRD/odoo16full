/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DomainField } from '@web/views/fields/domain/domain_field';


export class QualityDomainField extends DomainField {}

QualityDomainField.template = 'quality_control_worksheet.QualityDomainField';
registry.category("fields").add("quality_domain_field", QualityDomainField);