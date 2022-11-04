/** @odoo-module **/

"use strict";

import core from "web.core";
import config from "web.config";
import Dialog from "web.Dialog";
import { PDFIframe } from "@sign/js/common/PDFIframe";
import { sign_utils } from "@sign/js/backend/utils";
import SmoothScrollOnDrag from "web/static/src/js/core/smooth_scroll_on_drag.js";

const { _t } = core;

const InitialAllPagesDialog = Dialog.extend({
  template: "sign.initial_all_pages_dialog",

  init: function (parent, parties, options) {
    options = options || {};

    options.title = options.title || _t("Add Initials");
    options.size = options.size || "medium";

    if (!options.buttons) {
      options.buttons = this.addDefaultButtons();
    }

    this._super(parent, options);

    this.parties = parties;
  },

  start: function () {
    this.$responsibleSelect = this.$(".o_sign_responsible_select_initials");
    return this._super.apply(this, arguments).then(() => {
      sign_utils.setAsResponsibleSelect(
        this.$responsibleSelect.find("select"),
        this.getParent().currentRole,
        this.parties
      );
    });
  },

  open: function ($signatureItem) {
    this.$currentTarget = $signatureItem;
    this._super.apply(this, arguments);
  },

  updateTargetResponsible: function () {
    const resp = parseInt(this.$responsibleSelect.find("select").val());
    this.getParent().currentRole = resp;
    this.$currentTarget.data("responsible", resp);
  },

  addDefaultButtons() {
    const buttons = [];
    buttons.push({
      text: _t("Add once"),
      classes: "btn-primary",
      close: true,
      click: (e) => {
        this.updateTargetResponsible();
        this.$currentTarget.trigger("itemChange");
      },
    });
    buttons.push({
      text: _t("Add to all pages"),
      classes: "btn-secondary",
      close: true,
      click: (e) => {
        this.updateTargetResponsible();
        this.$currentTarget.draggable("destroy").resizable("destroy");
        this.$currentTarget.trigger("itemClone");
      },
    });
    return buttons;
  },
});

PDFIframe.include({
  init: function () {
    sign_utils.resetResponsibleSelectConfiguration();
    sign_utils.resetOptionsSelectConfiguration();
    this._super.apply(this, arguments);
    this.events = Object.assign(this.events || {}, {
      "itemClone .o_sign_sign_item": function (e) {
        const $target = $(e.target);
        this.updateSignItem($target);
        const newElems = [];

        for (let i = 1; i <= this.nbPages; i++) {
          const hasSignatureInPage = this.configuration[i].some(
            (item) => this.types[item.data("type")].item_type === "signature"
          );
          if (!hasSignatureInPage) {
            const $newElem = $target.clone(true).off();
            $newElem.data({itemId: Math.floor(Math.random() * this.minID) - 1});
            this.enableCustom($newElem);
            this.configuration[i].push($newElem);
            newElems.push($newElem);
          }
        }

        this.deleteSignItem($target);
        this.refreshSignItems();
        if (typeof this.postItemClone === "function") {
          this.postItemClone(newElems);
        }
      },
    });
  },

  doPDFPostLoad: function () {
    this.fullyLoaded.then(this._doPDFFullyLoaded.bind(this));
    this._super.apply(this, arguments);
  },

  getToolbarTypesArray: function () {
    return [];
  },

  _doPDFFullyLoaded: function () {
    if ((this.editMode && !this.$iframe.prop("disabled")) ||
       (!this.readonlyFields && this.templateEditable && !config.device.isMobile)
    ) {
      // set helper lines when dragging
      this.$hBarTop = $("<div/>");
      this.$hBarBottom = $("<div/>");
      this.$hBarTop
        .add(this.$hBarBottom)
        .addClass("o_sign_drag_helper o_sign_drag_top_helper");
      this.$vBarLeft = $("<div/>");
      this.$vBarRight = $("<div/>");
      this.$vBarLeft
        .add(this.$vBarRight)
        .addClass("o_sign_drag_helper o_sign_drag_side_helper");

      this.$fieldTypeToolbar = $("<div/>").addClass(
        "o_sign_field_type_toolbar d-flex flex-column"
      );
      this.$fieldTypeToolbar.prependTo(this.$("body"));

      const smoothScrollOptions = {
        scrollBoundaries: {
          right: false,
          left: false,
        },
        jQueryDraggableOptions: {
          cancel: false,
          distance: 0,
          cursorAt: { top: 5, left: 5 },
          helper: (e) => {
            const type = this.types[$(e.currentTarget).data("item-type-id")];
            const $signatureItem = this.createSignItem(
              type,
              true,
              this.currentRole,
              0,
              0,
              type.default_width || type.defaultWidth,
              type.default_height || type.defaultHeight,
              "",
              "",
              [],
              type.placeholder,
              "",
              "",
              this.isSignItemEditable,
            );
            $signatureItem.addClass("o_sign_sign_item_to_add");

            this.$(".page").first().append($signatureItem);
            this.updateSignItem($signatureItem);
            $signatureItem
              .css("width", $signatureItem.css("width"))
              .css("height", $signatureItem.css("height")); // Convert % to px
            this.updateSignItemFontSize($signatureItem, this.normalSize());
            $signatureItem.detach();

            return $signatureItem;
          },
        },
      };

      const typesArray = this.getToolbarTypesArray();
      const $fieldTypeButtons = $(
        core.qweb.render("sign.type_buttons", {
          sign_item_types: typesArray,
        })
      );
      if ($fieldTypeButtons) {
        $fieldTypeButtons.appendTo(this.$fieldTypeToolbar);
      }
      const $fieldTypeButtonItems = $fieldTypeButtons.children(
        ".o_sign_field_type_button"
      );
      this.buttonsDraggableComponent = new SmoothScrollOnDrag(
        this,
        $fieldTypeButtonItems,
        this.$("#viewerContainer"),
        smoothScrollOptions
      );
      $fieldTypeButtonItems.each((i, el) => {
        this.enableCustomBar($(el));
      });

      this.$(".page").droppable({
        accept: "*",
        tolerance: "touch",
        drop: (e, ui) => {
          // the 'o_sign_sign_item_to_add' is added once a sign item is dragged.
          // two consecutive pages have overlaps borders,
          // we remove the o_sign_sign_item_to_add once the sign item is dropped
          // to make sure ths sign item will not be dropped into multiple pages
          if (!ui.helper.hasClass("o_sign_sign_item_to_add")) {
            return true;
          }
          ui.helper.removeClass("o_sign_sign_item_to_add");

          const $parent = $(e.target);
          const pageNo = parseInt($parent.data("page-number"));

          let $signatureItem;
          if (ui.draggable.hasClass("o_sign_sign_item")) {
            let pageNoOri = parseInt(
              $(ui.draggable).parent().attr("data-page-number")
            );
            if (pageNoOri === pageNo) {
              // if sign_item is dragged to its previous page
              return true;
            }
            $signatureItem = $(ui.draggable);
            this.detachSignItem($signatureItem);
          } else {
            $signatureItem = ui.helper
              .clone(true).off()
              .removeClass()
              .addClass("o_sign_sign_item o_sign_sign_item_required");
            this.enableCustom($signatureItem);
          }
          const posX =
            (ui.offset.left - $parent.find(".textLayer").offset().left) /
            $parent.innerWidth();
          const posY =
            (ui.offset.top - $parent.find(".textLayer").offset().top) /
            $parent.innerHeight();
          $signatureItem.data({ posx: posX, posy: posY });

          this.configuration[pageNo].push($signatureItem);
          this.refreshSignItems();

          if (!ui.draggable.hasClass("o_sign_sign_item")) {
            this.updateSignItem($signatureItem);
            if (this.types[$signatureItem.data("type")].item_type === "initial") {
              new InitialAllPagesDialog(this, this.parties).open($signatureItem);
            }
            if (typeof this.postItemDrop === "function") {
                this.postItemDrop($signatureItem);
            }
          }

          return false;
        },
      });
    }
  },

  enableCustom: function ($signatureItem) {
    $signatureItem.prop(
      "field-type",
      this.types[$signatureItem.data("type")].item_type
    );
    $signatureItem.prop(
      "field-name",
      this.types[$signatureItem.data("type")].name
    );

    const smoothScrollOptions = {
      scrollBoundaries: {
        right: false,
        left: false,
      },
      jQueryDraggableOptions: {
        containment: $("#viewerContainer"),
        distance: 0,
        classes: { "ui-draggable-dragging": "o_sign_sign_item_to_add" },
        handle: ".o_sign_config_handle",
        scroll: false,
      },
    };
    if (!$signatureItem.hasClass("ui-draggable")) {
      this.signItemsDraggableComponent = new SmoothScrollOnDrag(
        this,
        $signatureItem,
        this.$("#viewerContainer"),
        smoothScrollOptions
      );
    }
    if (!$signatureItem.hasClass("ui-resizable")) {
      $signatureItem
        .resizable({
          containment: "parent",
        })
        .css("position", "absolute");
    }

    $signatureItem.off("dragstop").on("dragstop", function (e, ui) {
      const $parent = $(e.target).parent();
      $signatureItem.data({
        posx:
          Math.round(
            ((ui.offset.left - $parent.find(".textLayer").offset().left) /
              $parent.innerWidth()) *
              1000
          ) / 1000,
        posy:
          Math.round(
            ((ui.offset.top - $parent.find(".textLayer").offset().top) /
              $parent.innerHeight()) *
              1000
          ) / 1000,
      });
    });

    $signatureItem.off("resizestop").on("resizestop", function (e, ui) {
      $signatureItem.data({
        width:
          Math.round(
            (ui.size.width / $signatureItem.parent().innerWidth()) * 1000
          ) / 1000,
        height:
          Math.round(
            (ui.size.height / $signatureItem.parent().innerHeight()) * 1000
          ) / 1000,
      });
    });

    $signatureItem.on("dragstop resizestop", (e, ui) => {
      this.updateSignItem($signatureItem);
      if (typeof this.postItemDragResizeStop === "function") {
        this.postItemDragResizeStop($signatureItem);
      }
    });

    this.enableCustomBar($signatureItem);
  },

  enableCustomBar: function ($item) {
    $item.on("dragstart resizestart", (e, ui) => {
      const $target = $(e.target);
      if (
        !$target.hasClass("ui-draggable") &&
        !$target.hasClass("ui-resizable")
      ) {
        // The element itself is not draggable or resizable
        // Let the event propagate to its parents
        return;
      }
      start.call(this, ui.helper);
    });
    $item
      .find(".o_sign_config_area .o_sign_config_handle")
      .on("mousedown", (e) => {
        start.call(this, $item);
        process.call(this, $item);
      });
    $item.on("drag resize", (e, ui) => {
      const $target = $(e.target);
      if (
        !$target.hasClass("ui-draggable") &&
        !$target.hasClass("ui-resizable")
      ) {
        // The element itself is not draggable or resizable
        // Let the event propagate to its parents
        return;
      }
      process.call(this, ui.helper);
    });
    $item.on("dragstop resizestop", (e, ui) => {
      end.call(this);
    });
    $item
      .find(".o_sign_config_area .o_sign_config_handle")
      .on("mouseup", (e) => {
        end.call(this);
      });

    function start($helper) {
      this.$hBarTop.detach().insertAfter($helper).show();
      this.$hBarBottom.detach().insertAfter($helper).show();
      this.$vBarLeft.detach().insertAfter($helper).show();
      this.$vBarRight.detach().insertAfter($helper).show();
    }
    function process($helper) {
      const helperBoundingClientRect = $helper.get(0).getBoundingClientRect();
      this.$hBarTop.css("top", helperBoundingClientRect.top);
      this.$hBarBottom.css(
        "top",
        helperBoundingClientRect.top + parseFloat($helper.css("height")) - 1
      );
      this.$vBarLeft.css("left", helperBoundingClientRect.left);
      this.$vBarRight.css(
        "left",
        helperBoundingClientRect.left + parseFloat($helper.css("width")) - 1
      );
    }
    function end() {
      this.$hBarTop.hide();
      this.$hBarBottom.hide();
      this.$vBarLeft.hide();
      this.$vBarRight.hide();
    }
  },
});
