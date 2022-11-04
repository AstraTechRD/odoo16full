/** @odoo-module **/

"use strict";

import ajax from "web.ajax";
import { _t } from "web.core";

function getSelect2Options(placeholder) {
  return {
    placeholder: placeholder,
    allowClear: false,
    width: "100%",

    formatResult: function (data, resultElem, searchObj) {
      if (!data.text) {
        $(data.element[0]).data("create_name", searchObj.term);
        return $("<div/>", { text: _t('Create: "') + searchObj.term + '"' });
      }
      return $("<div/>", { text: data.text });
    },

    formatSelection: function (data) {
      if (!data.text) {
        return $("<div/>", {
          text: $(data.element[0]).data("create_name"),
        }).html();
      }
      return $("<div/>", { text: data.text }).html();
    },

    matcher: function (search, data) {
      if (!data) {
        return search.length > 0;
      }
      return data.toUpperCase().indexOf(search.toUpperCase()) > -1;
    },
  };
}

function getOptionsSelectConfiguration(item_id, select_options, selected) {
  if (getOptionsSelectConfiguration.configuration === undefined) {
    let data = [];
    for (let id in select_options) {
      data.push({ id: parseInt(id), text: select_options[id].value });
    }
    const select2Options = {
      data: data,
      multiple: true,
      placeholder: _t("Select available options"),
      allowClear: true,
      width: "200px",
      createSearchChoice: function (term, data) {
        if (
          $(data).filter(function () {
            return this.text.localeCompare(term) === 0;
          }).length === 0
        ) {
          return { id: -1, text: term };
        }
      },
    };

    const selectChangeHandler = async function (e) {
      const $select = $(e.target),
        option = e.added || e.removed;
      $select.data("item_options", $select.select2("val"));
      const option_id = option.id;
      const value = option.text || option.data("create_name");
      if (option_id >= 0 || !value) {
        return false;
      }
      const optionId = await ajax
        .rpc("/web/dataset/call_kw/sign.item.option/get_or_create", {
          model: "sign.item.option",
          method: "get_or_create",
          args: [value],
          kwargs: {},
        });
      process_option(optionId);

      function process_option(optionId) {
        const option = { id: optionId, value: value };
        select_options[optionId] = option;
        selected = $select.select2("val");
        selected.pop(); // remove temp element (with id=-1)
        selected.push(optionId.toString());
        $select.data("item_options", selected);
        resetOptionsSelectConfiguration();
        setAsOptionsSelect($select, item_id, selected, select_options);
        $select.select2("focus");
      }
    };

    getOptionsSelectConfiguration.configuration = {
      options: select2Options,
      handler: selectChangeHandler,
      item_id: item_id,
    };
  }

  return getOptionsSelectConfiguration.configuration;
}

function getResponsibleSelectConfiguration(parties) {
  if (getResponsibleSelectConfiguration.configuration === undefined) {
    const select2Options = getSelect2Options(_t("Select the responsible"));

    const selectChangeHandler = async function (e) {
      const $select = $(e.target),
        $option = $(e.added.element[0]);

      const resp = parseInt($option.val());
      const name = $option.text() || $option.data("create_name");

      if (resp >= 0 || !name) {
        return false;
      }

      const partyValues = await ajax
        .rpc("/web/dataset/call_kw/sign.item.role/get_or_create", {
          model: "sign.item.role",
          method: "get_or_create",
          args: [name],
          kwargs: {},
        });
      process_party(partyValues);

      function process_party(partyValues) {
        parties[partyValues['id']] = { id: partyValues['id'], name: partyValues['name'], color: partyValues['color'] };
        getResponsibleSelectConfiguration.configuration = undefined;
        setAsResponsibleSelect($select, partyValues['id'], parties);
      }
    };

    const $responsibleSelect = $("<select/>").append($("<option/>"));
    for (let id in parties) {
      $responsibleSelect.append(
        $("<option/>", {
          value: parseInt(id),
          text: parties[id].name,
        })
      );
    }
    $responsibleSelect.append($("<option/>", { value: -1 }));

    getResponsibleSelectConfiguration.configuration = {
      html: $responsibleSelect.html(),
      options: select2Options,
      handler: selectChangeHandler,
    };
  }

  return getResponsibleSelectConfiguration.configuration;
}

function resetResponsibleSelectConfiguration() {
  getResponsibleSelectConfiguration.configuration = undefined;
}

function resetOptionsSelectConfiguration() {
  getOptionsSelectConfiguration.configuration = undefined;
}

function setAsResponsibleSelect($select, selected, parties) {
  const configuration = getResponsibleSelectConfiguration(parties);
  setAsSelect(configuration, $select, selected);
}

function setAsOptionsSelect($select, item_id, selected, select_options) {
  const configuration = getOptionsSelectConfiguration(
    item_id,
    select_options,
    selected
  );
  setAsSelect(configuration, $select, selected);
}

function setAsSelect(configuration, $select, selected) {
  $select.select2("destroy");
  if (configuration.html) {
    $select.empty().append(configuration.html).addClass("form-control");
  }
  $select.select2(configuration.options);
  if (selected !== undefined) {
    $select.select2("val", selected);
  }

  $select.off("change").on("change", configuration.handler);
}

export const sign_utils = {
  setAsResponsibleSelect,
  resetResponsibleSelectConfiguration,
  setAsOptionsSelect,
  resetOptionsSelectConfiguration,
};

export default sign_utils;
