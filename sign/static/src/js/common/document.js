/** @odoo-module **/

"use strict";

import { PDFIframe } from "@sign/js/common/PDFIframe";
import Widget from "web.Widget";

export const Document = Widget.extend({
  start: function () {
    this.attachmentLocation = this.$("#o_sign_input_attachment_location").val();
    this.templateName = this.$("#o_sign_input_template_name").val();
    this.templateID = parseInt(this.$("#o_sign_input_template_id").val());
    this.templateItemsInProgress = parseInt(
      this.$("#o_sign_input_template_in_progress_count").val()
    );
    this.requestID = parseInt(this.$("#o_sign_input_sign_request_id").val());
    this.requestToken = this.$("#o_sign_input_sign_request_token").val();
    this.requestState = this.$("#o_sign_input_sign_request_state").val();
    this.accessToken = this.$("#o_sign_input_access_token").val();
    this.templateEditable = this.$("#o_sign_input_template_editable").val();
    this.authMethod = this.$("#o_sign_input_auth_method").val();
    this.signerName = this.$("#o_sign_signer_name_input_info").val();
    this.signerPhone = this.$("#o_sign_signer_phone_input_info").val();
    this.RedirectURL = this.$("#o_sign_input_optional_redirect_url").val();
    this.RedirectURLText = this.$(
      "#o_sign_input_optional_redirect_url_text"
    ).val();
    this.types = this.$(".o_sign_field_type_input_info");
    this.items = this.$(".o_sign_item_input_info");
    this.select_options = this.$(".o_sign_select_options_input_info");
    this.$validateBanner = this.$(".o_sign_validate_banner").first();
    this.$validateButton = this.$(".o_sign_validate_banner button").first();
    this.validateButtonText = this.$validateButton.text();
    this.isUnknownPublicUser = this.$("#o_sign_is_public_user").length > 0;

    return Promise.all([
      this._super.apply(this, arguments),
      this.initialize_iframe(),
    ]);
  },

  get_pdfiframe_class: function () {
    return PDFIframe;
  },

  initialize_iframe: function () {
    this.$iframe = this.$("iframe.o_sign_pdf_iframe").first();
    if (this.$iframe.length > 0 && !this.iframeWidget) {
      this.iframeWidget = new (this.get_pdfiframe_class())(
        this,
        this.attachmentLocation,
        !this.requestID,
        {
          types: this.types,
          signatureItems: this.items,
          select_options: this.select_options,
        },
        parseInt(this.$("#o_sign_input_current_role").val()),
        this.$("#o_sign_input_current_role_name").val()
      );
      return this.iframeWidget.attachTo(this.$iframe);
    }
    return Promise.resolve();
  },
});

export default Document;
