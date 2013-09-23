function prepareDataForSave(name, data) {
  var obj = new Object();
  obj.Name = name;
  obj.Data = data;
  return obj;
}

function prepareMultiPartPOST(data) {
  // var boundary = 'sPlItME' + Math.floor(Math.random()*10000);
  var boundary = '' + Math.floor(Math.random() * 10000);
  var reqdata = '--' + boundary + '\r\n';
  //console.log(data.length);
  for(var i = 0; i < data.length; i++) {
    reqdata += 'content-disposition: form-data; name="';
    reqdata += data[i].Name + '"';
    reqdata += "\r\n\r\n";
    reqdata += data[i].Data;
    reqdata += "\r\n";
    reqdata += '--' + boundary + '\r\n';
  }
  return new Array(reqdata, boundary);
}

function on_error() {
  jQuery("input[name='saved_on']").attr('style', 'background-color:red');
  jQuery("input[name='saved_on']").val('communication error');
}

function doHighlight(highlight) {
  // Put the cursor at the offending line:
  editor.setCursor({
    line: highlight.lineno - 1,
    ch: highlight.offset + 1
  });
}


function doClickSave() {
  var currentTabID = '#' + jQuery('#edit_placeholder div.tab-pane.active').attr('id');
  var editor = jQuery(currentTabID + ' textarea').data('editor');
  var data = editor.getValue();
  var dataForPost = prepareMultiPartPOST(new Array(
    prepareDataForSave('data', data),
    prepareDataForSave('file_hash',
      jQuery(currentTabID + " input[name='file_hash']").val()),
    prepareDataForSave('saved_on',
      jQuery(currentTabID + " input[name='saved_on']").val()),
    prepareDataForSave('saved_on',
      jQuery(currentTabID + " input[name='saved_on']").val()),
    prepareDataForSave('from_ajax', 'true')));
  // console.info(area.textarea.value);
  jQuery(currentTabID + " input[name='saved_on']").attr('style',
    'background-color:yellow');
  jQuery(currentTabID + " input[name='saved_on']").val('saving now...')
  currentUrl = jQuery(currentTabID + ' form').attr('action');
  jQuery.ajax({
    type: "POST",
    contentType: 'multipart/form-data;boundary="' + dataForPost[1] + '"',
    url: currentUrl,
    dataType: "json",
    data: dataForPost[0],
    timeout: 5000,
    beforeSend: function (xhr) {
      xhr.setRequestHeader('web2py-component-location',
        document.location);
      xhr.setRequestHeader('web2py-component-element',
        'doClickSave');
    },
    success: function (json, text, xhr) {
      jQuery(editor).data('saved', true); // Set as saved
      editor.on("change", store_changes_function); // Re-enable change watcher
      // reenable disabled submit button
      var t = jQuery("input[name='save']");
      t.attr('class', '');
      t.attr('disabled', '');
	  var flash = xhr.getResponseHeader('web2py-component-flash');
      if(flash) {
        jQuery('.flash').html(decodeURIComponent(flash))
          .append('<a href="#" class="close">&times;</a>')
          .slideDown();
      } else jQuery('.flash').hide();
      try {
        if(json.error) {
          window.location.href = json.redirect;
        } else {
          // console.info( json.file_hash );
          jQuery(currentTabID + " input[name='file_hash']").val(json.file_hash);
          jQuery(currentTabID + " input[name='saved_on']").val(json.saved_on);
          if(json.highlight) {
            doHighlight(json.highlight);
          } else {
            jQuery(currentTabID + " input[name='saved_on']").attr('style', 'background-color:#99FF99');
            //jQuery(".flash").delay(1000).fadeOut('slow');
          }
          // console.info(jQuery("input[name='file_hash']").val());
          var output = '<b>exposes:</b> ';
          for(var i in json.functions) {
            output += ' <a target="_blank" href="/' + json.application + '/' + json.controller + '/' + json.functions[i] + '">' + json.functions[i] + '</a>,';
          }
          if(output != '<b>exposes:</b> ') {
            jQuery(currentTabID + " .exposed").html(output.substring(0, output.length - 1));
          }
        }
      } catch(e) {
        on_error();
      }
    },
    error: function (json) {
      on_error();
    }
  });
  return false;
}

function getActiveEditor() {
  var currentTabID = '#' + jQuery('#edit_placeholder div.tab-pane.active').attr('id');
  var editor = jQuery(currentTabID + ' textarea').data('editor');
  return editor;
}

function getSelectionRange() {
  var editor = getActiveEditor();
  var sel = {};
  sel['start'] = editor.getCursor(true).line;
  sel['end'] = editor.getCursor(false).line;
  sel['data'] = '';
  return sel;
}

function doToggleBreakpoint(filename, url, sel) {
  var editor = getActiveEditor();
  if(sel == null) {
    // use cursor position to determine the breakpoint line
    // (gutter already tell us the selected line)
    sel = getSelectionRange();
  }
  var dataForPost = prepareMultiPartPOST(new Array(
    prepareDataForSave('filename', filename),
    prepareDataForSave('sel_start', sel["start"]),
    prepareDataForSave('sel_end', sel["end"]),
    prepareDataForSave('data', sel['data'])));
  jQuery.ajax({
    type: "POST",
    contentType: 'multipart/form-data;boundary="' + dataForPost[1] + '"',
    url: url,
    dataType: "json",
    data: dataForPost[0],
    timeout: 5000,
    beforeSend: function (xhr) {
      xhr.setRequestHeader('web2py-component-location',
        document.location);
      xhr.setRequestHeader('web2py-component-element',
        'doSetBreakpoint');
    },
    success: function (json, text, xhr) {
      // show flash message (if any)
      var flash = xhr.getResponseHeader('web2py-component-flash');
      if(flash) {
        jQuery('.flash').html(decodeURIComponent(flash))
          .append('<a href="#" class="close">&times;</a>')
          .slideDown();
      } else jQuery('.flash').hide();
      try {
        if(json.error) {
          window.location.href = json.redirect;
        } else {
          if(json.ok == true) {
            // mark the breakpoint if ok=True
            editor.setGutterMarker(json.lineno - 1, "breakpoints", makeMarker());
          } else if(json.ok == false) {
            // remove mark if ok=False
            editor.setGutterMarker(json.lineno - 1, "breakpoints", null);
          }
        }
      } catch(e) {
        on_error();
      }
    },
    error: function (json) {
      on_error();
    }
  });
  return false;
}

// on load, update all breakpoints markers:

function doListBreakpoints(filename, url, editor) {
  var dataForPost = prepareMultiPartPOST(new Array(
    prepareDataForSave('filename', filename)
  ));
  jQuery.ajax({
    type: "POST",
    contentType: 'multipart/form-data;boundary="' + dataForPost[1] + '"',
    url: url,
    dataType: "json",
    data: dataForPost[0],
    timeout: 5000,
    beforeSend: function (xhr) {
      xhr.setRequestHeader('web2py-component-location',
        document.location);
      xhr.setRequestHeader('web2py-component-element',
        'doListBreakpoints');
    },
    success: function (json, text, xhr) {
      try {
        if(json.error) {
          window.location.href = json.redirect;
        } else {
          var editor = getActiveEditor();
          for(i in json.breakpoints) {
            lineno = json.breakpoints[i];
            // mark the breakpoint if ok=True
            editor.setGutterMarker(lineno - 1, "breakpoints", makeMarker());
          }
        }
      } catch(e) {
        on_error();
      }
    },
    error: function (json) {
      on_error();
    }
  });
  return false;
}

function makeMarker() {
  var marker = document.createElement("div");
  marker.style.color = "#822";
  marker.innerHTML = "●";
  marker.className = "breakpoint";
  return marker;
}


function keepalive(url) {
  jQuery.ajax({
    type: "GET",
    url: url,
    timeout: 1000,
    success: function () {},
    error: function (x) {
      on_error();
    }
  });
}

function load_file(url) {
  jQuery.ajax({
    type: "GET",
    dataType: 'json',
    url: url,
    timeout: 1000,
    success: function (json) {
      if(typeof (json['plain_html']) !== undefined) {
        if(jQuery('#' + json['id']).length === 0 || json['force'] === true) {
          // Create a tab and put the code in it
          var tab_header = '<li><a href="#' + json['id'] + '" data-toggle="tab">' + json['filename'] + '<button type="button" class="close">&times;</button></a></li>';
          var tab_body = '<div id="' + json['id'] + '" class="tab-pane fade in " >' + json['plain_html'] + '</div>';
          if(json['force'] === false) {
            jQuery('#filesTab').append(jQuery(tab_header));
            jQuery('#myTabContent').append(jQuery(tab_body));
          } else {
            jQuery('#' + json['id']).html(jQuery(tab_body));
          }
        }
        jQuery("a[href='#" + json['id'] + "']").click();
      }
    },
    error: function (x) {
      on_error();
    }
  });
}

function set_font(editor, incr) {
  var fontSize = '';
  if(incr !== 0) {
    fontSize = parseInt(jQuery(editor.getWrapperElement()).css('font-size'));
    fontSize = fontSize + incr + "px";
  }
  jQuery(editor.getWrapperElement()).css('font-size', fontSize);
  editor.refresh();
}

var template_js = '<p class="repo-name">{{{a_tag}}}</p><small>{{address}}</small>';
