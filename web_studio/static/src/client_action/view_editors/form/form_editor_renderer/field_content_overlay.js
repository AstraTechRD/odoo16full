/** @odoo-module */
import { _lt } from "@web/core/l10n/translation";

const { Component, xml } = owl;
/*
 * Injected in the Field.js template
 * Allows to overlay the Field's Component widget to prompt
 * for editing a x2many subview
 */
export class FieldContentOverlay extends Component {}
FieldContentOverlay.translateViewType = {
    list: _lt("List"),
    form: _lt("Form"),
};
FieldContentOverlay.template = xml`
  <div class="position-relative">
    <t t-slot="default" />
    <div class="o-web-studio-edit-x2manys-buttons w-100 h-100 d-flex justify-content-center gap-3 position-absolute start-0 top-0 opacity-75 bg-dark" t-if="props.displayOverlay" style="z-index: 1000;">
        <button class="btn btn-primary btn-secondary o_web_studio_editX2Many align-self-center"
        t-foreach="['list', 'form']" t-as="vType" t-key="vType"
        t-on-click="() => props.onEditViewType(vType)"
        t-att-data-type="vType">
        Edit <t t-esc="constructor.translateViewType[vType]" /> view
        </button>
    </div> 
  </div>`;
