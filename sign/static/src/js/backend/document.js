/** @odoo-module **/

"use strict";
import AbstractAction from "web.AbstractAction";
import core from "web.core";
import { Document } from "@sign/js/common/document";
import framework from "web.framework";

export const DocumentAction = AbstractAction.extend({
  hasControlPanel: true,

  on_detach_callback: function () {
    core.bus.off("DOM_updated", this, this._init_page);
    return this._super.apply(this, arguments);
  },
  go_back_to_kanban: function () {
    return this.do_action("sign.sign_request_action", {
      clear_breadcrumbs: true,
    });
  },

  init: function (parent, action) {
    this._super.apply(this, arguments);
    const context = action.context;
    if (context.id === undefined) {
      return;
    }

    this.documentID = context.id;
    this.token = context.token;
    this.create_uid = context.create_uid;
    this.state = context.state;
    this.requestStates = context.request_item_states;

    this.token_list = context.token_list;
    this.name_list = context.name_list;
    this.cp_content = {};
    this.template_editable = context.template_editable;
  },
  /**
   * Callback to react to DOM_updated events. Loads the iframe and its contents
   * just after it is really in the DOM.
   *
   * @private
   */
  _init_page: async function () {
    if (this.$el.parents("html").length) {
      await this.refresh_cp();
      framework.blockUI({
        overlayCSS: { opacity: 0 },
        blockMsgClass: "o_hidden",
      });
      if (!this.documentPage) {
        this.documentPage = new (this.get_document_class())(this);
        await this.documentPage.attachTo(this.$el);
      } else {
        await this.documentPage.initialize_iframe();
      }
      await framework.unblockUI();
    }
  },
  start: async function () {
    if (this.documentID === undefined) {
      return this.go_back_to_kanban();
    }
    return Promise.all([this._super(), this.fetchDocument()]);
  },

  fetchDocument: async function () {
    const html = await this._rpc({
      route: "/sign/get_document/" + this.documentID + "/" + this.token,
      params: { message: this.message },
    });
    const $html = $(html.trim());

    this.$(".o_content").append($html);
    this.$(".o_content").addClass("o_sign_document");

    const newButtons =this.$(".o_sign_cp_buttons :is(button, a)").detach();
    this.$signer_info = this.$(".o_sign_signer_status_wrapper").detach();

    this.$buttons =
      this.cp_content &&
      this.cp_content.$buttons &&
      this.cp_content.$buttons.length
        ? this.cp_content.$buttons
        : $("");

    this.$buttons = $.merge(this.$buttons, newButtons);

    this.cp_content = {
      $buttons: this.$buttons,
      $pager: this.$signer_info,
    };
  },

  on_attach_callback: function () {
    core.bus.on("DOM_updated", this, this._init_page);
    return this._super.apply(this, arguments);
  },

  get_document_class: function () {
    return Document;
  },

  refresh_cp: function () {
    return this.updateControlPanel({
      cp_content: this.cp_content,
    });
  },
});

export default DocumentAction;
