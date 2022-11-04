/** @odoo-module */

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { ChatterContainer } from '@mail/components/chatter_container/chatter_container';

const { Component } = owl;

/**
 * This widget allows to embed a chatter container in the form view
 * using <widget name="bank_rec_form_chatter" m2oField="related_field_with_chatter"/>
 */
class FormChatterContainer extends Component {}

FormChatterContainer.template = "account_accountant.FormChatterContainer";
FormChatterContainer.props = {
    ...standardWidgetProps,
    m2oField: { type: String }
};
FormChatterContainer.extractProps = ({ attrs }) => ({
    m2oField: attrs.m2oField,
});
FormChatterContainer.components = { ChatterContainer }

registry.category("view_widgets").add("bank_rec_form_chatter", FormChatterContainer);
