odoo.define('web_studio.testUtils', function (require) {
"use strict";

const { start } = require('@mail/../tests/helpers/test_utils');

var dom = require('web.dom');
const MockServer = require('web.MockServer');
const { ComponentAdapter } = require('web.OwlCompatibility');
var QWeb = require('web.QWeb');
const { registry } = require('@web/core/registry');
var testUtils = require('web.test_utils');
var utils = require('web.utils');
var Widget = require('web.Widget');

var ReportEditor = require('web_studio.ReportEditor');
var ReportEditorManager = require('web_studio.ReportEditorManager');
var ReportEditorSidebar = require('web_studio.ReportEditorSidebar');
var ViewEditorManager = require('web_studio.ViewEditorManager');

var weTestUtils = require('web_editor.test_utils');

const { registerCleanup } = require("@web/../tests/helpers/cleanup");

/**
 * Create a ReportEditorManager widget.
 *
 * @param {Object} params
 * @return {ReportEditorManager}
 */
async function createReportEditor(params) {
    var Parent = Widget.extend({
        start: function () {
            var self = this;
            this._super.apply(this, arguments).then(function () {
                var $studio = $.parseHTML(
                    "<div class='o_web_studio_client_action'>" +
                            "<div class='o_web_studio_editor_manager o_web_studio_report_editor_manager'/>" +
                        "</div>" +
                    "</div>");
                self.$el.append($studio);
            });
        },
    });
    var parent = new Parent();
    weTestUtils.patch();
    params.data = weTestUtils.wysiwygData(params.data);
    await testUtils.mock.addMockEnvironment(parent, params);

    var selector = params.debug ? 'body' : '#qunit-fixture';
    return parent.appendTo(selector).then(function () {
        var editor = new ReportEditor(parent, params);
        // override 'destroy' of editor so that it calls 'destroy' on the parent
        // instead
        editor.destroy = function () {
            // remove the override to properly destroy editor and its children
            // when it will be called the second time (by its parent)
            delete editor.destroy;
            // TODO: call super?
            parent.destroy();
            weTestUtils.unpatch();
        };
        return editor.appendTo(parent.$('.o_web_studio_editor_manager')).then(function () {
            return editor;
        });
    });
}

/**
 * Create a ReportEditorManager widget.
 *
 * @param {Object} params
 * @return {Promise<ReportEditorManager>}
 */
async function createReportEditorManager(params) {
    var parent = new StudioEnvironment();
    await testUtils.mock.addMockEnvironment(parent, params);
    weTestUtils.patch();
    params.data = weTestUtils.wysiwygData(params.data);

    var rem = new ReportEditorManager(parent, params);
    // also destroy to parent widget to avoid memory leak
    rem.destroy = function () {
        delete rem.destroy;
        parent.destroy();
        weTestUtils.unpatch();
    };

    var fragment = document.createDocumentFragment();
    var selector = params.debug ? 'body' : '#qunit-fixture';
    if (params.debug) {
        $('body').addClass('debug');
    }
    await parent.prependTo(selector);
    await rem.appendTo(fragment)
    // use dom.append to call on_attach_callback
    dom.append(parent.$('.o_web_studio_client_action'), fragment, {
        callbacks: [{widget: rem}],
        in_DOM: true,
    });
    await rem.editorIframeDef
    return rem;
}

/**
 * Create a sidebar widget.
 *
 * @param {Object} params
 * @return {Promise<ReportEditorSidebar>}
 */
async function createSidebar(params) {
    var Parent = Widget.extend({
        start: function () {
            var self = this;
            this._super.apply(this, arguments).then(function () {
                var $studio = $.parseHTML(
                    "<div class='o_web_studio_client_action'>" +
                            "<div class='o_web_studio_editor_manager o_web_studio_report_editor_manager'/>" +
                    "</div>");
                self.$el.append($studio);
            });
        },
    });
    var parent = new Parent();
    weTestUtils.patch();
    params.data = weTestUtils.wysiwygData(params.data);
    await testUtils.mock.addMockEnvironment(parent, params);

    var sidebar = new ReportEditorSidebar(parent, params);
    sidebar.destroy = function () {
        // remove the override to properly destroy sidebar and its children
        // when it will be called the second time (by its parent)
        delete sidebar.destroy;
        parent.destroy();
        weTestUtils.unpatch();
    };

    var selector = params.debug ? 'body' : '#qunit-fixture';
    if (params.debug) {
        $('body').addClass('debug');
    }
    parent.appendTo(selector);

    var fragment = document.createDocumentFragment();
    return sidebar.appendTo(fragment).then(function () {
        sidebar.$el.appendTo(parent.$('.o_web_studio_editor_manager'));
        return sidebar;
    });
}

/**
 * This class let us instanciate a widget via createWebClient and get it
 * afterwards in order to use it during tests.
 */
const { onMounted, onWillUnmount } = owl;
class StudioEnvironmentComponent extends ComponentAdapter {
    constructor() {
        super(...arguments);
        this.env = owl.Component.env;
        onMounted(() => {
            StudioEnvironmentComponent.currentWidget = this.widget;
        });
        onWillUnmount(() => {
            StudioEnvironmentComponent.currentWidget = undefined;
        });
    }
}

/**
 * Create a ViewEditorManager widget.
 *
 * @param {Object} params
 * @return {ViewEditorManager}
 */
async function createViewEditorManager(params) {
    weTestUtils.patch();
    params.serverData = params.serverData || {};
    params.serverData.models = params.serverData.models || {};
    params.serverData.models = weTestUtils.wysiwygData(params.serverData.models);
    registry.category('main_components').add('StudioEnvironmentContainer', {
        Component: StudioEnvironmentComponent,
        props: { Component: StudioEnvironment },
    });
    const { env: wowlEnv } = await start({
        ...params,
        legacyParams: { withLegacyMockServer: true },
    });
    const parent = StudioEnvironmentComponent.currentWidget;
    const fieldsView = testUtils.mock.getView(MockServer.currentMockServer, params);
    if (params.viewID) {
        fieldsView.view_id = params.viewID;
    }
    const type = fieldsView.type;

    const viewDescriptions = {
        fields: fieldsView.fields,
        relatedModels: {
            [params.model]: fieldsView.fields,
        },
        views: {
            [type]: {
                arch: fieldsView.arch,
                id: fieldsView.view_id || false,
                custom_view_id: null,
            },
        }
    }


    const vem = new ViewEditorManager(parent, {
        action: {
            context: params.context || {},
            domain: params.domain || [],
            res_model: params.model,
        },
        controllerState: {
            currentId: 'res_id' in params ? params.res_id : undefined,
            resIds: 'res_id' in params ? [params.res_id] : undefined,
        },
        fields_view: fieldsView,
        viewType: fieldsView.type,
        studio_view_id: params.studioViewID,
        chatter_allowed: params.chatter_allowed,
        wowlEnv,
        viewDescriptions,
    });

    registerCleanup(() => {
        vem.destroy();
        weTestUtils.unpatch();
    });

    const fragment = document.createDocumentFragment();
    await parent.prependTo(testUtils.prepareTarget(params.debug));
    await vem.appendTo(fragment);
    dom.append(parent.$('.o_web_studio_client_action'), fragment, {
        callbacks: [{widget: vem}],
        in_DOM: true,
    });
    return vem;
}

/**
 * Renders a list of templates.
 *
 * @param {Array<Object>} templates
 * @param {Object} data
 * @param {String} [data.dataOeContext]
 * @returns {string}
 */
function getReportHTML(templates, data) {
    _brandTemplates(templates, data && data.dataOeContext);

    var qweb = new QWeb();
    _.each(templates, function (template) {
        qweb.add_template(template.arch);
    });
    var render = qweb.render('template0', data);
    return render;
}

/**
 * Builds the report views object.
 *
 * @param {Array<Object>} templates
 * @param {Object} [data]
 * @param {String} [data.dataOeContext]
 * @returns {Object}
 */
function getReportViews(templates, data) {
    _brandTemplates(templates, data && data.dataOeContext);

    var reportViews = {};
    _.each(templates, function (template) {
        reportViews[template.view_id] = {
            arch: template.arch,
            key: template.key,
            studio_arch: '</data>',
            studio_view_id: false,
            view_id: template.view_id,
        };
    });
    return reportViews;
}

/**
 * Brands (in place) a list of templates.
 *
 * @private
 * @param {Array<Object>} templates
 * @param {String} [dataOeContext]
 */
function _brandTemplates(templates, dataOeContext) {

    _.each(templates, function (template) {
        brandTemplate(template);
    });

    function brandTemplate(template) {
        var doc = $.parseXML(template.arch).documentElement;
        var rootNode = utils.xml_to_json(doc, true);
        brandNode([rootNode], rootNode, '');

        function brandNode(siblings, node, xpath) {
            // do not brand already branded nodes
            if (_.isObject(node) && !node.attrs['data-oe-id']) {
                if (node.tag !== 'kikou') {
                    xpath += ('/' + node.tag);
                    var index = _.filter(siblings, {tag: node.tag}).indexOf(node);
                    if (index > 0) {
                        xpath += '[' + index + ']';
                    }
                    node.attrs['data-oe-id'] = template.view_id;
                    node.attrs['data-oe-xpath'] = xpath;
                    node.attrs['data-oe-context'] = dataOeContext || '{}';
                }

                _.each(node.children, function (child) {
                    brandNode(node.children, child, xpath);
                });
            }
        }
        template.arch = utils.json_node_to_xml(rootNode);
    }
}

var StudioEnvironment = Widget.extend({
    className: 'o_web_client o_in_studio',
    start: function () {
        var self = this;
        this._super.apply(this, arguments).then(function () {
            // reproduce the DOM environment of Studio
            var $studio = $.parseHTML(
                "<div class='o_content'>" +
                    "<div class='o_web_studio_client_action'/>" +
                "</div>"
            );
            self.$el.append($studio);
        });
    },
});

return {
    createReportEditor: createReportEditor,
    createReportEditorManager: createReportEditorManager,
    createSidebar: createSidebar,
    createViewEditorManager: createViewEditorManager,
    getData: weTestUtils.wysiwygData,
    getReportHTML: getReportHTML,
    getReportViews: getReportViews,
    patch: weTestUtils.patch,
    unpatch: weTestUtils.unpatch,
};

});
