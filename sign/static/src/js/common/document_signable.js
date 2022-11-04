/** @odoo-module **/

// Signing part
"use strict";
/* global html2canvas */

import ajax from "web.ajax";
import config from "web.config";
import core from "web.core";
import { sprintf } from "@web/core/utils/strings";
import Dialog from "web.Dialog";
import { Document } from "@sign/js/common/document";
import { NameAndSignature } from "web.name_and_signature";
import session from "web.session";
import Widget from "web.Widget";
import time from "web.time";

const _t = core._t;

// The goal of this override is to fetch a default signature if one was
// already set by the user for this request.
const SignNameAndSignature = NameAndSignature.extend({
    template: 'sign.sign_name_and_signature',
    events: _.extend({}, NameAndSignature.prototype.events, {
        'click .o_web_frame_button': '_onClickFrameButton'
    }),
  //----------------------------------------------------------------------
  // Public
  //----------------------------------------------------------------------

  /**
   * Adds requestID and accessToken.
   *
   * @constructor
   * @param {Widget} parent
   * @param {Object} options
   * @param {number} requestID
   * @param {string} accessToken
   * @param {Array<String>} signatureFonts array of base64 encoded fonts
   */
  init: function (parent, options, requestID, accessToken, signatureFonts, hash, activeFrame) {
    this._super.apply(this, arguments);

    this.requestID = requestID;
    this.accessToken = accessToken;
    this.defaultSignature = options.defaultSignature || "";
    this.signatureChanged = !options.defaultSignature;
    this.fonts = signatureFonts;
    this.hash = hash;
    this.signLabel = _t('Signed with Odoo Sign');
    this.activeFrame = activeFrame;
    this.frame = options.defaultFrame;
    this.frameChanged = false;

    // if defaultSignature exists, we don't want to have mode set to auto
    if (this.defaultSignature) {
      this.signMode = 'draw';
    }
  },

  willStart: function () {
    return Promise.all([
      session.user_has_group('base.group_user').then(
      (res) => {
         this.showFrameCheck = res;
      }),
      this._super.apply(this, arguments)
    ]);
  },

  start: function () {
    const res = this._super.apply(this, arguments);
    this.$frameButton = this.$('.o_web_frame_button');
    this.$frameDiv = this.$('.o_sign_frame');
    this.$frameButton.prop('checked', this.activeFrame);
    this.$frameDiv.toggleClass('active', this.activeFrame);
    return res;
  },

  /**
   * Sets the existing signature.
   *
   * @override
   */
  resetSignature: function () {
    const self = this;
    return this._super.apply(this, arguments).then(function () {
      if (
        self.defaultSignature &&
        self.defaultSignature !== self.emptySignature
      ) {
        const settings = self.$signatureField.jSignature("getSettings");
        const decorColor = settings["decor-color"];
        self.$signatureField.jSignature("updateSetting", "decor-color", null);
        self.$signatureField.jSignature("reset");
        self.$signatureField.jSignature("importData", self.defaultSignature);
        settings["decor-color"] = decorColor;

        return self._waitForSignatureNotEmpty();
      }
    });
  },
  //----------------------------------------------------------------------
  // Handlers
  //----------------------------------------------------------------------

  /**
   * Override: If a user clicks on load, we overwrite the signature in the server.
   *
   * @see NameAndSignature._onChangeSignLoadInput()
   * @private
   */
  _onChangeSignLoadInput: function () {
    this.signatureChanged = true;
    return this._super.apply(this, arguments);
  },

  _onClickFrameButton: function () {
    this.signatureChanged = true;
    this.activeFrame = !this.activeFrame;
    this.$frameButton.prop('checked', this.activeFrame);
    this.$frameDiv.toggleClass('active', this.activeFrame);
  },

  _updateFrame: function () {
    if (this.activeFrame && !this.frameChanged) {
      this.signatureChanged = true;
      this.frameChanged = true;
      return html2canvas(this.$frameDiv[0],
        {
          'backgroundColor': null,
          'width': this.$signatureField.width(),
          'height': this.$signatureField.height(),
          'x': -this.$signatureField.width() * 0.06, // TODO VISUEL
          'y': -this.$signatureField.height() * 0.09, // TODO VISUEL
        }
      ).then(canvas => {
        this.frame = canvas.toDataURL('image/png');
      });
    }
    return Promise.resolve(false);
  },

  _getFrameImageSrc: function () {
    return this.activeFrame ? this.frame : false;
  },
  /**
   * If a user clicks on draw, we overwrite the signature in the server.
   *
   * @override
   * @see NameAndSignature._onClickSignDrawClear()
   * @private
   */
  _onClickSignDrawClear: function () {
    this.signatureChanged = true;
    return this._super.apply(this, arguments);
  },
  /**
   * If a user clicks on auto, we overwrite the signature in the server.
   *
   * @override
   * @see NameAndSignature._onClickSignAutoButton()
   * @private
   */
  _onClickSignAutoButton: function () {
    this.signatureChanged = true;
    return this._super.apply(this, arguments);
  },
  /**
   * If a user clicks on draw, we overwrite the signature in the server.
   *
   * @override
   * @see NameAndSignature._onClickSignDrawButton()
   * @private
   */
  _onClickSignDrawButton: function () {
    this.signatureChanged = true;
    return this._super.apply(this, arguments);
  },
});

// The goal of this override is to make the dialog re-enable the validate button
// when it is closed by the user
export const SignInfoDialog = Dialog.extend({
  destroy: function () {
    if (!this.isDestroyed()) {
      const parent = this.getParent();
      if (parent.$validateButton) {
        const signableDocument = parent;
        signableDocument.$validateButton.text(signableDocument.validateButtonText).removeAttr("disabled", true);
      }
    }
    this._super.apply(this, arguments);
  },
});

// The goal of this dialog is to ask the user a signature request.
// It uses @see SignNameAndSignature for the name and signature fields.
const SignatureDialog = SignInfoDialog.extend({
  template: "sign.signature_dialog",
  custom_events: {
    signature_changed: "_onChangeSignature",
  },

  //----------------------------------------------------------------------
  // Public
  //----------------------------------------------------------------------

  /**
   * Allows options.
   *
   * @constructor
   * @param {Widget} parent
   * @param {Object} options
   * @param {string} [options.title='Adopt Your Signature'] - modal title
   * @param {string} [options.size='medium'] - modal size
   * @param {Object} [options.nameAndSignatureOptions={}] - options for
   *  @see NameAndSignature.init()
   * @param {number} requestID
   * @param {string} accessToken
   * @param {Array<String>} signatureFonts array of base64 encoded fonts
   */
  init: function (parent, options, requestID, accessToken, signatureFonts, hash='', activeFrame=false) {
    options = options || {};

    options.title = options.title || _t("Adopt Your Signature");
    options.size = options.size || "medium";
    options.technical = false;
    if (config.device.isMobile) {
      options.technical = true;
      options.fullscreen = true;
    }

    if (!options.buttons) {
      options.buttons = this.addDefaultButtons();
    }

    this._super(parent, options);

    this.confirmFunction = function () {};

    const hashText = hash && hash.substring(0, 10) + '...' || '';

    this.nameAndSignature = new SignNameAndSignature(
      this,
      options.nameAndSignatureOptions,
      requestID,
      accessToken,
      signatureFonts,
      hashText,
      activeFrame
    );
  },
  /**
   * Start the nameAndSignature widget and wait for it.
   *
   * @override
   */
  willStart: function () {
    return Promise.all([
      this.nameAndSignature.appendTo($("<div>")),
      this._super.apply(this, arguments),
    ]);
  },
  /**
   * Initialize the name and signature widget when the modal is opened.
   *
   * @override
   */
  start: function () {
    const self = this;
    this.$primaryButton = this.$footer.find(".btn-primary");
    this.$secondaryButton = this.$footer.find(".btn-secondary");
    this.opened().then(function () {
      self
        .$(".o_web_sign_name_and_signature")
        .replaceWith(self.nameAndSignature.$el);
      // initialize the signature area
      self.nameAndSignature.resetSignature();
    });
    return this._super.apply(this, arguments);
  },

  destroy: function () {
    if (!this.isDestroyed() && this.getParent()) {
        this.getParent().isDialogOpen = false;
    }
    this._super.apply(this, arguments);
  },

  onConfirm: function (fct) {
    this.confirmFunction = fct;
  },

  onConfirmAll: function (fct) {
    this.confirmAllFunction = fct;
  },

  addDefaultButtons() {
    const buttons = [];
    buttons.push({
      text: _t("Cancel"),
      classes: 'btn-link',
      close: true,
    });
    buttons.push({
      text: _t("Sign"),
      classes: "btn-secondary",
      disabled: true,
      click: (e) => {
        this.confirmFunction();
      },
    });
    buttons.push({
      text: _t("Sign all"),
      classes: "btn-primary",
      disabled: true,
      click: (e) => {
        //this.confirmAllFunction is undefined in documents with no sign items
        this.confirmAllFunction
          ? this.confirmAllFunction()
          : this.confirmFunction();
      },
    });
    return buttons;
  },

  /**
   * Gets the name currently given by the user.
   *
   * @see NameAndSignature.getName()
   * @returns {string} name
   */
  getName: function () {
    return this.nameAndSignature.getName();
  },
  /**
   * Gets the signature currently drawn.
   *
   * @see NameAndSignature.getSignatureImage()
   * @returns {string[]} Array that contains the signature as a bitmap.
   *  The first element is the mimetype, the second element is the data.
   */
  getSignatureImage: function () {
    return this.nameAndSignature.getSignatureImage();
  },
  /**
   * Gets the signature currently drawn, in a format ready to be used in
   * an <img/> src attribute.
   *
   * @see NameAndSignature.getSignatureImageSrc()
   * @returns {string} the signature currently drawn, src ready
   */
  getSignatureImageSrc: function () {
    return this.nameAndSignature.getSignatureImageSrc();
  },
  /**
   * Returns whether the drawing area is currently empty.
   *
   * @see NameAndSignature.isSignatureEmpty()
   * @returns {boolean} Whether the drawing area is currently empty.
   */
  isSignatureEmpty: function () {
    return this.nameAndSignature.isSignatureEmpty();
  },
  /**
   * Gets the current name and signature, validates them, and
   * returns the result. If they are invalid, it also displays the
   * errors to the user.
   *
   * @see NameAndSignature.validateSignature()
   * @returns {boolean} whether the current name and signature are valid
   */
  validateSignature: function () {
    return this.nameAndSignature.validateSignature();
  },

  //----------------------------------------------------------------------
  // Handlers
  //----------------------------------------------------------------------

  /**
   * Toggles the submit button depending on the signature state.
   *
   * @private
   */
  _onChangeSignature: function () {
    const isEmpty = this.nameAndSignature.isSignatureEmpty();
    this.$primaryButton.prop("disabled", isEmpty);
    this.$secondaryButton.prop("disabled", isEmpty);
  },
  /**
   * @override
   */
  renderElement: function () {
    this._super.apply(this, arguments);
    // this trigger the adding of a custom css
    this.$modal.addClass("o_sign_signature_dialog");
  },
});

const SignItemNavigator = Widget.extend({
  className: "o_sign_sign_item_navigator",

  events: {
    click: "onClick",
  },

  init: function (parent, types) {
    this._super(parent);

    this.types = types;
    this.started = false;
    this.isScrolling = false;
  },

  start: function () {
    this.$signatureItemNavLine = $("<div/>")
      .addClass("o_sign_sign_item_navline")
      .insertBefore(this.$el);
    this.setTip(_t("Click to start"));
    this.$el.focus();

    return this._super();
  },

  setTip: function (tip) {
    this.$el.text(tip);
  },

  onClick: function (e) {
    this.goToNextSignItem();
  },

  goToNextSignItem() {
    const self = this;

    if (!self.started) {
      self.started = true;

      self
        .getParent()
        .$iframe.prev()
        .animate(
          { height: "0px", opacity: 0 },
          {
            duration: 750,
            complete: function () {
              self.getParent().$iframe.prev().hide();
              self.getParent().refreshSignItems();

              self.goToNextSignItem();
            },
          }
        );

      return false;
    }

    const $signItemsToComplete = self
      .getParent()
      .checkSignItemsCompletion()
      .sort((a, b) => {
        return ($(a).data("order") || 0) - ($(b).data("order") || 0);
      });
    if ($signItemsToComplete.length > 0) {
      self.scrollToSignItem($signItemsToComplete.first());
    }
  },

  scrollToSignItem: function ($item) {
    const self = this;
    if (!this.started) {
      return;
    }
    this._scrollToSignItemPromise($item).then(function () {
      const type = self.types[$item.data("type")];
      if (type.item_type === "text") {
        $item.val = () => $item.find("input").val();
        $item.focus = () => $item.find("input").focus();
      }

      if ($item.val() === "" && !$item.data("signature")) {
        self.setTip(type.tip);
      }

      self.getParent().refreshSignItems();
      $item.focus();
      if (["signature", "initial"].includes(type.item_type)) {
        if ($item.data('has-focus')) {
          // items with isEditMode have a different html structure
          $item.data('isEditMode') ? $item.find('.o_sign_item_display').click() : $item.click();
        } else {
          $item.data("has-focus", true);
        }
      }
      self.isScrolling = false;
    });

    this.getParent().$(".ui-selected").removeClass("ui-selected");
    $item.addClass("ui-selected").focus();
  },

  _scrollToSignItemPromise($item) {
    if (config.device.isMobile) {
      return new Promise((resolve) => {
        this.isScrolling = true;
        $item[0].scrollIntoView({
          behavior: "smooth",
          block: "center",
          inline: "center",
        });
        resolve();
      });
    }

    const $container = this.getParent().$("#viewerContainer");
    const $viewer = $container.find("#viewer");
    const containerHeight = $container.outerHeight();
    const viewerHeight = $viewer.outerHeight();

    let scrollOffset = containerHeight / 4;
    const scrollTop = $item.offset().top - $viewer.offset().top - scrollOffset;
    if (scrollTop + containerHeight > viewerHeight) {
      scrollOffset += scrollTop + containerHeight - viewerHeight;
    }
    if (scrollTop < 0) {
      scrollOffset += scrollTop;
    }
    scrollOffset +=
      $container.offset().top -
      this.$el.outerHeight() / 2 +
      parseInt($item.css("height")) / 2;

    const duration = Math.min(
      500,
      5 *
        (Math.abs($container[0].scrollTop - scrollTop) +
          Math.abs(parseFloat(this.$el.css("top")) - scrollOffset))
    );

    this.isScrolling = true;
    const def1 = new Promise(function (resolve, reject) {
      $container.animate({ scrollTop: scrollTop }, duration, function () {
        resolve();
        core.bus.trigger("resize");
      });
    });
    const def2 = new Promise((resolve, reject) => {
      this.$el
        .add(this.$signatureItemNavLine)
        .animate({ top: scrollOffset }, duration, function () {
          resolve();
          core.bus.trigger("resize");
        });
    });
    return Promise.all([def1, def2]);
  },
});

const PublicSignerDialog = SignInfoDialog.extend({
  template: "sign.public_signer_dialog",
  init(parent, requestID, requestToken, RedirectURL, options) {
    options = options || {};

    options.title = options.title || _t("Final Validation");
    options.size = options.size || "medium";
    options.technical = false;

    if (config.device.isMobile) {
      options.technical = true;
      options.fullscreen = true;
    }

    if (!options.buttons) {
      this.addDefaultButtons(parent, options);
    }

    this._super(parent, options);

    this.requestID = requestID;
    this.requestToken = requestToken;
    this.sent = new Promise((resolve) => {
      this.sentResolve = resolve;
    });
  },

  addDefaultButtons(parent, options) {
    options.buttons = [];
    options.buttons.push({ text: _t("Cancel"), classes: "btn-link", close: true });
    options.buttons.push({
      text: _t("Validate & Send"),
      classes: "btn-primary",
      click: async (e) => {
        const name = this.inputs[0].value;
        const mail = this.inputs[1].value;
        if (!this.validateDialogInputs(name, mail)) {
          return false;
        }
        const response = await this._rpc({
            route:
              "/sign/send_public/" + this.requestID + "/" + this.requestToken,
            params: {
              name: name,
              mail: mail,
            },
          })
        parent.requestID = response['requestID'];
        parent.requestToken = response['requestToken'];
        parent.accessToken = response['accessToken'];
        if(parent.coords) {
          await this._rpc({
            route:
              "/sign/save_location/" + parent.requestID + "/" + parent.accessToken,
            params: parent.coords,
          });
        }
        this.close();
        this.sentResolve();
      },
    });
    this.options = options;
  },

  validateDialogInputs(name, mail) {
    const isEmailInvalid = !mail || mail.indexOf("@") < 0;
    if (!name || isEmailInvalid) {
      this.inputs[0]
        .closest(".row")
        .querySelector(".form-control, .form-select")
        .classList.toggle("is-invalid", !name);
      this.inputs[1]
        .closest(".row")
        .querySelector(".form-control, .form-select")
        .classList.toggle("is-invalid", isEmailInvalid);
      return false;
    }
    return true;
  },

  open(name, mail) {
    this.opened(() => {
      this.inputs = this.el.querySelectorAll("input");
      this.inputs[0].value = name;
      this.inputs[1].value = mail;
    });
    return this._super.apply(this, arguments);
  },
});

const SMSSignerDialog = SignInfoDialog.extend({
  template: "sign.public_sms_signer",
  events: {
    "click button.o_sign_resend_sms": function (e) {
      const sendButton = this.el.querySelector(".o_sign_resend_sms");
      sendButton.disabled = true;
      const phoneNumber = this.el.querySelector("#o_sign_phone_number_input")
        .value;
      phoneNumber
        ? this.sendSMS(phoneNumber, sendButton)
        : sendButton.removeAttribute("disabled");
    },
  },

  sendSMS(phoneNumber, sendButton) {
    const route =
      "/sign/send-sms/" +
      this.requestID +
      "/" +
      this.requestToken +
      "/" +
      phoneNumber;
    session
      .rpc(route, {})
      .then((success) => {
        const errorMessage = _t(
          "Unable to send the SMS, please contact the sender of the document."
        );
        success
          ? this.handleSendSMSSuccess(sendButton)
          : this.handleSMSError(sendButton, errorMessage);
      })
      .guardedCatch((error) => {
        this.handleSMSError(sendButton);
      });
  },
  handleSendSMSSuccess(button) {
    button.innerHtml =
      "<span><i class='fa fa-check'/> " + _t("SMS Sent") + "</span>";
    setTimeout(() => {
      button.removeAttribute("disabled");
      button.textContent = _t("Re-send SMS");
    }, 15000);
  },
  handleSMSError(button, message) {
    button.removeAttribute("disabled");
    Dialog.alert(this, message, {
      title: _t("Error"),
    });
  },
  async _onValidateSMS() {
    const validateButton = this.$footer[0].querySelector(
      ".o_sign_validate_sms"
    );
    const validationCodeInput = this.el.querySelector(
      "#o_sign_public_signer_sms_input"
    );
    if (!validationCodeInput.value) {
      validationCodeInput
        .closest(".row")
        .querySelector(".form-control, .form-select")
        .classList.toggle("is-invalid");
      return false;
    }
    validateButton.disabled = true;
    this.getParent().signInfo.smsToken = validationCodeInput.value;
    await this.getParent()._signDocument(validationCodeInput.value);
    validateButton.removeAttribute("disabled");
  },
  init: function (
    parent,
    requestID,
    requestToken,
    signature,
    newSignItems,
    signerPhone,
    RedirectURL,
    options
  ) {
    options = options || {};
    if (config.device.isMobile) {
      options.fullscreen = true;
    }
    options.title = options.title || _t("Final Validation");
    options.size = options.size || "medium";
    if (!options.buttons) {
      options.buttons = this.addDefaultButtons();
    }
    this._super(parent, options);
    this.requestID = requestID;
    this.requestToken = requestToken;
    this.signature = signature;
    this.newSignItems = newSignItems;
    this.signerPhone = signerPhone;
    this.RedirectURL = RedirectURL;
    this.sent = $.Deferred();
  },
  addDefaultButtons() {
    return [
      {
        text: _t("Verify"),
        classes: "btn btn-primary o_sign_validate_sms",
        click: this._onValidateSMS,
      },
    ];
  },
});

const EncryptedDialog = SignInfoDialog.extend({
  template: "sign.public_password",

  _onValidatePassword: function () {
    const input = this.$("#o_sign_public_signer_password_input");
    if (!input.val()) {
      input.toggleClass("is-invalid");
      return false;
    }
    const route = "/sign/password/" + this.requestID;
    const params = {
      password: input.val(),
    };
    const self = this;
    session.rpc(route, params).then(function (response) {
      if (!response) {
        Dialog.alert(self, _t("Password is incorrect."), {
          title: _t("Error"),
        });
      }
      if (response === true) {
        self.close();
      }
    });
  },

  init: function (parent, requestID, options) {
    options = options || {};
    if (config.device.isMobile) {
      options.fullscreen = true;
    }
    options.title = options.title || _t("PDF is encrypted");
    options.size = options.size || "medium";
    if (!options.buttons) {
      options.buttons = this.addDefaultButtons();
    }
    this._super(parent, options);
    this.requestID = requestID;
  },

  /**
   * @override
   */
  renderElement: function () {
    this._super.apply(this, arguments);
    this.$modal.find("button.btn-close").addClass("invisible");
  },
  addDefaultButtons() {
    return [
      {
        text: _t("Generate PDF"),
        classes: "btn btn-primary o_sign_validate_encrypted",
        click: this._onValidatePassword,
      },
    ];
  },
});

export const ThankYouDialog = Dialog.extend({
  template: "sign.thank_you_dialog",
  events: {
    "click .o_go_to_document": "on_closed",
  },

  get_passworddialog_class: function () {
    return EncryptedDialog;
  },

  init: function (parent, RedirectURL, RedirectURLText, requestID, accessToken, options) {
    options = options || {};
    options.title = options.title || _t("Thank You !");
    options.subtitle = options.subtitle || _t("Your signature has been saved.");
    options.message = options.message || _t("You will receive a copy of the signed document by mail.");
    options.size = options.size || "medium";
    options.technical = false;
    options.buttons = [];
    if (RedirectURL) {
      // check if url contains http:// or https://
      if (!/^(f|ht)tps?:\/\//i.test(RedirectURL)) {
        RedirectURL = "http://" + RedirectURL;
      }
      options.buttons.push({
        text: RedirectURLText,
        classes: "btn-primary",
        click: function (e) {
          window.location.replace(RedirectURL);
        },
      });
    } else {
      const openDocumentButton = {
        text: _t("View Document"),
        classes: "btn-primary",
        click: this.viewDocument,
      };
      options.buttons.push(openDocumentButton);
    }
    this.options = options;
    this.has_next_document = false;
    this.RedirectURL = RedirectURL;
    this.requestID = requestID;
    this.accessToken = accessToken;

    this._super(parent, options);

    this._rpc({
      route: "/sign/encrypted/" + requestID,
    }).then((response) => {
      if (response === true) {
        new (this.get_passworddialog_class())(this, requestID).open();
      }
    });
  },

  /**
   * @override
   */
  renderElement: function () {
    this._super.apply(this, arguments);
    // this trigger the adding of a custom css
    this.$modal.addClass("o_sign_thank_you_dialog");
    this.$modal.find("button.btn-close").addClass("invisible");
    this.$modal.find(".modal-header .o_subtitle").before("<br/>");
  },

  viewDocument: function () {
    const protocol = window.location.protocol;
    const port = window.location.port;
    const hostname = window.location.hostname;
    const address = `${protocol}//${hostname}:${port}/sign/document/${this.requestID}/${this.accessToken}`;
    window.location.replace(address);
  }
});

const NextDirectSignDialog = Dialog.extend({
  template: "sign.next_direct_sign_dialog",
  events: {
    "click .o_go_to_document": "on_closed",
    "click .o_nextdirectsign_link": "on_click_next",
  },

  init: function (parent, RedirectURL, requestID, options) {
    this.token_list = parent.token_list || {};
    this.name_list = parent.name_list || {};
    this.requestID = parent.requestID;
    this.create_uid = parent.create_uid;
    this.state = parent.state;

    options = options || {};
    options.title = options.title || _t("Thank You !");
    options.subtitle =
      options.subtitle ||
      _t("Your signature has been saved.") +
        " " +
        sprintf(_t(`Next signatory is "%s"`), this.name_list[0]);
    options.size = options.size || "medium";
    options.technical = false;
    if (config.device.isMobile) {
      options.technical = true;
      options.fullscreen = true;
    }
    (options.buttons = [
      {
        text: sprintf(
          _t(`Next signatory ("%s")`),
          this.name_list[0]
        ),
        click: this.on_click_next,
      },
    ]),
      (this.options = options);
    this.RedirectURL = "RedirectURL";
    this.requestID = requestID;
    this._super(parent, options);
  },

  /**
   * @override
   */
  renderElement: function () {
    this._super.apply(this, arguments);
    this.$modal.addClass("o_sign_next_dialog");
    this.$modal.find("button.btn-close").addClass("invisible");
    this.$modal.find(".modal-header .o_subtitle").before("<br/>");
  },

  on_click_next: function () {
    const newCurrentToken = this.token_list.shift();
    this.name_list.shift();

    this.do_action(
      {
        type: "ir.actions.client",
        tag: "sign.SignableDocument",
        name: _t("Sign"),
      },
      {
        additional_context: {
          id: this.requestID,
          create_uid: this.create_uid,
          state: this.state,
          token: newCurrentToken,
          token_list: this.token_list,
          name_list: this.name_list,
        },
        replace_last_action: true,
      }
    );

    this.destroy();
  },
});

const InputBottomSheet = Widget.extend({
  events: {
    "blur .o_sign_item_bottom_sheet_field": "_onBlurField",
    "keyup .o_sign_item_bottom_sheet_field": "_onKeyUpField",
    "click .o_sign_next_button": "_onClickNext",
  },
  template: "sign.item_bottom_sheet",

  init(parent, options) {
    this._super(...arguments);

    this.type = options.type || "text";
    this.placeholder = options.placeholder || "";
    this.label = options.label || this.placeholder;
    this.value = options.value || "";
    this.buttonText = options.buttonText || _t("next");
    this.onTextChange = options.onTextChange || function () {};
    this.onValidate = options.onValidate || function () {};
  },

  updateInputText(text) {
    this.value = text;
    this.el.querySelector(".o_sign_item_bottom_sheet_field").value = text;
    this._toggleButton();
  },

  show() {
    // hide previous bottom sheet
    const bottomSheet = document.querySelector(
      ".o_sign_item_bottom_sheet.show"
    );
    if (bottomSheet) {
      bottomSheet.classList.remove("show");
    }

    this._toggleButton();
    this.el.style.display = "block";
    setTimeout(() => this.el.classList.add("show"));
    this.el.querySelector(".o_sign_item_bottom_sheet_field").focus();
  },

  hide() {
    this.el.classList.remove("show");
    this.el.addEventListener(
      "transitionend",
      () => (this.el.style.display = "none"),
      { once: true }
    );
  },

  _toggleButton() {
    const buttonNext = this.el.querySelector(".o_sign_next_button");
    this.value.length
      ? buttonNext.removeAttribute("disabled")
      : buttonNext.setAttribute("disabled", "disabled");
  },

  _updateText() {
    this.value = this.el.querySelector(".o_sign_item_bottom_sheet_field").value;
    this.onTextChange(this.value);
    this._toggleButton();
  },

  _onBlurField() {
    this._updateText();
  },

  _onClickNext() {
    this.onValidate(this.value);
  },

  _onKeyUpField() {
    this._updateText();
  },
});

export const SignableDocument = Document.extend({
  events: {
    "pdfToComplete .o_sign_pdf_iframe": function (e) {
      this.$validateBanner.hide().css("opacity", 0);
    },

    "pdfCompleted .o_sign_pdf_iframe": function (e) {
      if (this.name_list && this.name_list.length > 0) {
        const next_name_signatory = this.name_list[0];
        const next_signatory = sprintf(
          _t(`Validate & the next signatory is "%s"`),
          next_name_signatory
        );
        this.$validateBanner
          .find(".o_validate_button")
          .prop("textContent", next_signatory);
      }
      this.$validateBanner.show().animate({ opacity: 1 }, 500, () => {
        if (config.device.isMobile) {
          this.$validateBanner[0].scrollIntoView({
            behavior: "smooth",
            block: "center",
            inline: "center",
          });
        }
      });
    },

    "click .o_sign_validate_banner button": "signDocument",
    "click .o_sign_refuse_document_button": "refuseDocument",
  },

  init: function (parent, options) {
    this._super(parent, options);
    if (parent) {
      this.token_list = parent.token_list || {};
      this.name_list = parent.name_list || {};
      this.create_uid = parent.create_uid;
      this.state = parent.state;
      this.documentID = parent.documentID;
      this.frame_hash = parent
    }
  },

  start: function () {
    this.frame_hash = this.$("#o_sign_input_sign_frame_hash").val();
    return this._super.apply(this, arguments);
  },

  get_pdfiframe_class: function () {
    const SignablePDFIframe = this._super.apply(this, arguments).extend({
      init: function () {
        this._super.apply(this, arguments);
        this.events = Object.assign(this.events || {}, {
          "keydown .page .ui-selected": function (e) {
            if ((e.keyCode || e.which) !== 13) {
              return true;
            }
            e.preventDefault();
            this.signatureItemNav.goToNextSignItem();
          },
        });
        this.fonts = [];
      },
      fetchSignatureFonts: function () {
        return this._rpc({
          route: `/web/sign/get_fonts/`
        }).then(data => {
          this.fonts = data;
        })
      },

      doPDFPostLoad: function () {
        Promise.all([
          this.fullyLoaded,
          this.fetchSignatureFonts()
        ]).then(() => {
          this.signatureItemNav = new SignItemNavigator(this, this.types);
          return this.signatureItemNav
            .prependTo(this.$("#viewerContainer"))
            .then(() => {
              this.checkSignItemsCompletion();
              this.$("#viewerContainer").on("scroll", (e) => {
                if (
                  !this.signatureItemNav.isScrolling &&
                  this.signatureItemNav.started
                ) {
                  this.signatureItemNav.setTip(_t("next"));
                }
              });
            });
        });

        this._super.apply(this, arguments);
      },

      createSignItem: function (
        type,
        required,
        responsible,
        posX,
        posY,
        width,
        height,
        value,
        frame_value,
        options,
        name,
        tooltip,
        alignment,
        isSignItemEditable,
        update = true
      ) {
        const $signatureItem = this._super.apply(this, arguments);
        const readonly =
          this.readonlyFields ||
          (responsible > 0 && responsible !== this.role) ||
          !!value;
        if (!readonly) {
          // Do not display the placeholder of Text and Multiline Text if the name of the item is the default one.
          if (
            ["text", "textarea"].includes(type.name) &&
            type.placeholder === $signatureItem.prop("placeholder")
          ) {
            $signatureItem.attr("placeholder", " ");
            $signatureItem.find(".o_placeholder").text(" ");
          }
          this.registerCreatedSignItemEvents(
            $signatureItem,
            type,
            isSignItemEditable
          );
        } else {
          $signatureItem.val(value);
        }
        return $signatureItem;
      },
      /**
       * Fills text sign item with value
       * @param { jQuery } $signatureItem sign item
       * @param { String } value
       */
      fillTextSignItem($signatureItem, value) {
        if ($signatureItem.val() === "") {
          $signatureItem.val(value);
          $signatureItem.trigger("input");
        }
      },

      /**
       *
       * @param { jQuery } $signatureItem
       * @param { Object } type type of sign item
       * @param { Boolean } isSignItemEditable flag for sign item added while signing
       */
      registerCreatedSignItemEvents($signatureItem, type, isSignItemEditable) {
        if (type.name === _t("Date")) {
          $signatureItem.on("focus", (e) =>
            this.fillTextSignItem(
              $(e.currentTarget),
              moment().format(time.getLangDateFormat())
            )
          );
        }
        if (type.item_type === "signature" || type.item_type === "initial") {
          $signatureItem.on(
            "click",
            (e) => {
              // when signing for the first time in edit mode, clicking in .o_sign_item_display should cause the sign.
              // (because both edit and sign are possible) However if you want to change the signature after another
              // one is set, .o_sign_item_display is not there anymore.
              if (
                this.isDialogOpen ||
                isSignItemEditable &&
                $(e.currentTarget).find('.o_sign_item_display').length &&
                !$(e.target).hasClass('o_sign_item_display')
              ) {
                return;
              }
              this.handleSignatureDialogClick($(e.currentTarget), type)
            }
          );
        }

        if (type.auto_value && ['text', 'textarea'].includes(type.item_type)) {
          $signatureItem.on("focus", (e) =>
            this.fillTextSignItem($signatureItem, type.auto_value)
          );
        }

        if (
          config.device.isMobile &&
          ["text", "textarea"].includes(type.item_type)
        ) {
          const inputBottomSheet = new InputBottomSheet(this, {
            type: type.item_type,
            value: $signatureItem.val(),
            label: `${type.tip}: ${type.placeholder}`,
            placeholder: $signatureItem.attr("placeholder"),
            onTextChange: (value) => {
              $signatureItem.val(value);
            },
            onValidate: (value) => {
              $signatureItem.val(value);
              $signatureItem.trigger("input");
              inputBottomSheet.hide();
              this.signatureItemNav.goToNextSignItem();
            },
          });
          inputBottomSheet.appendTo(document.body);

          $signatureItem.on("focus", () => {
            inputBottomSheet.updateInputText($signatureItem.val());
            inputBottomSheet.show();
          });
        }

        $signatureItem.on("input", (e) => {
          this.checkSignItemsCompletion(this.role);
          this.signatureItemNav.setTip(_t("next"));
        });
      },
      /**
       * Logic for wizard/mark behavior is:
       * If auto_value is defined and the item is not marked yet, auto_value is used
       * Else, wizard is opened.
       * @param { jQuery } $signatureItem
       * @param { Object } type
       */
      handleSignatureDialogClick($signatureItem, type) {
        this.refreshSignItems();
        if (
          type.auto_value &&
          !$signatureItem.data("signature")
        ) {
          this.adjustSignatureSize(type.auto_value, $signatureItem).then(
            (data) => {
              this.adjustSignatureSize(type.frame_value, $signatureItem).then(
                (frame_data) => {
                  $signatureItem
                    .data("signature", data)
                    .empty()
                    .append($("<span/>").addClass("o_sign_helper"));
                  if (frame_data) {
                    $signatureItem
                      .data({
                        frameHash: "0",
                        frame: frame_data,
                      })
                      .append($("<img/>", { src: $signatureItem.data("frame"), class: 'o_sign_frame'}));
                  }
                  $signatureItem.append($("<img/>", { src: $signatureItem.data("signature") }));
                  $signatureItem.trigger("input");
                }
              );
            }
          );
        } else if (
          type.item_type === "initial" &&
          this.nextInitial &&
          !$signatureItem.data("signature")
        ) {
          this.adjustSignatureSize(this.nextInitial, $signatureItem).then(
            (data) => {
              $signatureItem
                .data("signature", data)
                .empty()
                .append(
                  $("<span/>").addClass("o_sign_helper"),
                  $("<img/>", { src: $signatureItem.data("signature") })
                );
              $signatureItem.trigger("input");
            }
          );
        } else {
          this.openSignatureDialog($signatureItem, type);
        }
      },

      openSignatureDialog($signatureItem, type) {
        this.isDialogOpen = true;
        const nameAndSignatureOptions = {
          defaultName: this.getParent().signerName || "",
          fontColor: "DarkBlue",
          signatureType: type.item_type,
          defaultSignature: type.auto_value,
          defaultFrame: type.frame_value,
          displaySignatureRatio:
            parseFloat($signatureItem.css("width")) /
            parseFloat($signatureItem.css("height")),
        };
        const signDialog = new SignatureDialog(
          this,
          { nameAndSignatureOptions: nameAndSignatureOptions },
          this.getParent().requestID,
          this.getParent().accessToken,
          this.fonts,
          this.getParent().frame_hash,
          $signatureItem.find('.o_sign_frame').length > 0 || !type.auto_value,
        );

        signDialog.open().onConfirm(async() => {
          if (!signDialog.isSignatureEmpty() && signDialog.nameAndSignature.signatureChanged) {
            const name = signDialog.getName();
            const signature = signDialog.getSignatureImageSrc();
            await signDialog.nameAndSignature._updateFrame();
            const frame = signDialog.nameAndSignature._getFrameImageSrc();
            this.getParent().signerName = name;

            type.auto_value = signature;
            type.frame_value = frame;

            if (session.user_id) {
              this.updateUserSignature(type);
            }
            $signatureItem.empty()
              .data({
                signature: signature
              })
              .append($("<span/>").addClass("o_sign_helper"));
              if (frame && signDialog.nameAndSignature.activeFrame) {
                $signatureItem
                  .data({
                    frameHash: signDialog.nameAndSignature.hash,
                    frame: frame,
                  }).append($("<img/>", { src: $signatureItem.data("frame"), class: 'o_sign_frame' }));
              }
              else {
                $signatureItem.removeData("frame");
              }
              $signatureItem.append($("<img/>", { src: $signatureItem.data("signature") }));
          } else if (signDialog.nameAndSignature.signatureChanged) {
            $signatureItem
              .removeData("signature")
              .removeData("frame")
              .empty()
              .append($("<span/>").addClass("o_sign_helper"), type.placeholder);
          }

          $signatureItem.trigger("input").focus();
          signDialog.close();
        });

        signDialog.onConfirmAll(async () => {
          const name = signDialog.getName();
          const signature = signDialog.getSignatureImageSrc();
          await signDialog.nameAndSignature._updateFrame();
          const frame = signDialog.nameAndSignature._getFrameImageSrc();
          const frameHash = signDialog.nameAndSignature.hash;

          this.getParent().signerName = name;
          type.auto_value = signature;
          type.frame_value = frame;

          if (session.user_id && signDialog.nameAndSignature.signatureChanged) {
            this.updateUserSignature(type);
          }

          for (const pageNumber of Object.keys(this.configuration)) {
            const page = this.configuration[pageNumber];
            await Promise.all(
              page.reduce((promise, item) => {
                if (
                  item.data("type") === type.id &&
                  item.data("responsible") === this.role
                ) {
                  promise.push(
                    this.adjustSignatureSize(signature, item).then((data) => {
                      this.adjustSignatureSize(frame, item).then((frame_data) => {
                        item
                        .data("signature", data)
                        .empty()
                        .append($("<span/>").addClass("o_sign_helper"));
                        if (signDialog.nameAndSignature.activeFrame && frame_data) {
                          item.data({
                            frameHash: frameHash,
                            frame: frame_data,
                          }).append($("<img/>", { src: item.data("frame"), class: 'o_sign_frame'}));
                        }
                        else {
                          item.removeData("frame");
                        }
                        item.append($("<img/>", { src: item.data("signature") }));
                      })
                    })
                  );
                }
                return promise;
              }, [])
            );
          }
          $signatureItem.trigger("input").focus();
          signDialog.close();
        });
      },

      /**
       * Updates the user's signature in the res.user model
       * @param { Object } type
       */
      updateUserSignature(type) {
        this._rpc({
          route: "/sign/update_user_signature/",
          params: {
            sign_request_id: this.getParent().requestID,
            role: this.role,
            signature_type:
              type.item_type === "signature" ? "sign_signature" : "sign_initials",
            datas: type.auto_value,
            frame_datas: type.frame_value,
          },
        });
      },

      /**
       * Adjusts signature/initial size to fill the dimensions of the sign item box
       * @param { String } data base64 image
       * @param { jQuery } signatureItem
       * @returns { Promise }
       */
      adjustSignatureSize: function (data, signatureItem) {
        if (!data) { return Promise.resolve(false); }
        return new Promise(function (resolve, reject) {
          const img = new Image();
          img.onload = function () {
            const c = document.createElement("canvas");
            const boxWidth = signatureItem.width();
            const boxHeight = signatureItem.height();
            const imgHeight = img.height;
            const imgWidth = img.width;
            const ratio_box_w_h = boxWidth / boxHeight;
            const ratio_img_w_h = imgWidth / imgHeight;

            const [canvasHeight, canvasWidth] = ratio_box_w_h > ratio_img_w_h ?
              [imgHeight,  imgHeight * ratio_box_w_h] :
              [imgWidth / ratio_box_w_h, imgWidth];

            c.height = canvasHeight;
            c.width = canvasWidth;

            const ctx = c.getContext("2d");
            const oldShadowColor = ctx.shadowColor;
            ctx.shadowColor = "transparent";
            ctx.drawImage(
              img,
              c.width / 2 - (img.width) / 2,
              c.height / 2 - (img.height) / 2,
              img.width,
              img.height
            );
            ctx.shadowColor = oldShadowColor;
            resolve(c.toDataURL());
          };
          img.src = data;
        });
      },

      checkSignItemsCompletion: function () {
        this.refreshSignItems();
        const $toComplete = this.$(
          ".o_sign_sign_item.o_sign_sign_item_required:not(.o_sign_sign_item_pdfview)"
        ).filter(function (i, el) {
          let $elem = $(el);
          /* in edit mode, the text sign item has a different html structure due to the form and resize/close icons
                for this reason, we need to check the input field inside the element to check if it has a value */
          $elem =
            $elem.data("isEditMode") && $elem.attr("type") === "text"
              ? $elem.find("input")
              : $elem;
          const unchecked_box = $elem.val() == "on" && !$elem.is(":checked");
          return (
            !(($elem.val() && $elem.val().trim()) || $elem.data("signature")) ||
            unchecked_box
          );
        });

        this.signatureItemNav.$el
          .add(this.signatureItemNav.$signatureItemNavLine)
          .toggle($toComplete.length > 0);
        this.$iframe.trigger(
          $toComplete.length > 0 ? "pdfToComplete" : "pdfCompleted"
        );

        return $toComplete;
      },
    });
    return SignablePDFIframe;
  },

  get_thankyoudialog_class: function () {
    return ThankYouDialog;
  },

  get_nextdirectsigndialog_class: function () {
    return NextDirectSignDialog;
  },
  signDocument: async function (e) {
    this.$validateButton.attr("disabled", true);
    this.signInfo = {name: "", mail: ""};
    this.iframeWidget.$(".o_sign_sign_item").each((i, el) => {
      const value = $(el).val();
      if (value && value.indexOf("@") >= 0) {
        this.signInfo.mail = value;
      }
    });
    [this.signInfo.signatureValues, this.signInfo.frameValues, this.signInfo.newSignItems] = this.getSignatureValuesFromConfiguration();
    if (!this.signInfo.signatureValues) {
      this.iframeWidget.checkSignItemsCompletion();
      Dialog.alert(this, _t("Some fields have still to be completed !"), {
        title: _t("Warning"),
      });
      this.$validateButton.text(this.validateButtonText).removeAttr("disabled", true);
      return;
    }
    this.signInfo.hasNoSignature =
      Object.keys(this.signInfo.signatureValues).length == 0 &&
      !(this.iframeWidget &&
        this.iframeWidget.signatureItems &&
        Object.keys(this.iframeWidget.signatureItems).length > 0)

    this._signDocument();
  },

  _signDocument: async function (e) {
    this.$validateButton.text(this.validateButtonText).prepend('<i class="fa fa-spin fa-circle-o-notch" />');
    this.$validateButton.attr("disabled", true);
    if (this.signInfo.hasNoSignature) {
      if (this.isDialogOpen) {
        return;
      }
      this.isDialogOpen = true;
      const nameAndSignatureOptions = {
        fontColor: "DarkBlue",
        defaultName: this.signerName,
      };
      const options = { nameAndSignatureOptions: nameAndSignatureOptions };
      const signDialog = new SignatureDialog(
        this,
        options,
        this.requestID,
        this.accessToken,
        this.iframeWidget.fonts
      );

      signDialog.open().onConfirm(() => {
        if (!signDialog.validateSignature()) {
          return false;
        }

        this.signInfo.name = signDialog.getName();
        this.signInfo.signatureValues = signDialog.getSignatureImage()[1];
        this.signInfo.frameValues = [];
        this.signInfo.hasNoSignature = false;

        signDialog.close();
        this._signDocument();
      });
    } else if (this.isUnknownPublicUser) {
      new PublicSignerDialog(
        this,
        this.requestID,
        this.requestToken,
        this.RedirectURL,
        { nextSign: this.name_list.length }
      )
        .open(this.signInfo.name, this.signInfo.mail)
        .sent.then(() => {
          this.isUnknownPublicUser = false;
          this._signDocument()
      });
    } else if (this.authMethod) {
      this.openAuthDialog();
    } else {
      await this._sign();
      return;
    }
  },

  openAuthDialog: async function () {
    const authDialog = await this.getAuthDialog();
    if (authDialog) {
      authDialog.open();
    } else {
      this._sign();
    }
  },

  getAuthDialog: async function () {
    if (this.authMethod === 'sms' && !this.signInfo.smsToken) {
      // check for sms credits
      const credits = await session.rpc('/sign/has_sms_credits');
      if (credits) {
        return new SMSSignerDialog(
          this,
          this.requestID,
          this.accessToken,
          this.signInfo.signatureValues,
          this.signInfo.newSignItems,
          this.signerPhone,
          this.RedirectURL,
          {nextSign: this.name_list.length}
        );
      }
      return false;
    }
    return false;
  },

  _getRouteAndParams: function () {
    const route = this.signInfo.smsToken ?
      `/sign/sign/${this.requestID}/${this.accessToken}/${this.signInfo.smsToken || ''}` :
      `/sign/sign/${this.requestID}/${this.accessToken}`;

    const params = {
      signature: this.signInfo.signatureValues,
      frame: this.signInfo.frameValues,
      new_sign_items: this.signInfo.newSignItems,
    };
    return [route, params];
  },

  _sign: async function () {
    const [route, params] = this._getRouteAndParams();
    return session.rpc(route, params).then((response) => {
      this.$validateButton.text(this.validateButtonText).removeAttr("disabled", true);
      if (response.success) {
        if (response.url) {
          document.location.pathname = response.url;
        } else {
          this.iframeWidget.disableItems();
          if (this.name_list && this.name_list.length > 0) {
            new (this.get_nextdirectsigndialog_class())(
                this,
                this.RedirectURL,
                this.requestID,
                {nextSign: this.name_list.length}
            ).open();
          } else {
            this.openThankYouDialog(0);
          }
        }
      } else {
        if (response.sms) {
          Dialog.alert(
            this,
            _t("Your signature was not submitted. Ensure the SMS validation code is correct."),
            {title: _t("Error")}
          );
        } else {
          this.openErrorDialog(
            _t(
              "Sorry, an error occurred, please try to fill the document again."
            ),
            () => { window.location.reload(); }
          );
        }
      };
    });
  },

  /**
   * Gets the signature values dictionary from the iframeWidget.configuration
   * Gets the added sign items that were added in edit while signing
   * @returns { Array } array with [0] being the signature values and [1] the new sign items added when editing while signing
   */
  getSignatureValuesFromConfiguration() {
    let signatureValues = {};
    let frameValues = {};
    let newSignItems = {};
    for (let page in this.iframeWidget.configuration) {
      for (let i = 0; i < this.iframeWidget.configuration[page].length; i++) {
        const $elem = this.iframeWidget.configuration[page][i];
        const resp = parseInt($elem.data("responsible")) || 0;
        if (resp > 0 && resp !== this.iframeWidget.role) {
          continue;
        }
        let value;
        /*open inputs*/
        if ($elem.prop('nodeName').toLowerCase() === 'input' || $elem.find("input").length) {
            value =
              $elem.val() && $elem.val().trim()
                ? $elem.val()
                : $elem.find("input").val() || false;
        } else {
        /*Already prefilled*/
            value =
              $elem.text() && $elem.text().trim() ? $elem.text() : false;
        }

        let frameValue = false;
        let frameHash = false;

        if ($elem.data("signature")) {
          value = $elem.data("signature");
          frameValue = $elem.data("frame");
          frameHash = $elem.data('frameHash');
        }
        if ($elem[0].type === "checkbox") {
          value = false;
          if ($elem[0].checked) {
            value = "on";
          } else {
            if (!$elem.data("required")) value = "off";
          }
        } else if ($elem[0].type === "textarea") {
          value = this.textareaApplyLineBreak($elem[0]);
        }
        if (!value) {
          if ($elem.data("required")) {
            return [{}, {}];
          }
          continue;
        }

        signatureValues[parseInt($elem.data("item-id"))] = value;
        frameValues[parseInt($elem.data("item-id"))] = {frameValue, frameHash};

        if ($elem.data("isEditMode")) {
          const id = $elem.data("item-id");
          newSignItems[id] = {
            type_id: $elem.data("type"),
            required: $elem.data("required"),
            name: $elem.data("name") || false,
            option_ids: $elem.data("option_ids"),
            responsible_id: resp,
            page: page,
            posX: $elem.data("posx"),
            posY: $elem.data("posy"),
            width: $elem.data("width"),
            height: $elem.data("height"),
          };
        }
      }
    }

    return [signatureValues, frameValues, newSignItems];
  },

  openThankYouDialog(nextSign) {
    new (this.get_thankyoudialog_class())(
      this,
      this.RedirectURL,
      this.RedirectURLText,
      this.requestID,
      this.accessToken,
      { nextSign }
    ).open();
  },
  /**
   * Opens an error dialog
   * @param { String } errorMessage translated error message
   * @param {*} confirmCallback callback after confirm
   */
  openErrorDialog(errorMessage, confirmCallback) {
    Dialog.alert(this, errorMessage, {
      title: _t("Error"),
      confirm_callback: confirmCallback,
    });
  },

  refuseDocument: function (e) {
    const $content = $(core.qweb.render('sign.refuse_confirm_dialog', { widget: this }));
    const buttons = [
      {
        text: _t("Refuse"),
        classes: 'btn-primary o_safe_confirm_button',
        close: true,
        click: this._refuse.bind(this),
        disabled: true,
      },
      {
        text: _t("Cancel"),
        close: true,
      }
    ];
    const dialog = new Dialog(this, {
      size: 'medium',
      buttons: buttons,
      $content: $content,
      title: _t("Refuse Document"),
    });
    dialog.opened(() => {
      const $button = dialog.$footer.find('.o_safe_confirm_button');
      dialog.$content.find(".o_sign_refuse_confirm_message").on('change keyup paste',  function (ev) {
          $button.prop('disabled', $(this).val().length === 0);
      });
    });
    return dialog.open();
},

  _refuse: function () {
    const refusalReason = $(".o_sign_refuse_confirm_message").val();

    // refuse sign request
    const route = `/sign/refuse/${this.requestID}/${this.accessToken}`;
    const params = {
      refusal_reason: refusalReason
    };
    session.rpc(route, params).then(response => {
      if (!response) {
        return this.openErrorDialog (
          _t("Sorry, you cannot refuse this document"),
          () => { window.location.reload(); }
        );
      }
      this.iframeWidget.disableItems();
      (new (this.get_thankyoudialog_class())(this, this.RedirectURL, this.RedirectURLText, this.requestID, this.accessToken, {
        'nextSign': 0,
        'subtitle': _t("The document has been refused"),
        'message': _t("We'll send an email to warn other contacts in copy & signers with the reason you provided."),
      })).open();
    });
  },

  textareaApplyLineBreak: function (oTextarea) {
    // Removing wrap in order to have scrollWidth > width
    oTextarea.setAttribute("wrap", "off");

    const strRawValue = oTextarea.value;
    oTextarea.value = "";

    const nEmptyWidth = oTextarea.scrollWidth;
    let nLastWrappingIndex = -1;

    // Computing new lines
    strRawValue.split("").forEach((curChar, i) => {
      oTextarea.value += curChar;

      if (curChar === " " || curChar === "-" || curChar === "+") {
        nLastWrappingIndex = i;
      }

      if (oTextarea.scrollWidth > nEmptyWidth) {
        let buffer = "";
        if (nLastWrappingIndex >= 0) {
          for (let j = nLastWrappingIndex + 1; j < i; j++) {
            buffer += strRawValue.charAt(j);
          }
          nLastWrappingIndex = -1;
        }
        buffer += curChar;
        oTextarea.value = oTextarea.value.substr(
          0,
          oTextarea.value.length - buffer.length
        );
        oTextarea.value += "\n" + buffer;
      }
    });
    oTextarea.setAttribute("wrap", "");
    return oTextarea.value;
  },
});

export function initDocumentToSign(parent) {
  return session.is_bound.then(function () {
    // Manually add 'sign' to module list and load the
    // translations.
    const modules = ["sign", "web"];
    return session.load_translations(modules).then(function () {
      const documentPage = new SignableDocument(parent);
      return documentPage.attachTo($("body")).then(function () {
        // Geolocation
        const askLocation = $("#o_sign_ask_location_input").length > 0;
        if (askLocation && navigator.geolocation) {
          navigator.geolocation.getCurrentPosition(function (position) {
            const { latitude, longitude } = position.coords;
            const coords = { latitude, longitude };
            documentPage.coords = coords;
            if (documentPage.requestState !== 'shared') {
              ajax.jsonRpc(
                  `/sign/save_location/${documentPage.requestID}/${documentPage.accessToken}`,
                "call",
                coords
              );
            }
          });
        }
      });
    });
  });
}
