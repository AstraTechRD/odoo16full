/** @odoo-module **/

"use strict";

import core from "web.core";
import session from "web.session";
import { DocumentAction } from "@sign/js/backend/document";
import { multiFileUpload } from "@sign/js/backend/multi_file_upload";
import { sprintf } from "@web/core/utils/strings";

const { _t } = core;

const EditableDocumentAction = DocumentAction.extend({
  events: {
    "click .o_sign_resend_access_button": async function (e) {
      const $envelope = $(e.target);
      await this._rpc({
        model: "sign.request.item",
        method: "send_signature_accesses",
        args: [parseInt($envelope.parent(".o_sign_signer_status").data("id"))],
        context: session.user_context,
      });
      $envelope.empty().append(_t("Resent !"));
    },
  },

  init: function (parent, action, options) {
    this._super.apply(this, arguments);

    this.is_author = this.create_uid === session.uid;
    this.is_sent = this.state === "sent";

    if (action.context.need_to_sign) {
      const $signButton = $("<button/>", {
        html: _t("Sign Document"),
        type: "button",
        class: "btn btn-primary me-2 o_sign_sign_directly",
      });
      $signButton.on("click", () => {
        this._rpc({
          model: 'sign.request',
          method: 'go_to_signable_document',
          args: [[this.documentID]],
        }).then((action) => {
          action['name'] = _t('Sign'),
          this.do_action(action);
        });
      });
      if (this.cp_content) {
        this.cp_content.$buttons = $signButton.add(this.cp_content.$buttons);
      }
    }
  },

  start: async function () {
    const nextTemplate = multiFileUpload.getNext();

    if (nextTemplate && nextTemplate.template) {
      const nextDocumentButton = $("<button/>", {
        html: _t("Next Document"),
        type: "button",
        class: "btn btn-primary me-2",
      });
      nextDocumentButton.on("click", () => {
        multiFileUpload.removeFile(nextTemplate.template);
        this.do_action(
          {
            type: "ir.actions.client",
            tag: "sign.Template",
            name: sprintf(_t('Template "%s"'), nextTemplate.name),
            context: {
              sign_edit_call: "sign_send_request",
              id: nextTemplate.template,
              sign_directly_without_mail: false,
            },
          },
          { clear_breadcrumbs: true }
        );
      });
      if (this.cp_content) {
        this.cp_content.$buttons = nextDocumentButton.add(
          this.cp_content.$buttons
        );
      }
    }

    await this._super.apply(this, arguments);

    if (this.is_author && this.is_sent) {
      this.cp_content.$pager.find(".o_sign_signer_status.o_sign_signer_waiting")
        .each((i, el) => {
          $(el).prepend(
            $("<button/>", {
              type: "button",
              title:
                this.requestStates && this.requestStates[el.dataset.id]
                  ? _t("Resend the invitation")
                  : _t("Send the invitation"),
              text:
                this.requestStates && this.requestStates[el.dataset.id]
                  ? _t("Resend")
                  : _t("Send"),
              class: "o_sign_resend_access_button btn btn-link ms-2 me-2",
              style: "vertical-align: baseline;",
            })
          );
        });
    }
  },
});

core.action_registry.add("sign.Document", EditableDocumentAction);
