/** @odoo-module **/

"use strict";

import AbstractAction from "web.AbstractAction";
import config from "web.config";
import core from "web.core";
import { sprintf } from "@web/core/utils/strings";
import Dialog from "web.Dialog";
import framework from "web.framework";
import session from "web.session";
import Widget from "web.Widget";
import { PDFIframe } from "@sign/js/common/PDFIframe";
import { sign_utils } from "@sign/js/backend/utils";
import StandaloneFieldManagerMixin from "web.StandaloneFieldManagerMixin";
import {
  FormFieldMany2ManyTags,
} from "web.relational_fields";
import { multiFileUpload } from "@sign/js/backend/multi_file_upload";

const { _t } = core;

const SignItemCustomPopover = Widget.extend({
  template: "sign.sign_item_custom_popover",
  events: {
    "click .o_sign_delete_field_button": function (e) {
      this.$currentTarget.popover("hide");
      this.$currentTarget.trigger("itemDelete");
    },
    "click .o_sign_align_button": function (e) {
      this.$(".o_sign_field_align_group .o_sign_align_button").removeClass(
        "btn-primary"
      );
      e.target.classList.add("btn-primary");
    },
    "click .o_sign_validate_field_button": function (e) {
      this.hide();
    },
  },

  init: function (parent, parties, options, select_options) {
    options = options || {};
    this._super(parent, options);
    //TODO: Add buttons for save, discard and remove.
    this.parties = parties;
    this.select_options = select_options;
    this.debug = config.isDebug();
  },

  start: function () {
    this.$responsibleSelect = this.$(".o_sign_responsible_select");
    this.$optionsSelect = this.$(".o_sign_options_select");

    return this._super().then(() => {
      const fieldType = this.$currentTarget.prop("field-type");
      if (["text", "textarea"].includes(fieldType)) {
        this.$(
          '.o_sign_field_align_group button[data-align="' +
            this.$currentTarget.data("alignment") +
            '"]'
        ).addClass("btn-primary");
      } else {
        this.$(".o_sign_field_align_group").hide();
      }
      sign_utils.setAsResponsibleSelect(
        this.$responsibleSelect.find("select"),
        this.$currentTarget.data("responsible"),
        this.parties
      );
      const $optionsSelectInput = this.$optionsSelect.find("input");
      sign_utils.setAsOptionsSelect(
        $optionsSelectInput,
        this.$currentTarget.data("itemId"),
        this.$currentTarget.data("option_ids"),
        this.select_options
      );
      $optionsSelectInput.data("item_options", $optionsSelectInput.select2("val"));
      this.$('input[type="checkbox"]').prop(
        "checked",
        this.$currentTarget.data("required")
      );

      this.$("#o_sign_name").val(this.$currentTarget.data("name") || "");
      this.title = this.$currentTarget.prop("field-name");
      if (fieldType !== "selection") {
        this.$(".o_sign_options_group").hide();
      }
    });
  },

  create: function ($targetEl) {
    this.$currentTarget = $targetEl;
    this.$elPopover = $("<div class='o_sign_item_popover'/>");
    const buttonClose = '<button class="o_sign_close_button">&times;</button>';
    const isRTL = _t.database.parameters.direction === "rtl";

    this.appendTo(this.$elPopover).then(() => {
      const options = {
        title: this.title + buttonClose,
        content: () => {
          return this.$el;
        },
        html: true,
        placement: isRTL ? "left" : "right",
        trigger: "focus",
        container: ".o_sign_template",
      };
      this.$currentTarget.popover(options).one("inserted.bs.popover", (e) => {
        $(".popover").addClass("o_popover_offset");
        $(".o_sign_close_button").on("click", (e) => {
          this.$currentTarget.popover("hide");
        });
      });
      this.$currentTarget.popover("toggle");
      //  Don't display placeholders of checkboxes: empty element
      if (this.$currentTarget.prop("field-type") === "checkbox") {
        $(".o_popover_placeholder").text("");
      }
    });
  },
  hide: function () {
    const resp = parseInt(this.$responsibleSelect.find("select").val());
    const selected_options = this.$optionsSelect
      .find("#o_sign_options_select_input")
      .data("item_options");
    const required = this.$('input[type="checkbox"]').prop("checked");
    const alignment = this.$(
      ".o_sign_field_align_group .o_sign_align_button.btn-primary"
    ).data("align");
    const name = odoo.debug ? this.$('#o_sign_name').val() : this.$currentTarget.data('name') || "";
    this.getParent().currentRole = resp;
    if (this.$currentTarget.prop("field-type") != "checkbox") {
      this.$currentTarget.find(".o_placeholder").text(name);
    }
    this.$currentTarget
      .data({
        responsible: resp,
        alignment: alignment,
        required: required,
        name: name,
        option_ids: selected_options,
      })
      .trigger("itemChange");
    this.$currentTarget.popover("hide");
  },
});

const EditablePDFIframe = PDFIframe.extend({
  init: function () {
    this._super.apply(this, arguments);
    if (this.editMode) {
      document.body.classList.add("o_block_scroll");
    }
    this.customPopovers = {};
    this.events = Object.assign(this.events || {}, {
      "itemChange .o_sign_sign_item": function (e) {
        this.updateSignItem($(e.target));
        this.$iframe.trigger("templateChange");
      },

      "itemDelete .o_sign_sign_item": function (e) {
        this.deleteSignItem($(e.target));
        this.$iframe.trigger("templateChange");
      },

      "click .o_sign_rotate": function (e) {
        const button = $(e.target);
        button.prepend('<i class="fa fa-spin fa-circle-o-notch"/>');
        button.attr("disabled", true);
        this._rotateDocument();
      },
    });
  },

  destroy: function () {
    this._super(...arguments);
    if (this.editMode) {
      document.body.classList.remove("o_block_scroll");
    }
  },

  getToolbarTypesArray: function () {
    return Object.values(this.types);
  },

  postItemDrop: function ($signatureItem) {
    this.$iframe.trigger("templateChange");
  },

  postItemDragResizeStop: function ($signatureItem) {
    $signatureItem.removeClass("ui-selected");
    this.$iframe.trigger("templateChange");
  },

  postItemClone: function (signItems) {
    this.$iframe.trigger("templateChange");
  },

  _doPDFFullyLoaded: function () {
    if (this.editMode) {
      if (this.$iframe.prop("disabled")) {
        const $div = $("<div/>").css({
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          "z-index": 110,
          opacity: 0.75,
        });
        this.$("#viewer").css("position", "relative").prepend($div);
        $div.on("click mousedown mouseup mouveover mouseout", function (e) {
          return false;
        });
      } else {
        // In the edit mode, a side bar will be added to the left of the pdfviewer
        // "margin-left:14rem" will be added to the pdfviewer to leave space for the sidebar
        // So, a "resize" must be triggered for the pdfviewer after its new css is added.
        // If not, when a pdf is opened with "page-width" there might be a horizontal scrollbar on the bottom of the pdfviewer
        // Unfortunately, it is hard to know when the css will be added.
        // So we manually add the css here and trigger the "resize"
        // css in iframe.css:
        // #outerContainer.o_sign_field_type_toolbar_visible {
        //     margin-left: 14rem;
        //     width: auto;
        // }
        this.$("#outerContainer").css("width", "auto");
        this.$("#outerContainer").css("margin-left", "14rem");
        this.$("#outerContainer").addClass("o_sign_field_type_toolbar_visible");
        this.$iframe.get(0).contentWindow.dispatchEvent(new Event("resize"));

        this.isSignItemEditable = false;
        const rotateButton = $(
          core.qweb.render("sign.rotate_pdf_button", {
            title: _t("Rotate Clockwise"),
          })
        );
        rotateButton.insertBefore(this.$("#print"));

        this.$("#viewer").selectable({
          appendTo: this.$("body"),
          filter: ".o_sign_sign_item",
        });

        $(document)
          .add(this.$el)
          .on("keyup", (e) => {
            if (e.which !== 46) {
              return true;
            }

            this.$(".ui-selected").each((i, el) => {
              this.deleteSignItem($(el));
              // delete the associated popovers. At this point, there should only be one popover
              const popovers = window.document.querySelectorAll(
                '[id^="popover"]'
              );
              popovers.forEach((popover) => {
                document.getElementById(popover.id).remove();
              });
            });
            this.$iframe.trigger("templateChange");
          });
      }

      this.$(".o_sign_sign_item").each((i, el) => {
        this.enableCustom($(el));
      });
    }

    this._super.apply(this, arguments);
  },

  enableCustom: function ($signatureItem) {
    const itemId = $signatureItem.data("itemId");
    const $configArea = $signatureItem.find(".o_sign_config_area");

    $configArea
      .find(".o_sign_item_display")
      .off("mousedown")
      .on("mousedown", (e) => {
        e.stopPropagation();
        const currentCustomPopoverExists = !!this.customPopovers[itemId];

        Object.keys(this.customPopovers).forEach((itemId) => {
          if (this.customPopovers[itemId]) {
            this._closePopover(itemId);
          }
        });

        if (!e.ctrlKey) {
          this.$(".ui-selected").removeClass("ui-selected");
          if (!currentCustomPopoverExists) {
            this.customPopovers[itemId] = new SignItemCustomPopover(
              this,
              this.parties,
              {
                field_name: $signatureItem[0]["field-name"],
                field_type: $signatureItem[0]["field-type"],
              },
              this.select_options
            );
            this.customPopovers[itemId].create($signatureItem);
            }
        }
        $signatureItem.addClass("ui-selected");
      });

    $configArea
      .find(".o_sign_config_handle")
      .off("mouseup")
      .on("mouseup", (e) => {
        if (!e.ctrlKey) {
          this
            .$(".o_sign_sign_item")
            .filter(function (i) {
              return this !== $signatureItem[0];
            })
            .removeClass("ui-selected");
        }
        $signatureItem.toggleClass("ui-selected");
      });

    $signatureItem
      .off("dragstart resizestart")
      .on("dragstart resizestart", (e, ui) => {
        if (!e.ctrlKey) {
          this.$(".o_sign_sign_item").removeClass("ui-selected");
        }
        $signatureItem.addClass("ui-selected");
      });



    this._super.apply(this, arguments);
  },

  enableCustomBar: function ($item) {
    const itemId = $item.data("itemId");
    $item.on("dragstart resizestart", (e, ui) => {
      if (this.customPopovers[itemId]) {
        this._closePopover(itemId);
      }
    });
    $item
      .find(".o_sign_config_area .o_sign_config_handle")
      .on("mousedown", (e) => {
        if (this.customPopovers[itemId]) {
          this._closePopover(itemId);
        }
      });

    this._super.apply(this, arguments);
  },

  _closePopover(itemId) {
    this.customPopovers[itemId].$currentTarget.popover("hide");
    this.customPopovers[itemId] = false;
  },

  updateSignItem: function ($signatureItem) {
    this._super.apply(this, arguments);

    if (this.editMode) {
      const responsibleName = this.parties[$signatureItem.data("responsible")]
        .name;
      const colorIndex = this.parties[$signatureItem.data("responsible")].color;
      const currentColor = $signatureItem
        .attr("class")
        .match(/o_color_responsible_\d+/);
      $signatureItem.removeClass(currentColor && currentColor[0]);
      $signatureItem.addClass("o_color_responsible_" + colorIndex);
      $signatureItem
        .find(".o_sign_responsible_display")
        .text(responsibleName)
        .prop("title", responsibleName);
      const option_ids = $signatureItem.data("option_ids") || [];
      const $options_display = $signatureItem.find(
          ".o_sign_select_options_display"
      );
      this.display_select_options(
        $options_display,
        this.select_options,
        option_ids
      );
    }
  },

  _rotateDocument: function () {
    this._rpc({
      model: "sign.template",
      method: "rotate_pdf",
      args: [this.getParent().templateID],
    }).then((response) => {
      if (response) {
        this.$("#pageRotateCw").click();
        this.$("#rotateCw").text("");
        this.$("#rotateCw").attr("disabled", false);
        this.refreshSignItems();
      } else {
        Dialog.alert(
          this,
          _t("Somebody is already filling a document which uses this template"),
          {
            confirm_callback: () => {
              this.getParent().go_back_to_kanban();
            },
          }
        );
      }
    });
  },
});
//TODO refactor
const TemplateAction = AbstractAction.extend(StandaloneFieldManagerMixin, {
  hasControlPanel: true,
  events: {
    "click .fa-pencil": function (e) {
      this.$templateNameInput.focus().select();
    },

    "input .o_sign_template_name_input": function (e) {
      this.$templateNameInput.attr(
        "size",
        this.$templateNameInput.val().length + 1
      );
    },

    "change .o_sign_template_name_input": function (e) {
      this.saveTemplate();
      if (this.$templateNameInput.val() === "") {
        this.$templateNameInput.val(this.initialTemplateName);
      }
    },

    "keydown .o_sign_template_name_input": function (e) {
      if (e.keyCode === 13) {
        this.$templateNameInput.blur();
      }
    },

    "templateChange iframe.o_sign_pdf_iframe": function (e) {
      this.saveTemplate();
    },

    "click .o_sign_template_send": function (e) {
      this.do_action("sign.action_sign_send_request", {
        additional_context: {
          active_id: this.templateID,
          sign_directly_without_mail: false,
        },
      });
    },

    "click .o_sign_template_sign_now": function (e) {
      this.do_action("sign.action_sign_send_request", {
        additional_context: {
          active_id: this.templateID,
          sign_directly_without_mail: true,
        },
      });
    },

    "click .o_sign_template_share": function (e) {
      this._rpc({
        model: 'sign.template',
        method: 'open_shared_sign_request',
        args: [[this.templateID]],
      }).then((action) => {
        this.do_action(action);
      });
    },

    "click .o_sign_template_save": function (e) {
      return this.do_action("sign.sign_template_action", {
        clear_breadcrumbs: true,
      });
    },

    "click .o_sign_template_edit_form": function (e) {
        return this.do_action({
            name: "Edit Template Form",
            type: "ir.actions.act_window",
            res_model: "sign.template",
            res_id: this.templateID,
            views: [[false, "form"]]
        });
      },

    "click .o_sign_template_next": function (e) {
      const templateName = e.target.getAttribute("template-name");
      const templateId = parseInt(e.target.getAttribute("template-id"));
      multiFileUpload.removeFile(templateId);
      this.do_action({
        type: "ir.actions.client",
        tag: "sign.Template",
        name: sprintf(_t('Template "%s"'), templateName),
        context: {
          sign_edit_call: "sign_template_edit",
          id: templateId,
          sign_directly_without_mail: false,
        },
      });
    },

    "click .o_sign_template_duplicate": function (e) {
      this.duplicateTemplate();
    },
  },
  custom_events: Object.assign({}, StandaloneFieldManagerMixin.custom_events, {
    field_changed: "_onFieldChanged",
  }),

  go_back_to_kanban: function () {
    return this.do_action("sign.sign_template_action", {
      clear_breadcrumbs: true,
    });
  },

  init: function (parent, options) {
    this._super.apply(this, arguments);
    StandaloneFieldManagerMixin.init.call(this);

    if (options.context.id === undefined) {
      return;
    }

    this.templateID = options.context.id;
    this.actionType = options.context.sign_edit_call
      ? options.context.sign_edit_call
      : "";
    this.rolesToChoose = {};

    const nextTemplate = multiFileUpload.getNext();
    this.nextTemplate = nextTemplate ? nextTemplate : false;
  },

  renderButtons: function () {
    this.$buttons = $(
      core.qweb.render("sign.template_cp_buttons", {
        widget: this,
        action_type: this.actionType,
      })
    );
  },

  willStart: function () {
    if (this.templateID === undefined) {
      return this._super.apply(this, arguments);
    }
    const set_manage_template_access = session.user_has_group('sign.manage_template_access').then(res => {this.manage_template_access = res;});
    return Promise.all([set_manage_template_access, this._super(), this.perform_rpc()]);
  },
  // TODO: probably this can be removed
  createTemplateTagsField: function () {
    const self = this;
    const params = {
      modelName: "sign.template",
      res_id: self.templateID,
      fields: {
        id: {
          type: "integer",
        },
        name: {
          type: "char",
        },
        tag_ids: {
          relation: "sign.template.tag",
          type: "many2many",
          relatedFields: {
            id: {
              type: "integer",
            },
            display_name: {
              type: "char",
            },
            color: {
              type: "integer",
            },
          },
          fields: {
            id: {
              type: "integer",
            },
            display_name: {
              type: "char",
            },
            color: {
              type: "integer",
            },
          },
        },
        group_ids: {
          relation: "res.groups",
          type: "many2many",
          relatedFields: {
            id: {
              type: "integer",
            },
            display_name: {
              type: "char",
            },
            color: {
              type: "integer",
            },
          },
          fields: {
            id: {
              type: "integer",
            },
            display_name: {
              type: "char",
            },
            color: {
              type: "integer",
            },
          },
        },
        authorized_ids: {
          relation: "res.users",
          type: "many2many",
          relatedFields: {
            id: {
              type: "integer",
            },
            display_name: {
              type: "char",
            },
            color: {
              type: "integer",
            },
          },
          fields: {
            id: {
              type: "integer",
            },
            display_name: {
              type: "char",
            },
            color: {
              type: "integer",
            },
          },
        },
      },
      fieldsInfo: {
        default: {
          id: {
            type: "integer",
          },
          name: {
            type: "char",
          },
          tag_ids: {
            relatedFields: {
              id: {
                type: "integer",
              },
              display_name: {
                type: "char",
              },
              color: {
                type: "integer",
              },
            },
            fieldsInfo: {
              default: {
                id: {
                  type: "integer",
                },
                display_name: {
                  type: "char",
                },
                color: {
                  type: "integer",
                },
              },
            },
            viewType: "default",
          },
          group_ids: {
            relatedFields: {
              id: {
                type: "integer",
              },
              display_name: {
                type: "char",
              },
              color: {
                type: "integer",
              },
            },
            fieldsInfo: {
              default: {
                id: {
                  type: "integer",
                },
                display_name: {
                  type: "char",
                },
                color: {
                  type: "integer",
                },
              },
            },
            viewType: "default",
          },
          authorized_ids: {
            relatedFields: {
              id: {
                type: "integer",
              },
              display_name: {
                type: "char",
              },
              color: {
                type: "integer",
              },
            },
            fieldsInfo: {
              default: {
                id: {
                  type: "integer",
                },
                display_name: {
                  type: "char",
                },
                color: {
                  type: "integer",
                },
              },
            },
            viewType: "default",
          },
        },
      },
    };

    return this.model.load(params).then(function (recordId) {
      self.handleRecordId = recordId;
      self.record = self.model.get(self.handleRecordId);

      const editMode = self.has_sign_requests ? "readonly" : "edit";
      const isReadonly = self.has_sign_requests ? false  : true;

      self.tag_idsMany2Many = new FormFieldMany2ManyTags(
        self,
        "tag_ids",
        self.record,
        {
          mode: editMode,
          create: true,
          attrs: { options: { color_field: "color", readonly: isReadonly } },
        }
      );
      self._registerWidget(
        self.handleRecordId,
        "tag_ids",
        self.tag_idsMany2Many
      );
      self.tag_idsMany2Many.appendTo(self.$(".o_sign_template_tags"));
      if (self.manage_template_access) {
        self.authorized_idsMany2many = new FormFieldMany2ManyTags(self, 'authorized_ids', self.record, {
          mode: editMode,
          create: false,
          attrs: {
            options: {
              color_field: 'color',
              readonly: isReadonly
            }
          },
        });
        self._registerWidget(self.handleRecordId, 'authorized_ids', self.authorized_idsMany2many);
        self.authorized_idsMany2many.appendTo(self.$('.o_sign_template_authorized_ids'));

        self.group_idsMany2many = new FormFieldMany2ManyTags(
          self,
          "group_ids",
          self.record,
          {
            mode: editMode,
            create: false,
            attrs: { options: { color_field: "color", readonly: isReadonly } },
          }
        );
        self._registerWidget(
          self.handleRecordId,
          "group_ids",
          self.group_idsMany2many
        );
        self.group_idsMany2many.appendTo(self.$(".o_sign_template_group_id"));
      }
    });
  },

  _onFieldChanged: function (event) {
    const $majInfo = this.$(event.target.$el)
      .parent()
      .next(".o_sign_template_saved_info");
    StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);
    this.model
      .save(this.handleRecordId, { reload: true })
      .then((fieldNames) => {
        this.record = this.model.get(this.handleRecordId);
        this.tag_idsMany2Many.reset(this.record);
        $majInfo.stop().css("opacity", 1).animate({ opacity: 0 }, 1500);
      });
  },

  perform_rpc: function () {
    const self = this;
    const defTemplates = this._rpc({
      model: "sign.template",
      method: "read",
      args: [[this.templateID], ['id', 'attachment_id', 'has_sign_requests', 'responsible_count', 'display_name']],
    }).then(function prepare_template(template) {
      if (template.length === 0) {
        self.templateID = undefined;
        self.displayNotification({
          title: _t("Warning"),
          message: _t("The template doesn't exist anymore."),
        });
        return Promise.resolve();
      }
      template = template[0];
      self.sign_template = template;
      self.has_sign_requests = template.has_sign_requests;

      const defSignItems = self
        ._rpc({
          model: "sign.item",
          method: "search_read",
          args: [[["template_id", "=", template.id]]],
          kwargs: { context: session.user_context },
        })
        .then(function (sign_items) {
          self.sign_items = sign_items;
          return self._rpc({
            model: "sign.item.option",
            method: "search_read",
            args: [[], ["id", "value"]],
            kwargs: { context: session.user_context },
          });
        });
      const defIrAttachments = self
        ._rpc({
          model: "ir.attachment",
          method: "read",
          args: [[template.attachment_id[0]], ["mimetype", "name"]],
          kwargs: { context: session.user_context },
        })
        .then(function (attachment) {
          attachment = attachment[0];
          self.sign_template.attachment_id = attachment;
          self.isPDF = attachment.mimetype.indexOf("pdf") > -1;
        });

      return Promise.all([defSignItems, defIrAttachments]);
    });

    const defSelectOptions = this._rpc({
      model: "sign.item.option",
      method: "search_read",
      args: [[]],
      kwargs: { context: session.user_context },
    }).then(function (options) {
      self.sign_item_options = options;
    });

    const defParties = this._rpc({
      model: "sign.item.role",
      method: "search_read",
      kwargs: { context: session.user_context },
    }).then(function (parties) {
      self.sign_item_parties = parties;
    });

    const defItemTypes = this._rpc({
      model: "sign.item.type",
      method: "search_read",
      kwargs: { context: session.user_context },
    }).then(function (types) {
      self.sign_item_types = types;
    });

    return Promise.all([
      defTemplates,
      defParties,
      defItemTypes,
      defSelectOptions,
    ]);
  },

  start: function () {
    if (this.templateID === undefined) {
      return this.go_back_to_kanban();
    }
    this.renderButtons();
    this.controlPanelProps.cp_content = { $buttons: this.$buttons };
    return this._super()
      .then(() => {
        this.initialize_content();
        if (this.$("iframe").length) {
          core.bus.on("DOM_updated", this, init_iframe);
        }
        this.$(".o_content").addClass("o_sign_template");
      });
    function init_iframe() {
      if (
        this.$el.parents("html").length &&
        !this.$el.parents("html").find(".modal-dialog").length
      ) {
        framework.blockUI({
          overlayCSS: { opacity: 0 },
          blockMsgClass: "o_hidden",
        });
        this.iframeWidget = new EditablePDFIframe(
          this,
          "/web/content/" + this.sign_template.attachment_id.id,
          true,
          {
            parties: this.sign_item_parties,
            types: this.sign_item_types,
            signatureItems: this.sign_items,
            select_options: this.sign_item_options,
          }
        );
        return this.iframeWidget.attachTo(this.$("iframe")).then(() => {
          framework.unblockUI();
          this.iframeWidget.currentRole = this.sign_item_parties[0].id;
        });
      }
    }
  },

  initialize_content: function () {
    this.createTemplateTagsField();
    this.$(".o_content").empty();
    this.debug = config.isDebug();
    this.$(".o_content").append(
      core.qweb.render("sign.template", { widget: this })
    );

    this.$("iframe,.o_sign_template_name_input").prop(
      "disabled",
      this.has_sign_requests
    );

    this.$templateNameInput = this.$(".o_sign_template_name_input").first();
    this.$templateNameInput.trigger("input");
    this.initialTemplateName = this.$templateNameInput.val();
  },

  do_show: function () {
    this._super();

    // the iframe cannot be detached normally
    // we have to reload it entirely and re-apply the sign items on it
    return this.perform_rpc().then(() => {
      if (this.iframeWidget) {
        this.iframeWidget.destroy();
        this.iframeWidget = undefined;
      }
      this.$("iframe").remove();
      this.initialize_content();
    });
  },

  prepareTemplateData: function () {
    this.rolesToChoose = {};
    let updatedSignItems = {},
      Id2UpdatedItem = {};
    const configuration = this.iframeWidget
      ? this.iframeWidget.configuration
      : {};
    for (let page in configuration) {
      configuration[page].forEach((signItem) => {
        if (signItem.data('updated') !== true) {
          return;
        }
        const id = signItem.data('item-id');
        Id2UpdatedItem[id] = signItem;
        const resp = signItem.data("responsible");
        updatedSignItems[id] = {
          type_id: signItem.data("type"),
          required: signItem.data("required"),
          name: signItem.data("name"),
          alignment: signItem.data("alignment"),
          option_ids: signItem.data("option_ids"),
          responsible_id: resp,
          page: page,
          posX: signItem.data("posx"),
          posY: signItem.data("posy"),
          width: signItem.data("width"),
          height: signItem.data("height"),
        };
        if (id < 0) {
          updatedSignItems[id]["transaction_id"] = id;
        }
        this.rolesToChoose[resp] = this.iframeWidget.parties[resp];
      });
    }
    return [updatedSignItems, Id2UpdatedItem];
  },

  saveTemplate: function () {
    const [updatedSignItems, Id2UpdatedItem] = this.prepareTemplateData();
    const $majInfo = this.$(".o_sign_template_saved_info").first();
    const newTemplateName = this.$templateNameInput.val();
    this._rpc({
      model: "sign.template",
      method: "update_from_pdfviewer",
      args: [
        this.templateID,
        updatedSignItems,
        this.iframeWidget.deletedSignItemIds,
        newTemplateName == this.initialTemplateName ? "" : newTemplateName,
      ],
    }).then((result) => {
      if (!result) {
        Dialog.alert(
          this,
          _t("Somebody is already filling a document which uses this template"),
          {
            confirm_callback: () => {
              this.go_back_to_kanban();
            },
          }
        );
      }
      const newId2ItemIdMap = result;
      for (let [newId, itemId] of Object.entries(newId2ItemIdMap)) {
          Id2UpdatedItem[newId].data({'itemId': itemId});
      }
      Object.entries(Id2UpdatedItem).forEach(([id,item]) => {
          item.data({'updated': false});
      })
      this.iframeWidget.deletedSignItemIds = [];
      this.initialTemplateName = newTemplateName;
      $majInfo.stop().css("opacity", 1).animate({ opacity: 0 }, 1500);
    });
  },

  duplicateTemplate: function () {
    this._rpc({
      model: 'sign.template',
      method: 'copy',
      args: [[this.templateID]],
    })
    .then((templateID) => {
      this.do_action({
        type: "ir.actions.client",
        tag: 'sign.Template',
        name: _t("Duplicated Template"),
        context: {
            id: templateID,
        },
      });
    });
  },
});

core.action_registry.add("sign.Template", TemplateAction);
