odoo.define('web_studio.ViewEditorManager', function (require) {
"use strict";

const { ComponentWrapper, WidgetAdapterMixin } = require('web.OwlCompatibility');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var framework = require('web.framework');
var session = require('web.session');
var view_registry = require('web.view_registry');
const { processArch } = require("@web/legacy/legacy_load_views");
const KanbanView = require("web.KanbanView");
const ListView = require("web.ListView");

var AbstractEditorManager = require('web_studio.AbstractEditorManager');
var bus = require('web_studio.bus');
var EditorMixin = require('web_studio.EditorMixin');
var EditorMixinOwl = require('web_studio.EditorMixinOwl');

var KanbanEditor = require('web_studio.KanbanEditor');
var ListEditor = require('web_studio.ListEditor');
var SearchEditor = require('web_studio.SearchEditor');
var SearchRenderer = require('web_studio.SearchRenderer');

var FieldSelectorDialog = require('web_studio.FieldSelectorDialog');
var NewButtonBoxDialog = require('web_studio.NewButtonBoxDialog');
var NewFieldDialog = require('web_studio.NewFieldDialog');
var utils = require('web_studio.utils');
const { ViewEditorSidebar } = require('@web_studio/legacy/js/views/view_editor_sidebar');
const { isComponent } = require('web.utils');
const viewUtils = require("web.viewUtils");

const { computeReportMeasures } = require("@web/views/utils");
const { evaluateExpr } = require("@web/core/py_js/py");
const { registry } = require("@web/core/registry");
const { SearchModel } = require("@web/search/search_model");
const { StudioView } = require("@web_studio/client_action/studio_view");

const wrapperRegistry = registry.category("wowl_editors_wrappers");
const editorsRegistry = registry.category("studio_editors");
const viewRegistry = registry.category("views");

const { resetViewCompilerCache } = require("@web/views/view_compiler");
const { extendEnv } = require('@web_studio/client_action/view_editors/utils')
const { getNodesFromXpath, getLegacyNode, xpathToLegacyXpathInfo, serializeXmlToString, parseStringToXml } = require('@web_studio/client_action/view_editors/xml_utils')

const CONVERTED_VIEWS = [
    "calendar",
    "cohort",
    "dashboard",
    "graph",
    "map",
    "pivot",
    "form",
];

var _t = core._t;
var QWeb = core.qweb;

var Editors = {
    kanban: KanbanEditor,
    list: ListEditor,
    search: SearchEditor,
};

class EditorWrapper extends ComponentWrapper {
    handleDrop() {
        return this.componentRef.comp &&
            this.componentRef.comp.handleDrop(...arguments);
    }
    highlightNearestHook() {
        return this.componentRef.comp &&
            this.componentRef.comp.highlightNearestHook(...arguments);
    }
    setSelectable() {
        return this.componentRef.comp &&
            this.componentRef.comp.setSelectable(...arguments);
    }
    unselectedElements() {
        return this.componentRef.comp &&
            this.componentRef.comp.unselectedElements(...arguments);
    }
}

class GenericWowlEditor extends EditorWrapper {
    setup() {
        super.setup();
        this.state = {
            getFieldNames: () => [],
        }
    }
    getLocalState() {}
    setLocalState() {}
    unselectedElements() {}
    handleDrop() {}
    highlightNearestHook() {}
    setSelectable() {}
}

function getX2MFullXpath(x2mPathsInfos) {
    return x2mPathsInfos.map(info => info.xpath).join("/");
}

function getSubArch(mainArch, xpath) {
    const nodes = getNodesFromXpath(xpath, parseStringToXml(mainArch));
    return serializeXmlToString(nodes[0]);
}

async function wowlCreateInlineView(env, { subViewType, viewId, fullXpath, subViewRef, resModel, fieldName }) {
    const { rpc, user } = env.services;
    subViewType = subViewType === 'list' ? 'tree' : subViewType;
    // We build the correct xpath if we are editing a 'sub' subview
    // Use specific view if available in context
    // We write views in the base language to make sure we do it on the source term field
    // of ir.ui.view
    const context = { ...user.context, lang: false };
    if (subViewRef) {
        context[`${subViewType}_view_ref`] = subViewRef;
    }

    const studioViewArch = await rpc('/web_studio/create_inline_view', {
        model: resModel,
        view_id: viewId,
        field_name: fieldName,
        subview_type: subViewType,
        subview_xpath: fullXpath,
        context,
    });
    return studioViewArch;
}

var ViewEditorManager = AbstractEditorManager.extend(WidgetAdapterMixin, {
    custom_events: _.extend({}, AbstractEditorManager.prototype.custom_events, {
        approval_archive: '_onApprovalArchive',
        approval_change: '_onApprovalChange',
        approval_condition: '_onApprovalCondition',
        approval_group_change: '_onApprovalGroupChange',
        approval_responsible_change: '_onApprovalResponsibleChange',
        approval_new_rule: '_onApprovalNewRule',
        default_value_change: '_onDefaultValueChange',
        email_alias_change: '_onEmailAliasChange',
        field_edition: '_onFieldEdition',
        field_renamed: '_onFieldRenamed',
        open_defaults: '_onOpenDefaults',
        open_field_form: '_onOpenFieldForm',
        open_record_form_view: '_onOpenRecordFormView',
        toggle_form_invisible: '_onShowInvisibleToggled',
    }),
    /**
     * The init always takes the main view's descriptions as parameters.
     * If we are editing a nested x2m field, the ViewManager's properties are changed
     * in order to target the right field and the right view.
     *
     * @override
     * @param {Widget} parent
     * @param {Object} params
     * @param {Object} params.action
     * @param {Object} params.fields_view
     * @param {string} params.viewType
     * @param {Object} [params.chatter_allowed]
     * @param {String} [params.controllerState]
     * @param {Object} [params.studio_view_id]
     * @param {Object} [params.studio_view_arch]
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.wowlEnv = params.wowlEnv;
        this.viewDescriptions = params.viewDescriptions;

        const { resId, resIds } = params.controllerState || {};
        this.resId = resId;
        this.resIds = resIds;

        this.action = params.action;

        this.fields_view = params.fields_view;
        this.fields = this._processFields(this.viewDescriptions.fields);

        this.model_name = this.fields_view.model;
        this.view_type = params.viewType;
        this.mainViewType = this.view_type;
        this.view_id = this.fields_view.view_id;

        this.studio_view_id = params.studio_view_id;
        this.studio_view_arch = params.studio_view_arch;

        this.isEditingX2m = params.x2mEditorPath && params.x2mEditorPath.length;
        if (this.isEditingX2m) {
            this.x2mEditorPath = params.x2mEditorPath;
            this.chatter_allowed = false;

            const currentX2m = this.x2mEditorPath[this.x2mEditorPath.length - 1];
            this.currentX2m = currentX2m;

            this.x2mField = currentX2m.x2mField;
            this.x2mViewType = currentX2m.x2mViewType;
            this.x2mModel = currentX2m.x2mModel;

            this.view_type = this.x2mViewType;
            this.x2mViewParams = currentX2m.x2mViewParams;
        } else {
            this.chatter_allowed = params.chatter_allowed || false;
            this.controllerState = params.controllerState;
        }

        this.renamingAllowedFields = []; // those fields can be renamed

        this.expr_attrs = {
            'field': ['name'],
            'label': ['for'],
            'page': ['name'],
            'group': ['name'],
            'div': ['name'],
            'filter': ['name'],
            'button': ['name'],
        };
    },
    /**
     * @override
     */
    start: async function () {
        const _super = this._super;
        if (this.isEditingX2m) {
            let fieldsView = this._getX2mFieldsView(this.fields_view);

            if (!fieldsView || fieldsView.name) {
                fieldsView = await this._createInlineView(this.x2mViewType, this.x2mField)
                fieldsView = this._getX2mFieldsView(fieldsView);
            }
            this.fields_view = fieldsView;
            this.fields = await this._getProcessedX2mFields();
        }
        return _super.apply(this, arguments);
    },

    destroy() {
        WidgetAdapterMixin.destroy.call(this);
        this._super();
    },

    on_attach_callback() {
        WidgetAdapterMixin.on_attach_callback.call(this);
        this._super();
    },

    on_detach_callback() {
        WidgetAdapterMixin.on_detach_callback.call(this);
        this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object} options
     * @returns {Promise}
     */
    updateEditor: function (options) {
        var self = this;
        var rendererScrollTop = this.$el.scrollTop();
        var localState = false;
        if (this.editor && this.editor.getLocalState) {
            localState = this.editor.getLocalState();
        }
        var oldEditor = this.editor;

        return this._instantiateEditor(options).then(function (editor) {
            var fragment = document.createDocumentFragment();
            let prom = undefined;
            if (editor instanceof ComponentWrapper) {
                prom = editor.mount(fragment);
            } else {
                prom = editor.appendTo(fragment);
            }
            return prom.then(function () {
                dom.append(self.$('.o_web_studio_view_renderer'), [fragment], {
                    in_DOM: self.isInDOM,
                    callbacks: [{ widget: editor }],
                });
                self.editor = editor;
                oldEditor.destroy();

                // restore previous state
                self.$el.scrollTop(rendererScrollTop);
                if (localState) {
                    self.editor.setLocalState(localState);
                }
            }).guardedCatch(function (e) {
                self.trigger_up('studio_error', {error: 'view_rendering'});
                self._undo(null, true);
            });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} data
     */
    _addAvatarImage: function (data) {
        this._do({
            type: 'avatar_image',
            field: data.field,
        });
    },
    /**
     * Enable approval for a <button> node as well as all other nodes of the
     * same type and the same name in the view; this is done server-side.
     * @private
     * @param {Object} data
     */
    _addApproval: async function (data) {
        const attrs = data.node.attrs;
        // enabling approval on node
        // need to enable it on all similar nodes silently in a single op
        await this._do({
            type: 'enable_approval',
            model: this.model_name,
            btn_type: attrs.type,
            btn_name: attrs.name,
            view_id: this.view_id,
            enable: data.enable,
        })
    },
    /**
     * @private
     * @param {String} type
     */
    _addButton: function (data) {
        var modelName = this.x2mModel ? this.x2mModel : this.model_name;
        var dialog = new NewButtonBoxDialog(this, modelName).open();
        dialog.on('saved', this, function (result) {
            if (data.add_buttonbox) {
                this.operations.push({type: 'buttonbox'});
            }
            this._do({
                type: data.type,
                target: {
                    tag: 'div',
                    attrs: {
                        class: 'oe_button_box',
                    }
                },
                position: 'inside',
                node: {
                    tag: 'button',
                    field: result.field_id,
                    string: result.string,
                    attrs: {
                        class: 'oe_stat_button',
                        icon: result.icon,
                    }
                },
            });
        });
    },
    /**
     * @private
     * @param {Object} data
     */
    _addChatter: function (data) {
        this._do({
            type: 'chatter',
            model: this.model_name,
            remove_activity_ids: data.remove_activity_ids,
            remove_message_ids: data.remove_message_ids,
            remove_follower_ids: data.remove_follower_ids,
        });
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {String} position
     * @param {String} tag
     */
    _addElement: function (type, node, xpath_info, position, tag) {
        this._do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: position,
            node: {
                tag: tag,
                attrs: {
                    name: 'studio_' + tag + '_' + utils.randomString(5),
                }
            },
        });
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} field_description
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {String} position
     * @param {Object} new_attrs
     * @param {Object} data
     */
    _addField: function (type, field_description, node, xpath_info, position, new_attrs, data) {
        var self = this;
        var def_field_values;
        var dialog;

        var openCurrencyCreationDialog = function (relatedCurrency, resolve) {
            var msg = _t("In order to use a monetary field, you need a currency field on the model. " +
                "Do you want to create a currency field first? You can make this field invisible afterwards.");
            return Dialog.confirm(this, msg, {
                confirm_callback: function () {
                    new_attrs = {};
                    // modifies the current operation in place to create a
                    // currency field instead
                    field_description = {
                        default_value: session.company_currency_id,
                        field_description: 'Currency',
                        model_name: modelName,
                        name: 'x_currency_id',
                        relation: 'res.currency',
                        type: 'many2one',
                    };
                    if (relatedCurrency) {
                        field_description.related = relatedCurrency;
                    }
                    resolve();
                },
            });
        };

        // The field doesn't exist: field_description is the definition of the new field.
        // No need to have field_description of an existing field
        if (field_description) {
            var modelName = this.x2mModel ? this.x2mModel : this.model_name;
            // "extend" avoids having the same reference in "this.operations"
            // We can thus modify it without editing previous existing operations
            field_description = _.extend({}, field_description, {
                name: `x_studio_${field_description.type}_field_${utils.randomString(5)}`,
                model_name: modelName,
            });
            // Fields with requirements
            if (field_description.type === 'selection' && new_attrs.widget === 'priority') {
                // should not be translated at the creation
                field_description.selection = [
                    ['0', "Normal"],
                    ['1', "Low"],
                    ['2', "High"],
                    ['3', "Very High"],
                ];
            } else if (field_description.special === 'lines') {
                // there's nothing to do, the operation will be fully handled server-side
            } else if (_.contains(['selection', 'one2many', 'many2one', 'many2many', 'related'], field_description.type)) {
                def_field_values = new Promise(function (resolve, reject) {
                    var prom;
                    if (field_description.type === 'one2many') {
                        // check for existing m2o fields for current model
                        var modelName = self.x2mModel ? self.x2mModel : self.model_name;
                        prom = self._rpc({
                            model:"ir.model.fields",
                            method: "search_count",
                            args: [[['relation', '=', modelName], ['ttype', '=', 'many2one']]],
                        });
                    } else {
                        prom = Promise.resolve(true);
                    }
                    prom.then(function (openFieldDialog) {
                        if (!openFieldDialog) {
                            // In case of o2m fields, if there's no m2o field available, display a warning instead
                            var $message = $(QWeb.render('web_studio.FieldOne2manyWarning'));
                            dialog = Dialog.alert(self, '', {
                                $content: $('<main/>', {
                                    role: 'alert',
                                    html: $message,
                                }),
                                title: _t("No related many2one fields found"),
                            });
                            dialog.on('closed', self, function () {
                                reject();
                            });
                        } else {
                            // open dialog to precise the required fields for this field
                            dialog = new NewFieldDialog(self, modelName, field_description, _.filter(self.fields, {type: 'many2one'})).open();
                            dialog.on('field_default_values_saved', self, function (values) {
                                if (values.related && values.type === 'monetary') {
                                    if (self._hasCurrencyField()) {
                                        resolve(values);
                                        dialog.close();
                                    } else {
                                        var relatedCurrency = values._currency;
                                        delete values._currency;
                                        var currencyDialog = openCurrencyCreationDialog(relatedCurrency, resolve);
                                        currencyDialog.on('closed', self, function () {
                                            dialog.close();
                                        });
                                    }
                                } else {
                                    resolve(values);
                                    dialog.close();
                                }
                            });
                            dialog.on('closed', self, function () {
                                reject();
                            });
                        }
                    });
                });
            } else if (field_description.type === 'monetary') {
                def_field_values = new Promise(function (resolve, reject) {
                    if (self._hasCurrencyField()) {
                        resolve();
                    } else {
                        dialog = openCurrencyCreationDialog(null, resolve);
                        dialog.on('closed', self, function () {
                            reject();
                        });
                    }
                });
            } else if (field_description.type === 'integer') {
                field_description.default_value = '0'
            }
        }
        // When the field values is selected, close the dialog and update the view
        Promise.resolve(def_field_values).then(function (values) {
            framework.blockUI();
            if (field_description) {
                self.renamingAllowedFields.push(field_description.name);
            }
            if (data.add_statusbar) {
                self.operations.push({type: 'statusbar'});
            }
            var target = data.target || {
                tag: node.tag,
                attrs: _.pick(node.attrs, self.expr_attrs[node.tag]),
                xpath_info: xpath_info,
            };
            self._do({
                type: type,
                target: target,
                position: position,
                node: {
                    tag: 'field',
                    attrs: new_attrs,
                    field_description: _.extend(field_description, values),
                },
            }).then(function () {
                framework.unblockUI();
                if (self.editor.selectField && field_description) {
                    self.editor.selectField(field_description.name);
                }
            }).guardedCatch(framework.unblockUI);
        }).guardedCatch(function () {
            self.updateEditor();
        });
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {String} position
     * @param {Object} new_attrs
     */
    _addFilter: function (type, node, xpath_info, position, new_attrs) {
        this._do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: position,
            node: {
                tag: 'filter',
                attrs: new_attrs,
            },
        });
    },
    /**
     * @private
     */
    _addKanbanDropdown: function () {
        this._do({
            type: 'kanban_dropdown',
        });
    },
    /**
     * @private
     * @param {string} type
     */
    _editKanbanCover: function (type) {
        if (type === 'kanban_set_cover') {
            var compatibleFields = _.pick(this.fields, function (field) {
               return field.type === "many2one" && field.relation === "ir.attachment";
            });
            var dialog = new FieldSelectorDialog(this, compatibleFields, true).open();
            dialog.on('confirm', this, function (field) {
                this._do({
                    type: type,
                    field: field,
                });
            });
        }
        if (type === 'remove') {
            var fieldToRemove = _.pick(this.view.fieldsInfo[this.view_type], function (field) {
                return field.widget === "attachment_image";
            });

            this._do({
                type: type,
                target: {
                    tag: 'field',
                    attrs: {name: _.keys(fieldToRemove)[0]},
                    extra_nodes: [{
                        tag: "a",
                        attrs: {
                            type: 'set_cover',
                        },
                    }],
                },
            });
        }
    },
    /**
     * @private
     * @param {Object} data
     */
    _addKanbanPriority: function (data) {
        this._do({
            type: 'kanban_priority',
            field: data.field,
        });
    },
    /**
     * @private
     * @param {Object} data
     */
    _addKanbanImage: function (data) {
        this._do({
            type: 'kanban_image',
            field: data.field,
        });
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {String} position
     */
    _addPage: function (type, node, xpath_info, position) {
        this._do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: position,
            node: {
                tag: 'page',
                attrs: {
                    string: 'New Page',
                    name: 'studio_page_' + utils.randomString(5),
                }
            },
        });
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {String} position
     */
    _addSeparator: function (type, node, xpath_info, position) {
        this._do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: position,
            node: {
                tag: 'separator',
                attrs: {
                    name: 'studio_separator_' + utils.randomString(5),
                },
            },
        });
    },
    /**
     * @private
     * @param {string} type operation type
     * @param {integer[]} fieldIDs
     */
    _changeMapPopupFields: function (type, fieldIDs) {
        this._do({
            type: 'map_popup_fields',
            target: {
                operation_type: type,
                field_ids: fieldIDs,
            }
        });
    },
    /**
     * @private
     * @param {string} type operation type
     * @param {integer[]} fieldIDs
     */
    _changePivotMeasuresFields(type, fieldIDs) {
        framework.blockUI();
        this._do({
            type: 'pivot_measures_fields',
            target: {
                operation_type: type,
                field_ids: fieldIDs,
            }
        }).finally(framework.unblockUI);
    },
    /**
     * @private
     * @param {string} type operation type
     * @param {object} data
     */
    _changeGraphPivotGroupbysFields(type, data) {
        framework.blockUI();
        this._do({
            type: 'graph_pivot_groupbys_fields',
            target: {
                operation_type: data.options.operationType,
                field_names: data.options.name,
                old_field_names: data.options.oldname,
                view_type: data.options.viewType,
                field_type: data.options.type,
            }
        }).finally(framework.unblockUI);
    },
    /**
     * @override
     */
    _applyChangeHandling: async function (result, opID) {
        var self = this;
        var prom = Promise.resolve();

        const { models, studio_view_id, views } = result;

        if (!views) {
            // the operation can't be applied
            this.trigger_up('studio_error', {error: 'wrong_xpath'});
            return this._undo(opID, true).then(function () {
                return Promise.reject();
            });
        }


        // the studio_view could have been created at the first edition so
        // studio_view_id must be updated (but /web_studio/edit_view_arch
        // doesn't return the view id)
        if (studio_view_id) {
            this.studio_view_id = studio_view_id;
        }

        const viewType = this.mainViewType;
        const view = views[viewType];
        const { arch, viewFields } = processArch(view.arch, viewType, this.model_name, models);

        // NOTE: fields & fields_view are from the base model here.
        // fields will be updated accordingly if editing a x2m (see
        // @_setX2mParameters).
        this.fields = this._processFields(models[this.model_name]);
        this.viewDescriptions.views[viewType].arch = view.arch;
        this.viewDescriptions.relatedModels = models; // add names (see _processFields)?
        this.viewDescriptions.fields = this.fields;

        this.fields_view = {
            arch,
            fields: this.fields,
            viewFields,
            model: view.model,
            type: viewType,
            view_id: view.id,
        };

        if (this.isEditingX2m) {
            this.fields_view = this._getX2mFieldsView(this.fields_view);
            this.fields = await this._getProcessedX2mFields();
        }

        return prom.then(self.updateEditor.bind(self));
    },
    /**
     * Find a currency field on the current model ; a monetary field can not be
     * added if such a field does not exist on the model.
     *
     * @private
     * @return {boolean} the presence of a currency field
     */
    _hasCurrencyField: function () {
        var currencyField = _.find(this.fields, function (field) {
            return field.type === 'many2one' && field.relation === 'res.currency' &&
                (field.name === 'currency_id' || field.name === 'x_currency_id');
        });
        return !!currencyField;
    },
    /**
     * @override
     * @param {Object} [lastOp]
     */
    _cleanOperationsStack: function (lastOp) {
        // As the studio view arch is stored in this widget, if this view
        // is updated directly with the XML editor, the arch should be updated.
        // The operations may not have any sense anymore so they are dropped.
        if (lastOp && lastOp.view_id === this.studio_view_id) {
            this.studio_view_arch = lastOp.new_arch;
            this._super.apply(this, arguments);
        }
    },
    /**
     * Makes a RPC to modify the studio view in order to add the x2m view
     * inline. This is done to avoid modifying the x2m default view.
     *
     * @private
     * @param {string} type
     * @param {string} field_name
     * @return {Promise}
     */
    _createInlineView: async function (type, field_name) {
        var subviewType = type === 'list' ? 'tree' : type;
        // We build the correct xpath if we are editing a 'sub' subview
        var subviewXpath = this._getSubviewXpath(this.x2mEditorPath.slice(0, -1));
        var context = _.extend({}, session.user_context, {lang: false});
        // Use specific view if available in context
        var specific_view = this.x2mViewParams.context[subviewType+'_view_ref'];
        if (specific_view) {
            context[subviewType+'_view_ref'] = specific_view;
        }
        const studioViewArch = await this._rpc({
            route: '/web_studio/create_inline_view',
            params: {
                model: this.x2mModel,
                view_id: this.view_id,
                field_name: field_name,
                subview_type: subviewType,
                subview_xpath: subviewXpath,
                // We write views in the base language to make sure we do it on the source term field
                // of ir.ui.view
                context: context,
            },
        });

        this.operations = [];
        this.studio_view_arch = studioViewArch;

        const viewInfo = await this.loadViews(
            this.model_name,
            this.currentX2m.x2mViewContext || {},
            [[this.view_id, this.mainViewType]]
        );

        return viewInfo[this.mainViewType];
    },
    /**
     * @override
     */
    _do: function (op) {
        // If we are editing an x2m field, we specify the xpath needed in front
        // of the one generated by the default route.
        if (this.x2mField && op.target) {
            this._setSubViewXPath(op);
        }

        return this._super.apply(this, arguments);
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {Object} new_attrs
     */
    _editElementAttributes: function (type, node, xpath_info, new_attrs) {
        var newOp = {
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: 'attributes',
            node: node,
            new_attrs: new_attrs,
        };
        if (node.tag === 'field' && new_attrs.string &&
            _.contains(this.renamingAllowedFields, node.attrs.name)) {
            if (this.x2mField) {
                this._setSubViewXPath(newOp);
            }
            this.operations.push(newOp);

            // find a new name that doesn't exist yet, acording to the label
            var baseName = 'x_studio_' + this._slugify(new_attrs.string);
            var newName = baseName;
            var index = 1;
            while (newName in this.fields) {
                newName = baseName + '_' + index;
                index++;
            }

            this._renameField(node.attrs.name, newName);
        } else {
            this._do(newOp);
        }
    },
    _editField(modelName, fieldName, values, forceEdit) {
        return this._rpc({
            route: '/web_studio/edit_field',
            params: {
                model_name: modelName,
                field_name: fieldName,
                values: values,
                force_edit: forceEdit,
            }
        })
    },
    /**
     * @override
     */
    _editView: async function (view_id, studio_view_arch, operations) {
        core.bus.trigger('clear_cache');
        return this._rpc({
            route: '/web_studio/edit_view',
            params: {
                view_id: view_id,
                studio_view_arch: studio_view_arch,
                operations: operations,
                model: this.x2mModel ? this.x2mModel : this.model_name,
                // We write views in the base language to make sure we do it on the source term field
                // of ir.ui.view
                context: _.extend({}, session.user_context, {lang: false}),
            },
        });
    },
    /**
     * @override
     */
    _editViewArch: async function (view_id, view_arch) {
        core.bus.trigger('clear_cache');
        return this._rpc({
            route: '/web_studio/edit_view_arch',
            params: {
                view_id: view_id,
                view_arch: view_arch,
                // We write views in the base language to make sure we do it on the source term field
                // of ir.ui.view
                context: _.extend({}, session.user_context, {lang: false}),
            },
        });
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} new_attrs
     */
    _editViewAttributes: function (type, new_attrs) {
        this._do({
            type: type,
            target: {
                tag: this.view_type === 'list' ? 'tree' : this.view_type,
                isSubviewAttr: true,
            },
            position: 'attributes',
            new_attrs: new_attrs,
        });
    },
    /**
     * Fetch the full spec of the approval rules for a specific
     * action on the model. This is used by the sidebar to display the
     * approval rules on a <button> node.
     * @private
     * @param {String} model_name
     * @param {String} method
     * @param {String} action
     * @returns {Promise}
     */
    _getApprovalSpec: async function (model_name, method, action) {
        const spec = await this._rpc({
            model: 'studio.approval.rule',
            method: 'get_approval_spec',
            args: [model_name, method, action],
            kwargs: { res_id: false },
        });
        return {approvalData: spec};
    },
    /**
     * @private
     * @param {String} model_name
     * @param {String} field_name
     * @returns {Promise}
     */
    _getDefaultValue: function (model_name, field_name) {
        return this._rpc({
            route: '/web_studio/get_default_value',
            params: {
                model_name: model_name,
                field_name: field_name,
            },
        });
    },
    /**
     * @private
     */
    _getDefaultSidebarMode: function () {
        return _.contains(['form', 'list', 'search'], this.view_type) ? 'new' : 'view';
    },
    /**
     * @private
     * @param {String} model_name
     * @returns {Promise}
     */
    _getEmailAlias: function (model_name) {
        return this._rpc({
            route: '/web_studio/get_email_alias',
            params: {
                model_name: model_name,
            },
        });
    },
    /**
     * @private
     * @returns {boolean}
     */
    _getShowInvisible() {
        return Boolean(
            this.sidebar &&
            this.sidebar.state &&
            this.sidebar.state.show_invisible
        );
    },
    /**
     * Makes a fields_get onto the current x2m model
     * @private
     */
    async _getProcessedX2mFields() {
        const fields = await this._rpc({
            model: this.x2mModel,
            method: 'fields_get',
        })
        return this._processFields(fields);
    },
    /**
     * @override
     * @param {Object} [params]
     * @param {Object} [params.node] mandatory if mode "properties"
     */
    _getSidebarState: function (mode, params) {
        var newState;
        var def = Promise.resolve();
        if (mode) {
            newState = _.extend({}, params, {
                renamingAllowedFields: this.renamingAllowedFields,
                mode: mode,
                show_invisible: this._getShowInvisible(),
            });
        } else {
            newState = this.sidebar.state;
        }
        switch (mode) {
            case 'view':
                newState = _.extend(newState, {
                    attrs: this.view.arch.attrs,
                });
                break;
            case 'new':
                break;
            case 'properties':
                var attrs;
                var node = params.node;
                if (node.tag === 'field' && this.view_type !== 'search') {
                    var viewType = this.editor.state.viewType;
                    attrs = this.editor.state.fieldsInfo[viewType][node.attrs.name];
                } else {
                    attrs = node.attrs;
                }
                newState = _.extend(newState, {
                    attrs: attrs,
                });

                var modelName = this.x2mModel ? this.x2mModel : this.model_name;
                if (node.tag === 'field') {
                    def = this._getDefaultValue(modelName, node.attrs.name);
                }
                if (node.tag === 'div' && node.attrs.class === 'oe_chatter') {
                    def = this._getEmailAlias(modelName);
                }
                if (node.tag === 'button' && node.attrs.studio_approval && node.attrs.studio_approval !== 'False') {
                    let method, action;
                    if (node.attrs.type === 'object') {
                        method = node.attrs.name;
                    } else if (node.attrs.type === 'action') {
                        action = parseInt(node.attrs.name);
                    }
                    def = this._getApprovalSpec(modelName, method, action);
                }
                break;
        }

        return def.then(function (result) {
            return _.extend(newState, result);
        });
    },
    /**
     * @private
     * @param  {Array} x2mEditorPath
     * @return {String}
     */
    _getSubviewXpath: function (x2mEditorPath) {
        var subviewXpath = "";
        _.each(x2mEditorPath, function (x2mPath) {
            var x2mViewType = x2mPath.x2mViewType === 'list' ? 'tree' : x2mPath.x2mViewType;
            subviewXpath += "//field[@name='" + x2mPath.x2mField + "']/" + x2mViewType;
        });
        return subviewXpath;
    },
    /**
     * From the main view's fields_view, go through the x2mEditorPath to get the current x2m fields_view
     *
     * @private
     * @param {Object} fieldsView: the main view's field_view
     * @return {Object} the fields_view of the x2m field
     */
    _getX2mFieldsView(fieldsView) {
        // this is a crappy way of processing the arch received as string
        // because we need a processed fields_view to find the x2m fields view
        const View = view_registry.get(this.mainViewType);
        const view = new View(fieldsView, _.extend({}, this.x2mViewParams));

        let fields_view = view.fieldsView;

        const x2mEditorPath = this.x2mEditorPath;
        for (let index = 0; index < x2mEditorPath.length; index++) {
            const step = x2mEditorPath[index];
            const x2mField = fields_view.fieldsInfo[step.parentViewType][step.x2mField];
            fields_view = x2mField.views[step.x2mViewType];
        }
        if (fields_view) {
            fields_view.model = this.x2mModel;
        }
        return fields_view;
    },

    async instantiateWowlController(viewParams) {
        const mainViewType = this.mainViewType;
        const x2ManyInfo = this.x2mEditorPath ? this.x2mEditorPath[this.x2mEditorPath.length-1].wowlX2ManyInfo  : null;
        const nextViewType = x2ManyInfo ? x2ManyInfo.viewType : mainViewType;

        const chatterAllowed = x2ManyInfo ? false : this.chatter_allowed;
        const resModel = x2ManyInfo ? x2ManyInfo.resModel : viewParams.action.res_model;

        const fullXpath = x2ManyInfo ? getX2MFullXpath(this.x2mEditorPath.map(infos => infos.wowlX2ManyInfo)) : "";

        // FIXME: only loadViews when arch changed
        let shouldLoadViews = false; //!!this.wowlEditor;
        if (x2ManyInfo && !x2ManyInfo.hasArch) {
            shouldLoadViews = true;
            const { viewType, fieldName, resModel } = x2ManyInfo;
            const viewId = this.viewDescriptions.views[mainViewType].id;
            const subViewRef = null;
            const studioArch = await wowlCreateInlineView(this.wowlEnv, { subViewType: viewType, viewId, fullXpath, subViewRef, resModel, fieldName })
            this.studio_view_arch = studioArch;
        }

        if (shouldLoadViews) {
            const context = Object.assign({}, this.action.context, { studio: true, lang: false });
            const resModel = this.action.res_model;
            const views = this.action.views;
            const actionId = this.action.id;
            const loadActionMenus = false;
            const loadIrFilters = true;
            this.viewDescriptions = await this.wowlEnv.services.view.loadViews(
                { context, resModel, views },
                { actionId, loadActionMenus, loadIrFilters }
            );
        }

        let { arch, custom_view_id } = this.viewDescriptions.views[mainViewType];
        if (x2ManyInfo) {
            arch = getSubArch(arch, `${fullXpath}/${nextViewType}`);
        }

        // determine view and controller classes
        const view = editorsRegistry.contains(nextViewType) && this.mode === "edition"
            ? editorsRegistry.get(nextViewType)
            : viewRegistry.get(nextViewType);

        if (view.type === "form") {
            const newModel = class newModel extends view.Model {};
            newModel.Record = class newRecord extends view.Model.Record {
                get isInEdition() {
                    return false;
                }
            };
            view.Model = newModel;
        }
        if (this.mode !== "edition") {
            resetViewCompilerCache();
        }
        let resId, resIds = [];
        if (x2ManyInfo) {
            resIds = x2ManyInfo.resIds;
            resId = x2ManyInfo.resId;
        } else if (viewParams.controllerState) {
            resId = viewParams.controllerState.resId || viewParams.controllerState.currentId;
            resIds = viewParams.controllerState.resIds || viewParams.controllerState.res_ids;
        } else {
            resId = this.resId;
            resIds = this.resIds;
        }

        const fields = x2ManyInfo ? this.viewDescriptions.relatedModels[x2ManyInfo.resModel] : this.viewDescriptions.fields;

        let controllerProps = {
            info: {},
            arch,
            fields,
            relatedModels: this.viewDescriptions.relatedModels,
            resModel,
            useSampleModel: false,
            searchMenuTypes: [],
            className: `o_view_controller o_${nextViewType}_view`,
            resId,
            resIds,
        };

        if (["list", "tree", "form"].includes(nextViewType) && this.mode === "edition" && x2ManyInfo) {
            controllerProps.parentRecord = x2ManyInfo.parentRecord;
        }

        if (nextViewType === "form") {
            controllerProps.preventEdit = true;
        }

        if (custom_view_id) {
            // for dashboard
            controllerProps.info.customViewId = custom_view_id;
        }

        const editorCallbacks = {};
        const config = {
            executeCallback: (name, ...args) => editorCallbacks[name](...args),
            registerCallback: (name, fn) => editorCallbacks[name] = fn,
            views: [],
            getDisplayName: () => {},
            setDisplayName: () => {},
            mode: 'readonly',
            chatterAllowed,
            studioShowInvisible: this._getShowInvisible(),
            x2mField: this.x2mField,
            type: nextViewType,
        };

        config.onNodeClicked = (params) => {
            this.wowlEditor.setLastClickedXpath(params.xpath);
            const legacyNode = getLegacyNode(params.xpath, controllerProps.archInfo.xmlDoc)
            this._onNodeClicked({data: {
                node: legacyNode,
                isWowl: true,
            }})
        }
        config.onViewChange = (data) => {
            resetViewCompilerCache();
            return this.__onViewChange(data)
        };

        config.onEditX2ManyView = ({viewType, fieldName, record, xpath}) => {
            let data = record.data[fieldName];
            // LEGACY STUFF: FIXME by removing me
            if ("__bm__" in record.model) {
                // well we shouldn't be here if there is no basicModel
                data = record.model.__bm__.get(record.__bm_handle__).data[fieldName];
            }
            const legacyX2MPath = this._computeX2mPath(fieldName, viewType, null, data);
            legacyX2MPath.x2mViewParams.model = record.model.__bm__;
            legacyX2MPath.x2mViewParams.parentID = record.__bm_handle__;
            // END LEGACY STUFF

            const activeField = record.activeFields[fieldName];
            const staticList = record.data[fieldName];

            const resIds = staticList.records.map((r) => r.resId);
            const wowlX2ManyInfo = {
                hasArch: viewType in activeField.views,
                resModel: staticList.resModel,
                resId: resIds[0],
                resIds,
                viewType,
                parentRecord: record,
                xpath,
                fieldName
            }

            legacyX2MPath.wowlX2ManyInfo = wowlX2ManyInfo;
            bus.trigger('STUDIO_ENTER_X2M', legacyX2MPath);
        }

        config.structureChange = (params) => {
            const legacyNode = getLegacyNode(params.xpath, controllerProps.archInfo.xmlDoc)
            const xpathInfo = xpathToLegacyXpathInfo(params.xpath);
            const data = {...params, node: legacyNode, xpathInfo }
            resetViewCompilerCache();
            this._onViewChange({data});
        }

        controllerProps = view.props ? view.props(controllerProps, view, config) : controllerProps;

        const Controller = view.Controller;
        const SearchModelClass = view.SearchModel || SearchModel;

        const env = extendEnv(this.wowlEnv, { config });
        const studioViewProps = {
            Controller,
            SearchModelClass,
            context: viewParams.context,
            domain: viewParams.domain || [], // bug in cohort domain = false???
            env, // deleted by ComponentWrapper (see owl_compatibility)
            controllerProps,
            setOverlay: !["form", "list", "tree", "kanban"].includes(nextViewType),
            resetSidebar: () => {
                this._resetSidebarMode();
            }
        };

        const Wrapper = wrapperRegistry.get(nextViewType, GenericWowlEditor);
        this.wowlEditor = new Wrapper(this, StudioView, studioViewProps);

        const parser = new DOMParser();
        const xml = parser.parseFromString(controllerProps.arch, "text/xml");
        const rootNode = xml.documentElement;

        const attrs = {};
        for (const { name, value } of rootNode.attributes) {
            attrs[name] = value;
        }
        if (attrs.sample) {
            controllerProps.useSampleModel = Boolean(evaluateExpr(attrs.sample));
        }

        this.view = {
            //  in case we pass line: const arch = Editors[this.view_type].prototype.preprocessArch(this.view.arch);
            arch: Object.assign({}, viewUtils.parseArch(controllerProps.arch), { mode: "view"}),
            controllerProps,
            loadParams: {},
        };
        return this.wowlEditor;
    },
    /**
     * @override
     * @returns {Promise<Widget>}
     */
    _instantiateEditor: async function (params) {
        params = params || {};

        const fields_view = this.fields_view;

        var viewParams = this.x2mField ? this.x2mViewParams : {
            action: this.action,
            context: this.action.context,
            controllerState: this.controllerState,
            withSearchPanel: false,
            domain: this.action.domain,
        };

        var def;
        // Different behaviour for the search view because
        // it's not defined as a "real view", no inherit to abstract view.
        // The search view in studio has its own renderer.
        if (this.view_type === 'search') {
            if (this.mode === 'edition') {
                const editorParams = _.defaults(params, {
                    show_invisible: this._getShowInvisible(),
                });
                this.view = new Editors.search(this, fields_view, editorParams);
            } else {
                this.view = new SearchRenderer(this, fields_view);
            }
            def = Promise.resolve(this.view);
        } else {
            if (CONVERTED_VIEWS.includes(this.view_type)) {
                return this.instantiateWowlController(viewParams);
            }
            let View;
            if (this.view_type === "kanban") {
                View = KanbanView;
            } else if (this.view_type === "list") {
                View = ListView;
            } else {
                View = view_registry.get(this.view_type);
            }
            this.view = new View(fields_view, _.extend({}, viewParams));
            if (this.mode === 'edition') {
                var Editor = Editors[this.view_type];
                if (!Editor) {
                    // generate the Editor on the fly if it doesn't exist
                    if (isComponent(View.prototype.config.Renderer)) {
                        const Renderer = class extends EditorMixinOwl(View.prototype.config.Renderer) { };
                        const propsValidation = View.prototype.config.Renderer.props;
                        if (propsValidation) {
                            const optString = { type: String, optional: 1 };
                            Renderer.props = Object.assign({}, propsValidation, {
                                mode: propsValidation.mode || String,
                                chatter_allowed: propsValidation.chatter_allowed || Boolean,
                                show_invisible: propsValidation.show_invisible || Boolean,
                                arch: propsValidation.arch || Object,
                                x2mField: propsValidation.x2mField || optString,
                                viewType: propsValidation.viewType || String,
                            });
                        }
                        params.Component = Renderer;
                        Editor = EditorWrapper;
                    } else {
                        Editor = View.prototype.config.Renderer.extend(EditorMixin);
                    }
                }
                var chatterAllowed = this.x2mField ? false : this.chatter_allowed;
                var editorParams = _.defaults(params, {
                    mode: 'readonly',
                    chatter_allowed: chatterAllowed,
                    show_invisible: this._getShowInvisible(),
                    arch: this.view.arch,
                    x2mField: this.x2mField,
                    viewType: this.view_type,
                });

                if (this.view_type === 'list') {
                    editorParams.hasSelectors = false;
                }
                def = this.view.createStudioEditor(this, Editor, editorParams);
            } else {
                def = this.view.createStudioRenderer(this, {
                    mode: 'readonly',
                });
            }
        }
        const editor = await def;
        return editor;
    },
    /**
     * @override
     */
    _instantiateSidebar: function (state, previousState) {

        var defaultMode = this._getDefaultSidebarMode();
        state = _.defaults(state || {}, {
            mode: defaultMode,
            attrs: defaultMode === 'view' ? this.view.arch.attrs : {},
        });
        var modelName = this.x2mModel ? this.x2mModel : this.model_name;
        var params = {
            view_type: this.view_type,
            model_name: modelName,
            fields: this.fields,
            renamingAllowedFields: this.renamingAllowedFields,
            state: state,
            previousState: previousState,
            isEditingX2m: !!this.x2mField,
            // In case of a search view, the editor doesn't have state
            editorData: this.editor.state && this.editor.state.data || {},
            fieldsInfo: this.view.fieldsInfo ? this.view.fieldsInfo[this.view_type] : false,
            defaultOrder: this.view.arch.attrs.default_order || false,
        };

        if (_.contains(['list', 'form', 'kanban'], this.view_type)) {
            var fields_in_view = _.pick(this.fields, this.editor.state.getFieldNames());
            var fields_not_in_view = _.omit(this.fields, this.editor.state.getFieldNames());
            params.fields_not_in_view = fields_not_in_view;
            params.fields_in_view = fields_in_view;
        } else if (this.view_type === 'search') {
            // we return all the model fields since it's possible
            // to have multiple times the same field defined in the search view.
            params.fields_not_in_view = this.fields;
            params.fields_in_view = [];
        } else if (this.view_type === 'pivot') {
            const { controllerProps } = this.view;
            const {
                colGroupBys,
                rowGroupBys,
                activeMeasures,
                fieldAttrs,
            } = controllerProps.modelParams.metaData;
            params.fieldsInfo = false // useless for pivot search for fields_in_view
            params.colGroupBys = colGroupBys;
            params.rowGroupBys = rowGroupBys;
            params.measures = computeReportMeasures(this.fields, fieldAttrs, activeMeasures);
        } else if (this.view_type === 'graph') {
            const { controllerProps } = this.view;
            const { groupBy, measure } = controllerProps.modelParams;
            params.groupBys = groupBy;
            params.measure = measure;
        }

        return new ViewEditorSidebar(this, params);
    },

    _computeX2mPath(x2mField, x2mViewType, fieldsView=null, x2mData=null) {
        let fields = this.fields;
        if (fieldsView) {
            fields = fieldsView.fields;
        }
        const x2mModel = fields[x2mField].relation;

        let data = x2mData;
        if (x2mViewType === 'form' && data.count) {
            // the x2m data is a datapoint type list and we need the datapoint
            // type record to open the form view with an existing record
            data = data.data[0];
        }
        const context = _.omit(data.getContext(), function (val, key) {
            return key.startsWith('default_');
        });

        const x2mViewParams = {
            currentId: data.res_id,
            context: context,
            ids: data.res_ids,
            model: this.editor.model,  // reuse the same BasicModel instance
            modelName: x2mModel,
            parentID: this.editor.state.id,
        };

        return  {
            parentViewType: this.view_type,
            x2mField: x2mField,
            x2mViewType: x2mViewType,
            x2mModel,
            x2mData,
            x2mViewParams,
            x2mViewContext: this.view.loadParams.context,
        };
    },
    /**
     * Processes the fields to write the field name inside the description. This
     * name is mainly used in the sidebar.
     *
     * @private
     * @param {Object} fields
     * @returns {Object} a deep copy of fields with the key as attribute `name`
     */
    _processFields: function (fields) {
        fields = $.extend(true, {}, fields);  // deep copy
        _.each(fields, function (value, key) {
            value.name = key;
        });
        return fields;
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     */
    _removeElement: function (type, node, xpath_info) {
        // After the element removal, if the parent doesn't contain any children
        // anymore, the parent node is also deleted (except if the parent is
        // the only remaining node and if we are editing a x2many subview)
        if (!this.x2mField) {
            if (node.attrs.studioXpath) {
                node = findNodeViewArch([this.view.arch], node.attrs.studioXpath);
            }
            var parent_node = findParent(this.view.arch, node, this.expr_attrs);
            var is_root = !findParent(this.view.arch, parent_node, this.expr_attrs);
            var is_group = parent_node.tag === 'group';
            if (parent_node.children.length === 1 && !is_root && !is_group) {
                node = parent_node;
                // Since we changed the node being deleted, we recompute the xpath_info
                // if necessary
                if (node && _.isEmpty(_.pick(node.attrs, this.expr_attrs[node.tag]))) {
                    xpath_info = findParentsPositions(this.view.arch, node);
                }
            }
        }

        this.editor.unselectedElements();
        this._resetSidebarMode();
        this._do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
                xpath_info: xpath_info,
            },
        });
    },
    /**
     * Rename field.
     *
     * @private
     * @param {string} oldName
     * @param {string} newName
     * @returns {Promise}
     */
    _renameField: function (oldName, newName) {
        var self = this;

        // blockUI is used to prevent the user from doing any operation
        // because the hooks are still related to the old field name
        framework.blockUI();
        this.sidebar.$('input').attr('disabled', true);
        this.sidebar.$('select').attr('disabled', true);

        return this._rpc({
            route: '/web_studio/rename_field',
            params: {
                studio_view_id: this.studio_view_id,
                studio_view_arch: this.studio_view_arch,
                model: this.x2mModel ? this.x2mModel : this.model_name,
                old_name: oldName,
                new_name: newName,
            },
        }).then(function () {
            self._updateOperations(oldName, newName);
            var oldFieldIndex = self.renamingAllowedFields.indexOf(oldName);
            self.renamingAllowedFields.splice(oldFieldIndex, 1);
            self.renamingAllowedFields.push(newName);
            return self._applyChanges().then(framework.unblockUI).guardedCatch(framework.unblockUI);
        }).guardedCatch(framework.unblockUI);
    },
    /**
     * @private
     */
    _resetSidebarMode: function () {
        this._updateSidebar(this._getDefaultSidebarMode());
    },
    /**
     * @private
     * @param {int} view_id
     * @returns {Promise}
     */
    _restoreDefaultView: async function (view_id) {
        core.bus.trigger('clear_cache');
        const result = await this._rpc({
            route: '/web_studio/restore_default_view',
            params: {
                view_id: view_id,
            },
        });
        await this._applyChangeHandling(result);
        this.studio_view_id = null;
        this.operations = [];
        this.operations_undone = [];
        this.studio_view_arch = "";
        this._updateButtons();
        await this._updateSidebar(this.sidebar.state.mode);
        bus.trigger('toggle_snack_bar', 'saved');
    },
    /**
     * @private
     * @param {String} model_name
     * @param {String} field_name
     * @param {*} value
     * @returns {Promise}
     */
    _setDefaultValue: function (model_name, field_name, value) {
        var params = {
            model_name: model_name,
            field_name: field_name,
            value: value,
        };
        return this._rpc({route: '/web_studio/set_default_value', params: params});
    },
    /**
     * @private
     * @param {String} model_name
     * @param {[type]} value
     * @returns {Promise}
     */
    _setEmailAlias: function (model_name, value) {
        return this._rpc({
            route: '/web_studio/set_email_alias',
            params: {
                model_name: model_name,
                value: value,
            },
        });
    },
    /**
     * Modifies in place the operation to add `subview_xpath` on the target key.
     *
     * @private
     * @param {Object} op
     */
    _setSubViewXPath: function (op) {
        var subviewXpath = this._getSubviewXpath(this.x2mEditorPath);
        // If the xpath_info last element is the same than the subview type
        // we remove it since it will be added by the subviewXpath.
        if (op.target.xpath_info && op.target.xpath_info[0].tag === this.x2mViewType) {
            op.target.xpath_info.shift();
        }
        op.target.subview_xpath = subviewXpath;

        if (op.type === 'move') {
            // the node also comes from the subview in 'move' operations
            op.node.subview_xpath = subviewXpath;
        }
    },
    /**
     * Slugifies a string (used to transform a label into a field name)
     * Source: https://gist.github.com/mathewbyrne/1280286
     *
     * @private
     * @param {string} text
     * @returns {string}
     */
    _slugify: function (text) {
        return text.toString().toLowerCase().trim()
            .replace(/[^\w\s-]/g, '') // remove non-word [a-z0-9_], non-whitespace, non-hyphen characters
            .replace(/[\s_-]+/g, '_') // swap any length of whitespace, underscore, hyphen characters with a single _
            .replace(/^-+|-+$/g, ''); // remove leading, trailing -
    },
    /**
     * Updates the list of operations after a field renaming (i.e. replace all
     * occurences of @oldName by @newName).
     *
     * @private
     * @param {string} oldName
     * @param {string} newName
     */
    _updateOperations: function (oldName, newName) {
        var strOperations = JSON.stringify(this.operations);
        // We only want to replace exact matches of the field name, but it can
        // be preceeded/followed by other characters, like parent.my_field or in
        // a domain like [('...', '...', my_field)] etc.
        // Note that negative lookbehind is not correctly handled in JS ...
        var chars = '[^\\w\\u007F-\\uFFFF]';
        var re = new RegExp('(' + chars + '|^)' + oldName + '(' + chars + '|$)', 'g');
        this.operations = JSON.parse(strOperations.replace(re, '$1' + newName + '$2'));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
    * Handler for 'Remove rule' button.
    * @private
    * @param {OdooEvent} ev
    */
    _onApprovalArchive: async function (ev) {
        bus.trigger("toggle_snack_bar", "saving");
        await this._rpc({
            model: "studio.approval.rule",
            method: "write",
            args: [[ev.data.ruleId], { active: false }],
        });
        await this._updateSidebar(this.sidebar.state.mode, {
            node: this.sidebar.state.node,
        });
        bus.trigger("toggle_snack_bar", "saved");
        this.updateEditor();
    },
    /**
     * Handler for generic edition of approval rule.
     * @private
     * @param {OdooEvent} ev
     */
    _onApprovalChange: async function(ev) {
        const node = ev.data.node;
        // modifying approval spec, everything done server-side
        // and widgets will fetch their spec on re-render
        const isMethod = node.attrs.type === 'object';
        bus.trigger('toggle_snack_bar', 'saving');
        await this._rpc({
            route: '/web_studio/edit_approval',
            params: {
                model: this.model_name,
                method: isMethod?node.attrs.name:false,
                action: isMethod?false:node.attrs.name,
                operations: [[ev.data.type, ev.data.ruleId, ev.data.payload]],
            }
        });
        bus.trigger('toggle_snack_bar', 'saved');
    },
    /**
    * Handler for writing the domain on an approval rule (when the domain
    * selection dialog is closed).
    * @private
    * @param {OdooEvent} ev
    */
   _onApprovalCondition: async function (ev) {
        bus.trigger("toggle_snack_bar", "saving");
        await this._rpc({
            model: "studio.approval.rule",
            method: "write",
            args: [[ev.data.ruleId], { domain: ev.data.domain }],
        });
        bus.trigger("toggle_snack_bar", "saved");
        this._updateSidebar(this.sidebar.state.mode, {
            node: this.sidebar.state.node,
        });
    },
    /**
    * Handler for changes on the 'group_id' field of an approval rule.
    * @private
    * @param {OdooEvent} ev
    */
    _onApprovalGroupChange: async function (ev) {
        bus.trigger("toggle_snack_bar", "saving");
        await this._rpc({
            model: "studio.approval.rule",
            method: "write",
            args: [[ev.data.ruleId], { group_id: ev.data.groupId }],
        });
        bus.trigger("toggle_snack_bar", "saved");
        this._updateSidebar(this.sidebar.state.mode, {
            node: this.sidebar.state.node,
        });
    },
    /**
    * Handler for 'add approval rule' button.
    * @private
    * @param {OdooEvent} ev
    */
    _onApprovalNewRule: async function (ev) {
        bus.trigger("toggle_snack_bar", "saving");
        await this._rpc({
            model: "studio.approval.rule",
            method: "create_rule",
            args: [],
            kwargs: {
                model: ev.data.model,
                method: ev.data.method,
                action_id: parseInt(ev.data.action),
            },
        });
        await this._updateSidebar(this.sidebar.state.mode, {
            node: this.sidebar.state.node,
        });
        bus.trigger("toggle_snack_bar", "saved");
        this.updateEditor();
    },
    /**
    * Handler for changes on the 'responsible_id' field of an approval rule.
    * @private
    * @param {OdooEvent} ev
    */
     _onApprovalResponsibleChange: async function (ev) {
        bus.trigger("toggle_snack_bar", "saving");
        await this._rpc({
            model: "studio.approval.rule",
            method: "write",
            args: [[ev.data.ruleId], { responsible_id: ev.data.responsibleId }],
        });
        bus.trigger("toggle_snack_bar", "saved");
        this._updateSidebar(this.sidebar.state.mode, {
            node: this.sidebar.state.node,
        });
    },
    /**
     * @override
     */
    _onCloseXMLEditor: function () {
        this._super.apply(this, arguments);
        resetViewCompilerCache();
        this.updateEditor();
    },
    /**
     * Show nearrest hook.
     *
     * @override
     */
    _onDragComponent: function (ev) {
        var is_nearest_hook = this.editor.highlightNearestHook(ev.data.$helper, ev.data.position);
        ev.data.$helper.toggleClass('ui-draggable-helper-ready', is_nearest_hook);
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onDefaultValueChange: function (event) {
        var data = event.data;
        var modelName = this.x2mModel ? this.x2mModel : this.model_name;
        this._setDefaultValue(modelName, data.field_name, data.value)
            .guardedCatch(function () {
                if (data.on_fail) {
                    data.on_fail();
                }
            });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onEmailAliasChange: function (event) {
        var value = event.data.value;
        var modelName = this.x2mModel ? this.x2mModel : this.model_name;
        this._setEmailAlias(modelName, value);
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onFieldEdition: function (event) {
        var self = this;
        var node = event.data.node;
        var field = this.fields[node.attrs.name];
        var dialog = new NewFieldDialog(this, this.model_name, field, this.fields).open();
        var modelName = this.x2mModel ? this.x2mModel : this.model_name;
        dialog.on('field_default_values_saved', this, function (values) {
            self._editField(modelName, field.name, values).then(function (result) {
                const _closeDialog = function () {
                    dialog.close();
                    self._applyChanges(false, false);
                };
                if (result && result.records_linked) {
                    const message = result.message || _t("Are you sure you want to remove the selection values?");
                    Dialog.confirm(self, message, {
                        confirm_callback: async function () {
                            await self._editField(modelName, field.name, values, true);
                            _closeDialog();
                        },
                        dialogClass: 'o_web_studio_preserve_space'
                    });
                } else {
                    _closeDialog();
                }
            });
        });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onFieldRenamed: function (event) {
        this._renameField(event.data.oldName, event.data.newName);
    },
    /**
     * Toggle editor sidebar.
     *
     * @param {Object} ev.data.node
     * @param {jQueryElement} [ev.data.$node]
     * @override
     *
     */
    _onNodeClicked: function (ev) {
        var self = this;
        var node = ev.data.node;
        var $node = ev.data.$node;
        if (this.view_type === 'form' && node.tag === 'field') {
            var field = this.fields[node.attrs.name];
            const attrs = {};
            //var attrs = this.editor.state.fieldsInfo[this.editor.state.viewType][node.attrs.name];
            var isX2Many = _.contains(['one2many','many2many'], field.type);
            var notEditableWidgets = ['many2many_tags', 'hr_org_chart'];
            if (!ev.data.isWowl && isX2Many && !_.contains(notEditableWidgets, attrs.widget)) {
                // If the node is a x2many we offer the possibility to edit or
                // create the subviews
                var message = $(QWeb.render('web_studio.X2ManyEdit'));
                var options = {
                    baseZ: 1000, // reset z-index to 1000 from 1100 for element blocking else dialog hides behind it
                    message: message,
                    css: {
                        cursor: 'auto',
                    },
                    overlayCSS: {
                        cursor: 'auto',
                    }
                };
                // Only the o_field_x2many div needs to be overlaid.
                // So if the node is not the div we find it before applying the overlay.
                if ($node.hasClass('o_field_one2many') || $node.hasClass('o_field_many2many')) {
                    $node.block(options);
                } else {
                    $node.find('div.o_field_one2many, div.o_field_many2many').block(options);
                }
                $node.find('.o_web_studio_editX2Many').click(function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    const x2mFieldName = node.attrs.name;
                    const x2mViewType = e.currentTarget.dataset.type;
                    // trigger on studioBus
                    bus.trigger('STUDIO_ENTER_X2M',
                        self._computeX2mPath(x2mFieldName, x2mViewType, null, self.editor.state.data[x2mFieldName])
                    );
                });
            }
        }
        this._updateSidebar('properties', ev.data);
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onOpenDefaults: function () {
        var modelName = this.x2mModel ? this.x2mModel : this.model_name;
        this.do_action({
            name: _t('Default Values'),
            type: 'ir.actions.act_window',
            res_model: 'ir.default',
            target: 'current',
            views: [[false, 'list'], [false, 'form']],
            domain: [['field_id.model', '=', modelName]],
        });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onOpenFieldForm: function (event) {
        var self = this;
        var field_name = event.data.field_name;
        var modelName = this.x2mModel ? this.x2mModel : this.model_name;
        this._rpc({
            model: 'ir.model.fields',
            method: 'search_read',
            fields: ['id'],
            domain: [['model', '=', modelName], ['name', '=', field_name]],
        }).then(function (result) {
            var res_id = result.length && result[0].id;
            if (res_id) {
                self.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'ir.model.fields',
                    res_id: res_id,
                    views: [[false, 'form']],
                    target: 'current',
                });
            }
        });
    },
    /**
     * @private
     */
    _onOpenRecordFormView: function () {
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'ir.ui.view',
            res_id: this.view_id,
            views: [[false, 'form']],
            target: 'current',
        });
    },
    /**
     * @override
     */
    _onOpenXMLEditor: function () {
        this._super.apply(this, arguments);
        this.renamingAllowedFields = [];
        this.updateEditor();  // the editor will be rendered in `rendering` mode
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onShowInvisibleToggled: function (ev) {
        this.updateEditor({ show_invisible: Boolean(ev.data.show_invisible) });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onViewChange: function (event) {
        this.__onViewChange(event.data);
    },
    /**
     * @private
     * @param {Object} data
     */
    __onViewChange: function (data) {
        var structure = data.structure;
        var type = data.type;
        var node = data.node;
        var new_attrs = data.new_attrs || {};
        var position = data.position || 'after';
        var xpath_info;
        const wowlXpath = data.xpath;
        if (node && !wowlXpath) {
            if (node.attrs.studioXpath) {
                // chatter feature use this: see compilation of true chatter (chatterAdded = false)
                xpath_info = xpathToLegacyXpathInfo(node.attrs.studioXpath);
            } else {
                const arch = Editors[this.view_type].prototype.preprocessArch(this.view.arch);
                xpath_info = findParentsPositions(arch, node);
            }
        } else if (wowlXpath) {
            xpath_info = data.xpathInfo;
        }
        switch (structure) {
            case 'text':
                break;
            case 'picture':
                break;
            case 'group':
                this._addElement(type, node, xpath_info, position, 'group');
                break;
            case 'button':
                this._addButton(data);
                break;
            case 'notebook':
                this._addElement(type, node, xpath_info, position, 'notebook');
                break;
            case 'page':
                this._addPage(type, node, xpath_info, position);
                break;
            case 'field':
                var field_description = data.field_description;
                new_attrs = _.pick(new_attrs, ['name', 'widget', 'options', 'display', 'optional']);
                this._addField(type, field_description, node, xpath_info, position,
                    new_attrs, data);
                break;
            case 'chatter':
                this._addChatter(data);
                break;
            case 'kanban_cover':
                this._editKanbanCover(type);
                break;
            case 'kanban_dropdown':
                this._addKanbanDropdown();
                break;
            case 'kanban_priority':
                this._addKanbanPriority(data);
                break;
            case 'kanban_image':
                this._addKanbanImage(data);
                break;
            case 'remove':
                this._removeElement(type, node, xpath_info);
                break;
            case 'view_attribute':
                this._editViewAttributes(type, new_attrs);
                break;
            case 'edit_attributes':
                this._editElementAttributes(type, node, xpath_info,
                    new_attrs);
                break;
            case 'filter':
                new_attrs = _.pick(new_attrs, ['name', 'string', 'domain', 'context', 'create_group', 'date']);
                this._addFilter(type, node, xpath_info, position, new_attrs);
                break;
            case 'separator':
                this._addSeparator(type, node, xpath_info, position);
                break;
            case 'restore':
                this._restoreDefaultView(this.view_id);
                break;
            case 'map_popup':
                this._changeMapPopupFields(type, data.field_ids);
                break;
            case 'pivot_popup':
                this._changePivotMeasuresFields(type, data.field_ids);
                break;
            case 'graph_pivot_groupbys_fields':
                this._changeGraphPivotGroupbysFields(type, data);
                break;
            case 'avatar_image':
                this._addAvatarImage(data);
                break;
            case 'enable_approval':
                this._addApproval(data);
                break;
        }
    },
});

function findNodeViewArch(archs, xpath) {
    return _findNodeViewArch(archs, xpathToLegacyXpathInfo(xpath));
}

function _findNodeViewArch(archs, xpaths) {
    const xpath = xpaths.shift();
    const filteredArchs = archs.filter(arch => arch.tag === xpath.tag) || [];
    const arch = filteredArchs[xpath.indice - 1];
    if (arch) {
        if (!xpaths.length) {
            return arch;
        }
        return _findNodeViewArch(arch.children, xpaths);
    } else {
        return null;
    }
}

function findParent(arch, node, expr_attrs) {
    var parent = arch;
    var result;
    var xpathInfo = findParentsPositions(arch, node);
    _.each(parent.children, function (child) {
        var deepEqual = true;
        // If there is not the expr_attr, we can't compare the nodes with it
        // so we compute the child xpath_info and compare it to the node
        // we are looking in the arch.
        if (_.isEmpty(_.pick(child.attrs, expr_attrs[child.tag]))) {
            var childXpathInfo = findParentsPositions(arch, child);
            _.each(xpathInfo, function (node, index) {
                if (index >= childXpathInfo.length) {
                    deepEqual = false;
                } else if (!_.isEqual(xpathInfo[index], childXpathInfo[index])) {
                    deepEqual = false;
                }
            });
        }
        if (deepEqual && child.attrs && child.attrs.name === node.attrs.name) {
            result = parent;
        } else {
            var res = findParent(child, node, expr_attrs);
            if (res) {
                result = res;
            }
        }
    });
    return result;
}

function findParentsPositions(arch, node) {
    return _findParentsPositions(arch, node, [], 1);
}

function _findParentsPositions(parent, node, positions, indice) {
    var result;
    positions.push({
        'tag': parent.tag,
        'indice': indice,
    });
    if (parent === node) {
        return positions;
    } else {
        var current_indices = {};
        _.each(parent.children, function (child) {
            // Save indice of each sibling node
            current_indices[child.tag] = current_indices[child.tag] ? current_indices[child.tag] + 1 : 1;
            var res = _findParentsPositions(child, node, positions, current_indices[child.tag]);
            if (res) {
                result = res;
            } else {
                positions.pop();
            }
        });
    }
    return result;
}

return ViewEditorManager;

});
