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
    for (var i=0;i < data.length;i++)
	{
	    reqdata += 'content-disposition: form-data; name="' + data[i].Name + '"';
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

function doClickSave() {
    try {
	var data = eamy.instances[0].getText();
    } catch(e) {
	var data = area.textarea.value;
    }
    var dataForPost = prepareMultiPartPOST(new Array(
	prepareDataForSave('data', data),
	prepareDataForSave('file_hash', jQuery("input[name='file_hash']").val()),
	prepareDataForSave('saved_on', jQuery("input[name='saved_on']").val()),
	prepareDataForSave('saved_on', jQuery("input[name='saved_on']").val()),
	prepareDataForSave('from_ajax','true')));
    // console.info(area.textarea.value);
        jQuery("input[name='saved_on']").attr('style','background-color:yellow');
	jQuery("input[name='saved_on']").val('saving now...')
	jQuery.ajax({
	  type: "POST",
	  contentType: 'multipart/form-data;boundary="' + dataForPost[1] + '"',
	  url: self.location.href,
	  dataType: "json",
	  data: dataForPost[0],
	  timeout: 5000,
      beforeSend: function(xhr) {
            xhr.setRequestHeader('web2py-component-location',document.location);
            xhr.setRequestHeader('web2py-component-element','doClickSave');},
	  success: function(json,text,xhr){

	        // show flash message (if any)
	        var flash=xhr.getResponseHeader('web2py-component-flash');
            if (flash) jQuery('.flash').html(flash).slideDown();
            else jQuery('.flash').hide();

            // reenable disabled submit button
		    var t=jQuery("input[name='save']");
		    t.attr('class','');
            t.attr('disabled','');

		    try {
			if (json.error) {
			    window.location.href=json.redirect;
			} else {
			    // console.info( json.file_hash );
			    jQuery("input[name='file_hash']").val(json.file_hash);
			    jQuery("input[name='saved_on']").val(json.saved_on);
			    if (json.highlight) {
			        editAreaLoader.setSelectionRange('body', json.highlight.start, json.highlight.end);
			    } else {
			        jQuery("input[name='saved_on']").attr('style','background-color:#99FF99');
			        jQuery(".flash").delay(1000).fadeOut('slow');
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
                    } catch(e) {
			on_error();
		    }
		},
	  error: function(json) { on_error(); }
	});
	return false;
}

function doToggleBreakpoint(filename, url) {
    try {
	var data = eamy.instances[0].getText();
    } catch(e) {
	var data = area.textarea.value;
	var sel = editAreaLoader.getSelectionRange('body');
    }
    var dataForPost = prepareMultiPartPOST(new Array(
	prepareDataForSave('filename', filename),
	prepareDataForSave('sel_start', sel["start"]),
	prepareDataForSave('sel_end', sel["end"]),
	prepareDataForSave('data', data)));
	jQuery.ajax({
	  type: "POST",
	  contentType: 'multipart/form-data;boundary="' + dataForPost[1] + '"',
	  url: url,
	  dataType: "json",
	  data: dataForPost[0],
	  timeout: 5000,
      beforeSend: function(xhr) {
            xhr.setRequestHeader('web2py-component-location',document.location);
            xhr.setRequestHeader('web2py-component-element','doSetBreakpoint');},
	  success: function(json,text,xhr){

	        // show flash message (if any)
	        var flash=xhr.getResponseHeader('web2py-component-flash');
            if (flash) jQuery('.flash').html(flash).slideDown();
            else jQuery('.flash').hide();
		    try {
			if (json.error) {
			    window.location.href=json.redirect;
			} else {
			    // mark the breakpoint if ok=True, remove mark if ok=False
			    // do nothing if ok = null  
			    // alert(json.ok + json.lineno);
			}
                    } catch(e) {
			on_error();
		    }

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

