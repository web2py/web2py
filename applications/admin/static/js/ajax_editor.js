function prepareDataForSave(name,data) {
    var obj = new Object();
    obj.Name = name;
    obj.Data = data;
    return obj;
}

function prepareMultiPartPOST(data) {
    // var boundary = 'sPlItME' + Math.floor(Math.random()*10000);
    var boundary = '' + Math.floor(Math.random()*10000);
    var reqdata = '--' + boundary + '\r\n';
    //console.log(data.length);
    for (var i=0;i < data.length;i++) {
	reqdata += 'content-disposition: form-data; name="';
	reqdata += data[i].Name + '"';
	reqdata += "\r\n\r\n" ;
	reqdata +=  data[i].Data;
	reqdata += "\r\n" ;
	reqdata += '--' + boundary + '\r\n';
    }
    return new Array(reqdata,boundary);
}

function on_error() {
    jQuery("input[name='saved_on']").attr('style','background-color:red');
    jQuery("input[name='saved_on']").val('communication error');
}

function getData() {
    if (window.ace_editor) {
        var data = window.ace_editor.getSession().getValue();
    } else if (window.mirror) {
	var data = window.mirror.getValue();
    } else if (window.eamy) {
	var data = window.eamy.instances[0].getText();
    } else if (window.textarea) {
	var data = textarea.value;
    }
    return data;
}

function doHighlight(highlight) {
    if (window.ace_editor) {
	window.ace_editor.gotoLine(highlight.lineno);
    } else if (window.mirror) {
        // Put the cursor at the offending line:
        window.mirror.setCursor({line:highlight.lineno-1,
                                 ch:highlight.offset+1});
    } else if (window.eamy) {
	// not implemented
    } else if (window.textarea) {
	editAreaLoader.setSelectionRange('body', highlight.start, highlight.end);
    }
}

function doClickSave() {
	var currentTabID = '#' + jQuery('#edit_placeholder div.tab-pane.active').attr('id');
	var editor = jQuery (currentTabID + ' textarea').data('editor');
   var data = editor.getValue();
    var dataForPost = prepareMultiPartPOST(new Array(
	prepareDataForSave('data', data),
	prepareDataForSave('file_hash',
			   jQuery(currentTabID + " input[name='file_hash']").val()),
	prepareDataForSave('saved_on',
			   jQuery(currentTabID + " input[name='saved_on']").val()),
	prepareDataForSave('saved_on',
			   jQuery(currentTabID + " input[name='saved_on']").val()),
	prepareDataForSave('from_ajax','true')));
        // console.info(area.textarea.value);
        jQuery(currentTabID + " input[name='saved_on']").attr('style',
					      'background-color:yellow');
	jQuery(currentTabID + " input[name='saved_on']").val('saving now...')
	currentUrl =  jQuery(currentTabID + ' form').attr('action');
	jQuery.ajax({
	  type: "POST",
	  contentType: 'multipart/form-data;boundary="'
		    + dataForPost[1] + '"',
	  url: currentUrl,
	  dataType: "json",
	  data: dataForPost[0],
	  timeout: 5000,
          beforeSend: function(xhr) {
		    xhr.setRequestHeader('web2py-component-location',
					 document.location);
		    xhr.setRequestHeader('web2py-component-element',
					 'doClickSave');
		},
          success: function(json,text,xhr){

	    // show flash message (if any)
	    var flash=xhr.getResponseHeader('web2py-component-flash');
            if (flash) {
		var flashhtml = decodeURIComponent(flash);
		jQuery('.flash').html(flashhtml).slideDown();
	    } else jQuery('.flash').hide();

            // reenable disabled submit button
		    var t=jQuery("input[name='save']");
		    t.attr('class','');
            t.attr('disabled','');
	    try {
		if (json.error) {
		    window.location.href=json.redirect;
		} else {
		    // console.info( json.file_hash );
		    jQuery(currentTabID + " input[name='file_hash']").val(json.file_hash);
		    jQuery(currentTabID + " input[name='saved_on']").val(json.saved_on);
		    if (json.highlight) {
			doHighlight(json.highlight);
		    } else {
			jQuery(currentTabID + " input[name='saved_on']").attr('style','background-color:#99FF99');
			//jQuery(".flash").delay(1000).fadeOut('slow');
		    }
		    // console.info(jQuery("input[name='file_hash']").val());
		    var output = '<b>exposes:</b> ';
		    for ( var i in json.functions) {
			output += ' <a href="/' + json.application + '/' + json.controller + '/' + json.functions[i] + '">' + json.functions[i] + '</a>,';
		    }
		    if(output!='<b>exposes:</b> ') {
			jQuery("#exposed").html( output.substring(0, output.length-1));
		    }
		}
	    } catch(e) { on_error();}
		},
		    error: function(json) { on_error(); }
	    });
	return false;
}

function getSelectionRange() {
    var sel;
    if (window.ace_editor) {
	sel = {};
        range = window.ace_editor.getSelectionRange();
        // passing the line number directly, no need to read the text
        sel['start'] = range.start.row;
        sel['end'] = range.end.row;
        sel['data'] = '';
    } else if (window.mirror) {
		var currentTabID = '#' + jQuery('#edit_placeholder div.tab-pane.active').attr('id');
		var editor = jQuery (currentTabID + ' textarea').data('editor');
		sel = {};
		sel['start'] = editor.getCursor(true).line;
		sel['end'] = editor.getCursor(false).line;
		sel['data'] = '';
    } else if (window.eamy) {
	sel = {};
	// not implemented
    } else if (window.textarea) {
        // passing offset, needs the text to calculate the line:
        sel = editAreaLoader.getSelectionRange('body');
        sel['data'] = getData();
    }
    return sel;
}

function doToggleBreakpoint(filename, url, sel) {
	var currentTabID = '#' + jQuery('#edit_placeholder div.tab-pane.active').attr('id');
	var editor = jQuery (currentTabID + ' textarea').data('editor');

    if (sel==null) {
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
	  contentType: 'multipart/form-data;boundary="'+dataForPost[1]+'"',
	  url: url,
	  dataType: "json",
	  data: dataForPost[0],
	  timeout: 5000,
      beforeSend: function(xhr) {
	  xhr.setRequestHeader('web2py-component-location',
			       document.location);
	  xhr.setRequestHeader('web2py-component-element',
			       'doSetBreakpoint');},
	  success: function(json,text,xhr){
	     // show flash message (if any)
	     var flash=xhr.getResponseHeader('web2py-component-flash');
	     if (flash) {
				jQuery('.flash').html(decodeURIComponent(flash))
				.append('<a href="#" class="close">&times;</a>')
				.slideDown();
		}
	     else jQuery('.flash').hide();
	     try {
		 if (json.error) {
		     window.location.href=json.redirect;
		 } else {
             if (json.ok==true && window.mirror) {
    		     // mark the breakpoint if ok=True
 		         editor.setMarker(json.lineno-1,
 		                         "<span style='color: red'>●</span> %N%")
 		     } else if (json.ok==false && window.mirror) {
    		     // remove mark if ok=False
 		         editor.setMarker(json.lineno-1, "%N%")
 		     } else {
    		     // do nothing if ok = null
    		 }
		     // alert(json.ok + json.lineno);
		 }
	     } catch(e) { on_error(); }
		},
		    error: function(json) { on_error(); }
	    });
	return false;
}

// on load, update all breakpoints markers:
function doListBreakpoints(filename, url) {
    var dataForPost = prepareMultiPartPOST(new Array(
	    prepareDataForSave('filename', filename)
        ));
     jQuery.ajax({
	  type: "POST",
	  contentType: 'multipart/form-data;boundary="'+dataForPost[1]+'"',
	  url: url,
	  dataType: "json",
	  data: dataForPost[0],
	  timeout: 5000,
      beforeSend: function(xhr) {
	  xhr.setRequestHeader('web2py-component-location',
			       document.location);
	  xhr.setRequestHeader('web2py-component-element',
			       'doListBreakpoints');},
	  success: function(json,text,xhr){
		try {
			if (json.error) {
				window.location.href=json.redirect;
			} else {
				var currentTabID = '#' + jQuery('#edit_placeholder div.tab-pane.active').attr('id');
				var editor = jQuery (currentTabID + ' textarea').data('editor');
				if (window.mirror) {
                     for (i in json.breakpoints) {
                         lineno = json.breakpoints[i];
            		     // mark the breakpoint if ok=True
         		         editor.setMarker(lineno-1, "<span style='color: red'>●</span> %N%");
         		     }
        		 }
		     }
	     } catch(e) { on_error(); }
      },
      error: function(json) { on_error(); }
	});
	return false;
}

function keepalive(url) {
	jQuery.ajax({
	  type: "GET",
	  url: url,
	  timeout: 1000,
	  success: function(){},
	  error: function(x) { on_error(); } });
}

function load_file (url) {
	jQuery.ajax({
		type: "GET",
		dataType: 'json',
		url: url,
		timeout: 1000,
		success: function(json){
			if (typeof(json['plain_html']) !== undefined) {
				if (jQuery('#' + json['id']).length === 0 || json['force'] === true) {			
					// Create a tab and put the code in it
					var tab_header = '<li><a href="#idDefault" data-toggle="tab">filenameDefault<button type="button" class="close">&times;</button></a></li>'.replace(/idDefault/, json['id']).replace(/filenameDefault/, json['filename'] );
					var tab_body = '<div id="idDefault" class="tab-pane fade in " >htmlDefault</div>'.replace(/htmlDefault/, json['plain_html']).replace(/idDefault/, json['id']);
					if (json['force'] === false) {
						jQuery('#filesTab').append(jQuery(tab_header));
						jQuery('#myTabContent').append(jQuery(tab_body));
					} else {
						jQuery('#' + json['id']).html(jQuery(tab_body));										
					}
				}
				jQuery("a[href='#" + json['id'] + "']" ).click();
			}
		},
		error: function(x) { on_error(); }
	});
}
