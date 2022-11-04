/** @odoo-module */

import Widget from "web.Widget";
import StandaloneFieldManagerMixin from "web.StandaloneFieldManagerMixin";
import { FieldMany2One } from "web.relational_fields";
import { qweb } from "web.core";

/**
 * This widget is used in to select records from a given model.
 * It uses a FieldMany2One widget.
 */
const StandaloneMany2OneField = Widget.extend(StandaloneFieldManagerMixin, {
    /**
     * @constructor
     */
    init: function (parent, modelName, value, domain, attrs = {}) {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.widget = undefined;
        this.modelName = modelName;
        this.value = value;
        this.domain = domain;
        this.attrs = attrs;
    },
    updateWidgetValue: async function (value) {
        this.value = value;
        await this._createM2OWidget();
        const $content = $(qweb.render("spreadsheet_edition.StandaloneMany2OneField", {}));
        this.$el.empty().append($content);
        this.widget.appendTo($content);
    },
    /**
     * @override
     */
    willStart: async function () {
        await this._super.apply(this, arguments);
        await this._createM2OWidget();
    },
    /**
     * @override
     */
    start: function () {
        const $content = $(qweb.render("spreadsheet_edition.StandaloneMany2OneField", {}));
        this.$el.append($content);
        this.widget.appendTo($content);
        return this._super.apply(this, arguments);
    },

    /**
     * Return the field input
     * @returns {HTMLInputElement}
     */
    getFocusableElement() {
        return this.widget.getFocusableElement()[0];
    },

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _confirmChange: async function () {
        const result = await StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
        this.trigger_up("value-changed", { value: this.widget.value.res_id });
        return result;
    },
    /**
     * Create a record of the correct model and a FieldMany2One linked to this
     * record
     */
    _createM2OWidget: async function () {
        const recordID = await this.model.makeRecord(this.modelName, [
            {
                name: this.modelName,
                relation: this.modelName,
                type: "many2one",
                value: this.value,
                domain: this.domain,
            },
        ]);
        this.widget = new FieldMany2One(this, this.modelName, this.model.get(recordID), {
            mode: "edit",
            attrs: {
                can_create: false,
                can_write: false,
                options: { no_open: true },
                ...this.attrs,
            },
        });
        this._registerWidget(recordID, this.modelName, this.widget);
    },
});
export { StandaloneMany2OneField };
