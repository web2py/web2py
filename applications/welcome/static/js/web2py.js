function popup(url) {
  newwindow=window.open(url,'name','height=400,width=600');
  if (window.focus) newwindow.focus();
  return false;
}
function collapse(id) { jQuery('#'+id).slideToggle(); }
function fade(id,value) { if(value>0) jQuery('#'+id).hide().fadeIn('slow'); else jQuery('#'+id).show().fadeOut('slow'); }
function ajax(u,s,t) {
    query = '';
    if (typeof s == "string") {
        d = jQuery(s).serialize();
        if(d){ query = d; }
    } else {
        pcs = [];
        if (s != null && s != undefined) for(i=0; i<s.length; i++) {
            q = jQuery("[name="+s[i]+"]").serialize();
            if(q){pcs.push(q);}
        }
        if (pcs.length>0){query = pcs.join("&");}
    }
    jQuery.ajax({type: "POST", url: u, data: query, success: function(msg) { if(t) { if(t==':eval') eval(msg); else if(typeof t=='string') jQuery("#"+t).html(msg); else t(msg); } } });
}

String.prototype.reverse = function () { return this.split('').reverse().join('');};
function web2py_ajax_fields(target) {
  var date_format = (typeof w2p_ajax_date_format != 'undefined') ? w2p_ajax_date_format : "%Y-%m-%d";
  var datetime_format = (typeof w2p_ajax_datetime_format != 'undefined') ? w2p_ajax_datetime_format : "%Y-%m-%d %H:%M:%S";
  jQuery("input.date",target).each(function() {Calendar.setup({inputField:this, ifFormat:date_format, showsTime:false });});
  jQuery("input.datetime",target).each(function() {Calendar.setup({inputField:this, ifFormat:datetime_format, showsTime: true, timeFormat: "24" });});
  jQuery("input.time",target).each(function(){jQuery(this).timeEntry();});

};

function web2py_ajax_init(target) {
  jQuery('.hidden', target).hide();
  jQuery('.error', target).hide().slideDown('slow');
  web2py_ajax_fields(target);
};

function web2py_event_handlers() {
  var doc = jQuery(document)
      doc.on('click', '.flash', function(e){var t=jQuery(this); if(t.css('top')=='0px') t.slideUp('slow'); else t.fadeOut(); e.preventDefault();});
  doc.on('keyup', 'input.integer', function(){this.value=this.value.reverse().replace(/[^0-9\-]|\-(?=.)/g,'').reverse();});
  doc.on('keyup', 'input.double, input.decimal', function(){this.value=this.value.reverse().replace(/[^0-9\-\.,]|[\-](?=.)|[\.,](?=[0-9]*[\.,])/g,'').reverse();});
  var confirm_message = (typeof w2p_ajax_confirm_message != 'undefined') ? w2p_ajax_confirm_message : "Are you sure you want to delete this object?";
  doc.on('click', "input[type='checkbox'].delete", function(){if(this.checked) if(!confirm(confirm_message)) this.checked=false;});
  doc.ajaxSuccess(function(e, xhr) {
    var redirect=xhr.getResponseHeader('web2py-redirect-location');
    if (redirect != null) {
      window.location = redirect;
    };
  });
};

jQuery(function() {
   var flash = jQuery('.flash');
   flash.hide();
   if(flash.html()) flash.append('<span style="float:right;">&times;<span>').slideDown();
   web2py_ajax_init(document);
   web2py_event_handlers();
});

function web2py_trap_form(action,target) {
   jQuery('#'+target+' form').each(function(i){
      var form=jQuery(this);
      if(!form.hasClass('no_trap'))
        form.submit(function(e){
         jQuery('.flash').hide().html('');
         web2py_ajax_page('post',action,form.serialize(),target);
	 e.preventDefault();
      });
   });
}

function web2py_trap_link(target) {
    jQuery('#'+target+' a.w2p_trap').each(function(i){
	    var link=jQuery(this);
	    link.click(function(e) {
		    jQuery('.flash').hide().html('');
		    web2py_ajax_page('get',link.attr('href'),[],target);
		    e.preventDefault();
		});
	});
}

function web2py_ajax_page(method, action, data, target) {
  jQuery.ajax({'type':method, 'url':action, 'data':data,
    'beforeSend':function(xhr) {
      xhr.setRequestHeader('web2py-component-location', document.location);
      xhr.setRequestHeader('web2py-component-element', target);},
    'complete':function(xhr,text){
      var html=xhr.responseText;
      var content=xhr.getResponseHeader('web2py-component-content');
      var command=xhr.getResponseHeader('web2py-component-command');
      var flash=xhr.getResponseHeader('web2py-component-flash');
      var t = jQuery('#'+target);
      if(content=='prepend') t.prepend(html);
      else if(content=='append') t.append(html);
      else if(content!='hide') t.html(html);
      web2py_trap_form(action,target);
      web2py_trap_link(target);
      web2py_ajax_init('#'+target);
      if(command)
	  eval(decodeURIComponent(command));
      if(flash)
	  jQuery('.flash').html(decodeURIComponent(flash)).slideDown();
    }
  });
}

function web2py_component(action, target, timeout, times){
  jQuery(function(){
    var element = jQuery("#" + target).get(0);
    var statement = "jQuery('#" + target + "').get(0).reload();";
    element.reload = function (){
        // Continue if times is Infinity or
        // the times limit is not reached
        if (this.reload_check()){
            web2py_ajax_page('get', action, null, target);} }; // reload
    // Method to check timing limit
    element.reload_check = function (){
        if (this.reload_counter == Infinity){return true;}
        else {
            if (!isNaN(this.reload_counter)){
                this.reload_counter -= 1;
                if (this.reload_counter < 0){
                    if (!this.run_once){
                        clearInterval(this.timing);
                        return false;
                    }
                }
                else{return true;}
            } }
            return false;}; // reload check
    if (!isNaN(timeout)){
        element.timeout = timeout;
        element.reload_counter = times;
        if (times > 1){
        // Multiple or infinite reload
        // Run first iteration
        web2py_ajax_page('get', action, null, target);
        element.run_once = false;
        element.timing = setInterval(statement, timeout);
        element.reload_counter -= 1;
        }
        else if (times == 1) {
        // Run once with timeout
        element.run_once = true;
        element.setTimeout = setTimeout;
        element.timing = setTimeout(statement, timeout);
        }
    } else {
        // run once (no timeout specified)
	element.reload_counter = Infinity;
        web2py_ajax_page('get', action, null, target);
    } }); }

function web2py_comet(url,onmessage,onopen,onclose) {
  if ("WebSocket" in window) {
    var ws = new WebSocket(url);
    ws.onopen = onopen?onopen:(function(){});
    ws.onmessage = onmessage;
    ws.onclose = onclose?onclose:(function(){});
    return true; // supported
  } else return false; // not supported
}

