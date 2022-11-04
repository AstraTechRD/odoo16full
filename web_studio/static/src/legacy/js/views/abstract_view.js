odoo.define('web_studio.AbstractViewEditor', function (require) {
"use strict";

const { loadBundle } = require("@web/core/assets");
var AbstractView = require('web.AbstractView');
const RendererWrapper = require('web.RendererWrapper');
const { ComponentWrapper } = require("web.OwlCompatibility");
const utils = require('web.utils');

AbstractView.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Widget} parent
     * @param {Widget} Editor
     * @param {Object} options
     * @returns {Widget}
     */
    createStudioEditor: function (parent, Editor, options) {
        return this._createStudioRenderer(parent, Editor, options);
    },
    /**
     * @param {Widget} parent
     * @param {Widget} Editor
     * @param {Object} options
     * @returns {Widget}
     */
    createStudioRenderer: function (parent, options) {
        var Renderer = this.config.Renderer;
        if (utils.isComponent(Renderer)) {
            options.Component = Renderer;
            Renderer = RendererWrapper;
        }
        options.viewType = 'viewType' in options ? options.viewType : this.viewType;
        return this._createStudioRenderer(parent, Renderer, options);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {Widget} parent
     * @param {Widget} Renderer
     * @param {Object} options
     * @param {String} [options.viewType]
     * @param {String} [options.controllerState]
     * @returns {Widget}
     */
    _createStudioRenderer: function (parent, Renderer, options) {
        var self = this;
        var model = this.getModel(parent);

        var loadViewDef = this._loadSubviews ? this._loadSubviews(parent) : Promise.resolve();
        return loadViewDef.then(function () {
            const searchQuery = self.controllerParams.searchModel.get('query');
            if (options.viewType === 'list') {
                // reset the group by so lists are not grouped in studio.
                searchQuery.groupBy = [];
            }
            if (options.viewType === 'graph') {
                delete options.mode;
            }
            self._updateMVCParams(searchQuery);
            // This override is a hack because when we load the data for a subview in
            // studio we don't want to display all the record of the list view but only
            // the one set in the parent record.
            if (options.x2mField) {
                self.loadParams.static = true;
            }

            const withSampleData = ['graph', 'pivot'].includes(options.viewType) ? true : false;
            return Promise.all([
                self._loadData(model, { withSampleData }),
                loadBundle(self)
            ]).then(function (results) {
                var { state } = results[0];
                if (options.x2mField) {
                    self.loadParams.static = false;
                }
                var params = _.extend({}, self.rendererParams, options, {
                    // TODO: why is it defined now? because it is, the no
                    // content is displayed if no record
                    noContentHelp: undefined,
                });
                let editor;
                if (Renderer.prototype instanceof ComponentWrapper) {
                    state = Object.assign({}, state, params);
                    const Component = state.Component;
                    const props = filterUnwantedProps(Component, state);
                    return new Renderer(parent, Component, props);
                } else {
                    editor = new Renderer(parent, state, params);
                }
                // the editor needs to have a reference to its BasicModel
                // instance to reuse it in x2m edition
                editor.model = model;
                model.setParent(editor);
                return editor;
            });
        });
    },
});

function filterUnwantedProps(ComponentType, params) {
    const props = ComponentType.props;
    if (!props) {
        return params;
    }
    const newParams = {};
    Object.entries(params).forEach(([k, v]) => {
        if (k in props) {
            newParams[k] = v;
        }
    });
    return newParams;
}

});
