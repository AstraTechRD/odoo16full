/** @odoo-module **/

"use strict";

import config from "web.config";
import core from "web.core";
import Dialog from "web.Dialog";
import Widget from "web.Widget";

const { _t } = core;

const PinchItemMixin = {
  events: {
    "touchstart .o_pinch_item": "_onResetPinchCache",
    "touchmove .o_pinch_item": "_onPinchMove",
    "touchend .o_pinch_item": "_onResetPinchCache",
  },

  /**
   * @param {Object} options
   * @param {jQuery} options.$target
   *        Element used as target where the pinch must be applied
   * @param {function} [options.increaseDistanceHandler]
   *        Handler called when the distance pinched between the 2 pointer is decreased
   * @param {function} [options.decreaseDistanceHandler]
   *        Handler called when the distance pinched between the 2 pointer is increased
   * }
   */
  init(options) {
    this.prevDiff = null;
    this.$target = options.$target;
    this.$target.addClass("o_pinch_item");
    this.increaseDistanceHandler = options.increaseDistanceHandler
      ? options.increaseDistanceHandler
      : () => {};
    this.decreaseDistanceHandler = options.decreaseDistanceHandler
      ? options.decreaseDistanceHandler
      : () => {};
  },

  //--------------------------------------------------------------------------
  // Handlers
  //--------------------------------------------------------------------------

  /**
   * This function implements a 2-pointer horizontal pinch/zoom gesture.
   *
   * If the distance between the two pointers has increased (zoom in),
   * distance is decreasing (zoom out)
   *
   * This function sets the target element's border to "dashed" to visually
   * indicate the pointer's target received a move event.
   * @param ev
   * @private
   */
  _onPinchMove(ev) {
    const touches = ev.touches;
    // If two pointers are down, check for pinch gestures
    if (touches.length === 2) {
      // Calculate the current distance between the 2 fingers
      const deltaX = touches[0].pageX - touches[1].pageX;
      const deltaY = touches[0].pageY - touches[1].pageY;
      const curDiff = Math.hypot(deltaX, deltaY);
      if (this.prevDiff === null) {
        this.prevDiff = curDiff;
      }
      const scale = this.prevDiff / curDiff;
      if (scale < 1) {
        this.decreaseDistanceHandler(ev);
      } else if (scale > 1) {
        this.increaseDistanceHandler(ev);
      }
    }
  },

  /**
   *
   * @private
   */
  _onResetPinchCache() {
    this.prevDiff = null;
  },
};

export const PDFIframe = Widget.extend(
  Object.assign({}, PinchItemMixin, {
    init: function (parent, attachmentLocation, editMode, datas, role, roleName) {
      this._super(parent);
      this.attachmentLocation = attachmentLocation;
      this.editMode = editMode;
      this.requestState = parent.requestState;
      this.templateID = parent.templateID;
      this.templateItemsInProgress = parent.templateItemsInProgress;
      this.templateName = parent.templateName;
      this.templateEditable = parent.templateEditable;
      this.authMethod = parent.authMethod;
      // sets datas values to this
      Object.keys(datas).forEach((dataName) => {
        this._set_data(dataName, datas[dataName]);
      });

      this.normalSize = () => this.$(".page").first().innerHeight() * 0.015;
      this.role = role || 0;
      this.roleName = roleName;
      this.configuration = {};
      this.deletedSignItemIds = [];
      this.minID = -(2 ** 30);

      let _res, _rej;
      this.fullyLoaded = new Promise(function (resolve, reject) {
        _res = resolve;
        _rej = reject;
      }).then(() => {
        // Init pinch event only after have the pdf loaded
        PinchItemMixin.init.call(this, {
          $target: this.$el.find("#viewerContainer #viewer"),
          decreaseDistanceHandler: () => this.$("button#zoomIn").click(),
          increaseDistanceHandler: () => this.$("button#zoomOut").click(),
        });
        return arguments;
      });
      this.fullyLoaded.resolve = _res;
      this.fullyLoaded.reject = _rej;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Adds buttons for completed signature download/certificate download
     */
    _managedToolBarButtonsForSignedDocument() {
      const cloneDownloadButton = ($button) =>
        $button
          .clone()
          .attr("id", $button.attr("id") + "_completed")
          .prop("title", _t("Download Document"))
          .on(
            "click",
            () =>
              (window.location = this.attachmentLocation.replace(
                "origin",
                "completed"
              ))
          );
      // inside toolbar
      const $buttonDownloadPrimary = this.$("button#download");
      $buttonDownloadPrimary.after(
        cloneDownloadButton($buttonDownloadPrimary).show()
      );
      // inside the more button on the toolbar
      const $buttonDownloadSecondary = this.$("button#secondaryDownload");
      const $buttonDownloadSecond = cloneDownloadButton(
        $buttonDownloadSecondary
      );
      if ($buttonDownloadSecond.hasClass("secondaryToolbarButton")) {
        $buttonDownloadSecond.find("span").text(_t("Download Document"));
      }
      $buttonDownloadSecondary.after($buttonDownloadSecond);
    },
    /**
     * Binds data received when initializing PDFIframe widget to self.dataName
     * @param { String } dataName
     * @param {*} data
     */
    _set_data: function (dataName, data) {
      this[dataName] = {};
      if (data instanceof jQuery) {
        const self = this;
        data
          .each(function (i, el) {
            self[dataName][$(el).data("id")] = $(el).data();
          })
          .detach();
      } else {
        data.forEach((item) => {
          this[dataName][item.id] = item;
        });
      }
    },

    start: function () {
      const self = this;
      self.$iframe = self.$el; // this.$el will be changed to the iframe html tag once loaded
      self.pdfView = self.$iframe.attr("readonly") === "readonly";
      self.readonlyFields = self.pdfView || self.editMode;

      let viewerURL =
        "/web/static/lib/pdfjs/web/viewer.html?unique=" +
        +new Date() +
        "&file=";
      viewerURL +=
        encodeURIComponent(self.attachmentLocation)
          .replace(/'/g, "%27")
          .replace(/"/g, "%22") + "#page=1";
      viewerURL += config.device.isMobile
        ? "&zoom=page-fit"
        : "&zoom=page-width";
      self.$iframe.ready(function () {
        self.waitForPDF();
      });
      self.$iframe.attr("src", viewerURL);

      return Promise.all([self._super(), self.fullyLoaded]);
    },

    /**
     * Waits for PDF to be loaded by PDFjs lib
     */
    waitForPDF: function () {
      if (this.$iframe.contents().find("#errorMessage").is(":visible")) {
        this.fullyLoaded.resolve();
        return Dialog.alert(
          this,
          _t("Need a valid PDF to add signature fields !")
        );
      }

      const nbPages = this.$iframe.contents().find(".page").length;
      const nbLayers = this.$iframe.contents().find(".textLayer").length;
      if (nbPages > 0 && nbLayers > 0) {
        this.nbPages = nbPages;
        this.doPDFPostLoad();
      } else {
        setTimeout(() => this.waitForPDF(), 50);
      }
    },

    doPDFPostLoad: function () {
      const self = this;
      const signature_keys = Object.keys(this.signatureItems);
      const is_all_signed =
        signature_keys.filter((key) => this.signatureItems[key].value).length ==
        signature_keys.length;
      this.setElement(this.$iframe.contents().find("html"));

      this.$(
        "#pageRotateCw, #pageRotateCcw, " +
          "#openFile, #presentationMode, #viewBookmark, #print, #download, " +
          "#secondaryOpenFile, #secondaryPresentationMode, #secondaryViewBookmark, #secondaryPrint, #secondaryDownload"
      )
        .add(this.$("#lastPage").next())
        .hide();
      this.$("button#print").prop("title", _t("Print original document"));
      this.$("button#download").prop("title", _t("Download original document"));
      // The following attribute is used to prevent Chrome to auto complete the text 'input' of sign items
      // The following password input is used to decrypt the PDF when needed.
      // The autocomplete="off" doesn't work anymore. https://bugs.chromium.org/p/chromium/issues/detail?id=468153#c164
      this.$(":password").attr("autocomplete", "new-password");
      // hack to prevent opening files in the pdf js viewer when dropping files/images to the viewerContainer
      // ref: https://stackoverflow.com/a/68939139
      this.$("#viewerContainer")[0].addEventListener('drop', (e) => {
        e.stopImmediatePropagation();
        e.stopPropagation();
      }, true);
      if (this.readonlyFields && !this.editMode && is_all_signed) {
        this._managedToolBarButtonsForSignedDocument();
      }

      config.device.isMobile
        ? this.$("button#zoomIn").click()
        : this.$("button#zoomOut").click().click();

      for (let i = 1; i <= this.nbPages; i++) {
        this.configuration[i] = [];
      }

      const assets_def = this._rpc({
        route: "/sign/render_assets_pdf_iframe",
        params: {
          args: [
            {
              debug: config.isDebug(),
            },
          ],
        },
      }).then(function (html) {
        $.each($(html), function (key, value) {
          self.$("head")[0].appendChild(value);
        });
      });

      $(
        Object.keys(this.signatureItems).map(function (id) {
          return self.signatureItems[id];
        })
      )
        .sort(function (a, b) {
          if (a.page !== b.page) {
            return a.page - b.page;
          }

          if (Math.abs(a.posY - b.posY) > 0.01) {
            return a.posY - b.posY;
          } else {
            return a.posX - b.posX;
          }
        })
        .each(function (i, el) {
          const $signatureItem = self.createSignItem(
            self.types[parseInt(el.type || el.type_id[0])],
            !!el.required,
            parseInt(
              el.responsible || (el.responsible_id && el.responsible_id[0])
            ) || 0,
            parseFloat(el.posX),
            parseFloat(el.posY),
            parseFloat(el.width),
            parseFloat(el.height),
            el.value,
            el.frame_value,
            el.option_ids,
            el.name,
            el.responsible_name ? el.responsible_name : "",
            el.alignment,
            false,
            false,
          );
          $signatureItem.data({ itemId: el.id, order: i });
          self.configuration[parseInt(el.page)].push($signatureItem);
        });

      assets_def.then(async function () {
        refresh_interval();

        self.$(".o_sign_sign_item").each(function (i, el) {
          self.updateSignItem($(el), false);
        });
        self.updateFontSize();

        self
          .$("#viewerContainer")
          .css("visibility", "visible")
          .animate({ opacity: 1 }, 1000);

        self.fullyLoaded.resolve();

        /**
         * This function is called every 2sec to check if the PDFJS viewer did not detach some signature items.
         * Indeed, when scrolling, zooming, ... the PDFJS viewer replaces page content with loading icon, removing
         * any custom content with it.
         * Previous solutions were tried (refresh after scroll, on zoom click, ...) but this did not always work
         * for some reason when the PDF was too big.
         */
        function refresh_interval() {
          try {
            // if an error occurs it means the iframe has been detach and will be reinitialized anyway (so the interval must stop)
            self.refreshSignItems();
            self.refresh_timer = setTimeout(refresh_interval, 2000);
          } catch (_e) {}
        }
      });
    },

    refreshSignItems: function () {
      Object.keys(this.configuration).forEach((page) => {
        const $pageContainer = this.$('.page[data-page-number="' + page + '"]');
        this.configuration[page].forEach((item) => {
          if (!item.parent().hasClass("page")) {
            $pageContainer.append(item);
          }
        });
      });
      this.updateFontSize();
    },

    display_select_options: function (
      $container,
      options,
      selected_options,
      readonly,
      active_option
    ) {
      readonly = readonly === undefined ? false : readonly;
      $container.empty();

      selected_options.forEach(function (id, index) {
        if (index !== 0) {
          $container.append(
            $('<span class="o_sign_option_separator">/</span>')
          );
        }
        const $op = $('<span class="o_sign_item_option"/>').text(
          options[id].value
        );
        $op.data("id", id);
        $container.append($op);
        if (!readonly) {
          $op.on("click", click_handler);
        }
      });

      if (active_option) {
        $container.parent().val(active_option);
        $container.parent().trigger("input");
        select_option($container, active_option);
      }
      function select_option($container, option_id) {
        const $selected_op = $container.find(":data(id)").filter(function () {
          return $(this).data("id") === option_id;
        });
        const $other_options = $container.find(":data(id)").filter(function () {
          return $(this).data("id") !== option_id;
        });
        $selected_op.addClass("o_sign_selected_option");
        $selected_op.removeClass("o_sign_not_selected_option");
        $other_options.removeClass("o_sign_selected_option");
        $other_options.addClass("o_sign_not_selected_option");
      }

      function click_handler(e) {
        const id = $(e.target).data("id");
        $container = $(e.target.parentElement);
        $container.parent().val(id);
        $container.parent().trigger("input");
        select_option($container, id);
      }
    },

    updateFontSize: function () {
      const self = this;
      const normalSize = self.normalSize();
      this.$(".o_sign_sign_item").each(function (i, el) {
        const $elem = $(el);
        self.updateSignItemFontSize($elem, normalSize);
      });
    },

    /**
     * @param {jQuery} $signItem the signItem the font size has to be set
     * @param {number} normalSize the normal font size
     */
    updateSignItemFontSize: function ($signItem, normalSize) {
      let size = parseFloat($signItem.css("height"));
      if (
        ["signature", "initial", "textarea", "selection"].includes(
          this.types[$signItem.data("type")].item_type
        )
      ) {
        size = normalSize;
      }
      $signItem.css("font-size", size * 0.8);
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
      option_ids,
      name,
      tooltip,
      alignment,
      isSignItemEditable,
      updated=true
    ) {
      // jQuery.data parse 0 as integer, but 0 is not considered falsy for signature item
      if (value === 0) {
        value = "0";
      }
      const readonly =
        this.readonlyFields ||
        (responsible > 0 && responsible !== this.role) ||
        !!value;
      const selected_options = option_ids || [];
      const $signatureItem = $(
        core.qweb.render("sign.sign_item", {
          editMode: isSignItemEditable || this.editMode,
          readonly: isSignItemEditable || readonly,
          role: tooltip,
          type: type.item_type,
          value: value || "",
          frame_value: frame_value || "",
          options: selected_options,
          placeholder: name || "",
          isSignItemEditable: isSignItemEditable,
        })
      );

      if (this.readonlyFields) {
        $signatureItem.addClass("o_readonly_mode");
      }

      if (type.item_type === "selection") {
        const $options_display = $signatureItem.find(
          ".o_sign_select_options_display"
        );
        this.display_select_options(
          $options_display,
          this.select_options,
          selected_options,
          readonly,
          value
        );
      }
      return $signatureItem
        .data({
          itemId: Math.floor(Math.random() * this.minID) - 1,
          type: type.id,
          required: required,
          responsible: responsible,
          posx: posX,
          posy: posY,
          width: width,
          height: height,
          name: name,
          option_ids: option_ids,
          alignment: alignment,
        })
        .data({
          hasValue: !!value,
          typeData: type,
          updated: updated,
          isEditMode: this.isSignItemEditable,
        })
        .toggle(!!value || this.requestState != "signed");
    },

    /**
     * Deletes or detaches a sign item
     * @param { jQuery } $item sign item to be deleted or detached
     * @param { Boolean } detach if set to true, sign item will be detached instead of removed
     */
    deleteSignItem: function ($signItem) {
      this.deleteSignItemFromConfiguration($signItem);
      this.deletedSignItemIds.push($signItem.data('itemId'));
      $signItem.remove();
    },

    /**
     * detach a sign item from the DOM (its page)
     * @param {jQuery} $signItem the signItem to be detached
     */
    detachSignItem: function ($signItem) {
      this.deleteSignItemFromConfiguration($signItem);
      $signItem.detach();
    },

    deleteSignItemFromConfiguration: function ($signItem) {
      const pageNo = parseInt($signItem.parent().data('page-number'));
      for(let i = 0 ; i < this.configuration[pageNo].length ; i++) {
        if(this.configuration[pageNo][i].data('itemId') === $signItem.data('itemId')) {
          this.configuration[pageNo].splice(i, 1);
          break;
        }
      }
    },

    updateSignItem: function ($signatureItem, updated=true) {
      const setPosition = (pos, dimension) => {
        if (pos < 0) {
          return 0;
        } else if (pos + dimension > 1.0) {
          return 1.0 - dimension;
        }
        return pos;
      };
      const width = $signatureItem.data("width"),
        height = $signatureItem.data("height");
      const posX = setPosition($signatureItem.data("posx"), width),
        posY = setPosition($signatureItem.data("posy"), height);

      const alignment = $signatureItem.data("alignment");
      $signatureItem
        .data({
          posx: Math.round(posX * 1000) / 1000,
          posy: Math.round(posY * 1000) / 1000,
        })
        .css({
          left: posX * 100 + "%",
          top: posY * 100 + "%",
          width: width * 100 + "%",
          height: height * 100 + "%",
          textAlign: alignment,
        });

      const resp = $signatureItem.data("responsible");
      const isSignItemRequired =
        $signatureItem.data("required") &&
        (this.editMode || resp <= 0 || resp === this.role);
      const isSignItemNotSigned =
        this.pdfView ||
        !!$signatureItem.data("hasValue") ||
        (resp !== this.role && resp > 0 && !this.editMode);
      $signatureItem
        .toggleClass("o_sign_sign_item_required", isSignItemRequired)
        .toggleClass("o_sign_sign_item_pdfview", isSignItemNotSigned);
      $signatureItem.data({'updated': updated});
    },

    disableItems: function () {
      this.$(".o_sign_sign_item")
        .addClass("o_sign_sign_item_pdfview")
        .removeClass("ui-selected");
    },

    destroy: function () {
      clearTimeout(this.refresh_timer);
      this._super.apply(this, arguments);
    },
  })
);

export default PDFIframe;
