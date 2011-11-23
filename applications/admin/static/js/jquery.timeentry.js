/*
   http://keith-wood.name/timeEntry.html
   Time entry for jQuery v1.4.8.
   Written by Keith Wood (kbwood{at}iinet.com.au) June 2007.
   Minor changes by Massimo Di Pierro Nov 2010 (simplified and changed behavior)
   Dual licensed under the GPL (http://dev.jquery.com/browser/trunk/jquery/GPL-LICENSE.txt) and 
   MIT (http://dev.jquery.com/browser/trunk/jquery/MIT-LICENSE.txt) licenses. 
   Please attribute the author if you use it.

   Turn an input field into an entry point for a time value.
   The time can be entered via directly typing the value,
   via the arrow keys.
   It is configurable to show 12 or 24-hour time, to show or hide seconds,
   to enforce a minimum and/or maximum time, to change the spinner image.

   Example:  jQuery('input.time').timeEntry();
*/

(function(jQuery) { // Hide scope, no jQuery conflict

    var PROP_NAME = 'timeEntry';
    
    /* TimeEntry manager.
       Use the singleton instance of this class, jQuery.timeEntry, to interact with the time entry
       functionality. Settings for (groups of) fields are maintained in an instance object
       (TimeEntryInstance), allowing multiple different settings on the same page. 
    */
    
    function TimeEntry() {
	this._disabledInputs = []; // List of time entry inputs that have been disabled
	this._defaults = {
	    showSeconds: true, // True to show seconds as well, false for hours/minutes only
	    defaultTime: null, // The time to use if none has been set, leave at null for now
	    minTime: null, // The earliest selectable time, or null for no limit
	    maxTime: null, // The latest selectable time, or null for no limit
	    show24Hours: true, // True to use 24 hour time, false for 12 hour (AM/PM)
	    ampmNames: ['am', 'pm'] // Names of morning/evening markers
	};
	jQuery.extend(this._defaults);
    }
    
    jQuery.extend(TimeEntry.prototype, {
	    /* 
	       Class name added to elements to indicate already configured with time entry. 
	     */
	    markerClassName: 'hasTimeEntry',
		
	    /* Override the default settings for all instances of the time entry.
	       @param  options  (object) the new settings to use as defaults (anonymous object)
	       @return  (DateEntry) this object 
	    */
	    setDefaults: function(options) {
		extendRemove(this._defaults, options || {});
		return this;
	    },
		
	    /* Attach the time entry handler to an input field.
	       @param  target   (element) the field to attach to
	       @param  options  (object) custom settings for this instance 
	    */
	    _connectTimeEntry: function(target, options) {
		var input = jQuery(target);
		if (input.hasClass(this.markerClassName)) {
		    return;
		}
		var inst = {};
		inst.options = jQuery.extend({}, options);
		inst._selectedHour = 0; // The currently selected hour
		inst._selectedMinute = 0; // The currently selected minute
		inst._selectedSecond = 0; // The currently selected second
		inst._field = 0; // The selected subfield
		inst.input = jQuery(target); // The attached input field
		jQuery.data(target, PROP_NAME, inst);
		input.addClass(this.markerClassName).bind('focus.timeEntry', this._doFocus).
		    bind('blur.timeEntry', this._doBlur).bind('click.timeEntry', this._doClick).
		    bind('keydown.timeEntry', this._doKeyDown).bind('keypress.timeEntry', this._doKeyPress);
		// Check pastes
		if (jQuery.browser.mozilla)
		    input.bind('input.timeEntry', function(event) { jQuery.timeEntry._parseTime(inst); });
		if (jQuery.browser.msie)
		    input.bind('paste.timeEntry', function(event) { setTimeout(function() { jQuery.timeEntry._parseTime(inst); }, 1); });
	    },
		
		
	    /* Check whether an input field has been disabled.
	       @param  input  (element) input field to check
	       @return  (boolean) true if this field has been disabled, false if it is enabled 
	    */
	    _isDisabledTimeEntry: function(input) {
		return jQuery.inArray(input, this._disabledInputs) > -1;
	    },
		
	    /* Reconfigure the settings for a time entry field.
	       @param  input    (element) input field to change
	       @param  options  (object) new settings to add or
	       (string) an individual setting name
	       @param  value    (any) the individual setting's value 
	    */
	    _changeTimeEntry: function(input, options, value) {
		var inst = jQuery.data(input, PROP_NAME);
		if (inst) {
		    if (typeof options == 'string') {
			var name = options;
			options = {};
			options[name] = value;
		    }
		    var currentTime = this._extractTime(inst);
		    extendRemove(inst.options, options || {});
		    if (currentTime)
			this._setTime(inst, new Date(0, 0, 0,
						     currentTime[0], currentTime[1], currentTime[2]));
		}
		jQuery.data(input, PROP_NAME, inst);
	    },
		
	    /* Remove the time entry functionality from an input.
	       @param  input  (element) input field to affect 
	    */
	    _destroyTimeEntry: function(input) {
		jQueryinput = jQuery(input);
		if (!jQueryinput.hasClass(this.markerClassName)) return;
		jQueryinput.removeClass(this.markerClassName).unbind('.timeEntry');		
		this._disabledInputs = jQuery.map(this._disabledInputs, function(value) { return (value == input ? null : value); }); // Delete entry
		jQueryinput.parent().replaceWith(jQueryinput);
		jQuery.removeData(input, PROP_NAME);
	    },
		
	    /* Initialise the current time for a time entry input field.
	       @param  input  (element) input field to update
	       @param  time   (Date) the new time (year/month/day ignored) or null for now 
	    */
	    _setTimeTimeEntry: function(input, time) {
		var inst = jQuery.data(input, PROP_NAME);
		if (inst) this._setTime(inst, time ? (typeof time == 'object' ? new Date(time.getTime()) : time) : null);
	    },
		
	    /* Retrieve the current time for a time entry input field.
	       @param  input  (element) input field to examine
	       @return  (Date) current time (year/month/day zero) or null if none 
	    */
	    _getTimeTimeEntry: function(input) {
		var inst = jQuery.data(input, PROP_NAME);
		var currentTime = (inst ? this._extractTime(inst) : null);
		return (!currentTime ? null : new Date(0, 0, 0, currentTime[0], currentTime[1], currentTime[2]));
	    },
		
	    /* Retrieve the millisecond offset for the current time.
	       @param  input  (element) input field to examine
	       @return  (number) the time as milliseconds offset or zero if none 
	    */
	    _getOffsetTimeEntry: function(input) {
		var inst = jQuery.data(input, PROP_NAME);
		var currentTime = (inst ? this._extractTime(inst) : null);
		return (!currentTime ? 0 : (currentTime[0] * 3600 + currentTime[1] * 60 + currentTime[2]) * 1000);
	    },
		
	    /* Initialise time entry.
	       @param  target  (element) the input field or (event) the focus event 
	    */
	    _doFocus: function(target) {
		var input = (target.nodeName && target.nodeName.toLowerCase() == 'input' ? target : this);
		if (jQuery.timeEntry._lastInput == input || jQuery.timeEntry._isDisabledTimeEntry(input)) {
		    jQuery.timeEntry._focussed = false;
		    return;
		}
		var inst = jQuery.data(input, PROP_NAME);
		jQuery.timeEntry._focussed = true;
		jQuery.timeEntry._lastInput = input;
		jQuery.timeEntry._blurredInput = null;
		jQuery.data(input, PROP_NAME, inst);
		jQuery.timeEntry._parseTime(inst);
		setTimeout(function() { jQuery.timeEntry._showField(inst); }, 10);
	    },
		
	    /* Note that the field has been exited.
	       @param  event  (event) the blur event 
	    */
	    _doBlur: function(event) {
		jQuery.timeEntry._blurredInput = jQuery.timeEntry._lastInput;
		jQuery.timeEntry._lastInput = null;
	    },
		
	    /* Select appropriate field portion on click, if already in the field.
	       @param  event  (event) the click event 
	    */
	    _doClick: function(event) {
		var input = event.target;
		var inst = jQuery.data(input, PROP_NAME);
		if (!jQuery.timeEntry._focussed) {
		    var fieldSize = 3;
		    inst._field = 0;
		    if (input.selectionStart != null) { // Use input select range
			for (var field = 0; field <= Math.max(1, inst._secondField, inst._ampmField); field++) {
			    var end = (field != inst._ampmField ? (field * fieldSize) + 2 : (inst._ampmField * fieldSize) + 2);
			    inst._field = field;
			    if (input.selectionStart < end) break;
			}
		    } else if (input.createTextRange) { // Check against bounding boxes
			var src = jQuery(event.srcElement);
			var range = input.createTextRange();
			var convert = function(value) {
			    return {thin: 2, medium: 4, thick: 6}[value] || value;
			};
			var offsetX = event.clientX + document.documentElement.scrollLeft -
			    (src.offset().left + parseInt(convert(src.css('border-left-width')), 10)) -
			    range.offsetLeft; // Position - left edge - alignment
			for (var field = 0; field <= Math.max(1, inst._secondField, inst._ampmField); field++) {
			    var end = (field != inst._ampmField ? (field * fieldSize) + 2 : (inst._ampmField * fieldSize) + 2);
			    range.collapse();
			    range.moveEnd('character', end);
			    inst._field = field;
			    if (offsetX < range.boundingWidth) break; // And compare
			}
		    }
		}
		jQuery.data(input, PROP_NAME, inst);
		jQuery.timeEntry._showField(inst);
		jQuery.timeEntry._focussed = false;
	    },
		
	    /* Handle keystrokes in the field.
	       @param  event  (event) the keydown event
	       @return  (boolean) true to continue, false to stop processing 
	    */
	    _doKeyDown: function(event) {
		if (event.keyCode >= 48) return true;
		var inst = jQuery.data(event.target, PROP_NAME);
		
		switch (event.keyCode) {		
		case 9: 
		    var its = jQuery(':input');
		    its.eq(its.index(this)+(event.shiftKey?-1:+1)).focus();
		    break;
		case 37: jQuery.timeEntry._changeField(inst, -1, false); break; // Previous field on left		    
		case 38: jQuery.timeEntry._adjustField(inst, -1); break; // Increment time field on down
		case 16: if(!event.shiftKey) jQuery.timeEntry._changeField(inst, +1, false); break; // Next field on right
		case 39: jQuery.timeEntry._changeField(inst, +1, false); break; // Next field on right
		case 40: jQuery.timeEntry._adjustField(inst, +1); break; // Decrement time field on up
		case 32: case 46: jQuery.timeEntry._setValue(inst, ''); break; // Clear time on delete
		}
		return false;
	    },
		
	    /* Disallow unwanted characters.
	       @param  event  (event) the keypress event
	       @return  (boolean) true to continue, false to stop processing 
	    */
	    _doKeyPress: function(event) {
		var chr = String.fromCharCode(event.charCode == undefined ? event.keyCode : event.charCode);
		if (chr < ' ') return true;
		var inst = jQuery.data(event.target, PROP_NAME);
		jQuery.timeEntry._handleKeyPress(inst, chr);
		return false;
	    },
		
	    /* Get a setting value, defaulting if necessary.
	       @param  inst  (object) the instance settings
	       @param  name  (string) the setting name
	       @return  (any) the setting value 
	    */
	    _get: function(inst, name) {
		return (inst.options[name] != null ? inst.options[name] : jQuery.timeEntry._defaults[name]);
	    },
		
	    /* Extract the time value from the input field, or default to now.
	       @param  inst  (object) the instance settings 
	    */
	    _parseTime: function(inst) {
		var currentTime = this._extractTime(inst);
		var showSeconds = this._get(inst, 'showSeconds');
		if (currentTime) {
		    inst._selectedHour = currentTime[0];
		    inst._selectedMinute = currentTime[1];
		    inst._selectedSecond = currentTime[2];
		}
		else {
		    var now = this._constrainTime(inst);
		    inst._selectedHour = now[0];
		    inst._selectedMinute = now[1];
		    inst._selectedSecond = (showSeconds ? now[2] : 0);
		}
		inst._secondField = (showSeconds ? 2 : -1);
		inst._ampmField = (this._get(inst, 'show24Hours') ? -1 : (showSeconds ? 3 : 2));
		inst._lastChr = '';
		inst._field = Math.max(0, Math.min(Math.max(1, inst._secondField, inst._ampmField), 0));
		if (inst.input.val() != '') this._showTime(inst);
	    },
		
	    /* Extract the time value from a string as an array of values, or default to null.
	       @param  inst   (object) the instance settings
	       @param  value  (string) the time value to parse
	       @return  (number[3]) the time components (hours, minutes, seconds)
	       or null if no value 
	    */
	    _extractTime: function(inst, value) {
		value = value || inst.input.val();
		var currentTime = value.split(':');
		var ampmNames = this._get(inst, 'ampmNames');
		var show24Hours = this._get(inst, 'show24Hours');
		if (currentTime.length >= 2) {
		    var isAM = !show24Hours && (value.indexOf(ampmNames[0]) > -1);
		    var isPM = !show24Hours && (value.indexOf(ampmNames[1]) > -1);
		    var hour = parseInt(currentTime[0], 10);
		    hour = (isNaN(hour) ? 0 : hour);
		    hour = ((isAM || isPM) && hour == 12 ? 0 : hour) + (isPM ? 12 : 0);
		    var minute = parseInt(currentTime[1], 10);
		    minute = (isNaN(minute) ? 0 : minute);
		    var second = (currentTime.length >= 3 ?
				  parseInt(currentTime[2], 10) : 0);
		    second = (isNaN(second) || !this._get(inst, 'showSeconds') ? 0 : second);
		    return this._constrainTime(inst, [hour, minute, second]);
		} 
		return null;
	    },
		
	    /* Constrain the given/current time to the time steps.
	       @param  inst    (object) the instance settings
	       @param  fields  (number[3]) the current time components (hours, minutes, seconds)
	       @return  (number[3]) the constrained time components (hours, minutes, seconds) 
	    */
	    _constrainTime: function(inst, fields) {
		var specified = (fields != null);
		if (!specified) {
		    var now = this._determineTime(inst, this._get(inst, 'defaultTime')) || new Date();
		    fields = [now.getHours(), now.getMinutes(), now.getSeconds()];
		}
		return fields;
	    },
		
	    /* Set the selected time into the input field.
	       @param  inst  (object) the instance settings 
	    */
	    _showTime: function(inst) {
		var show24Hours = this._get(inst, 'show24Hours');
		var currentTime = (this._formatNumber(show24Hours ? inst._selectedHour :
						      ((inst._selectedHour + 11) % 12) + 1) + ':' +
				   this._formatNumber(inst._selectedMinute) +
				   (this._get(inst, 'showSeconds') ? ':' +
				    this._formatNumber(inst._selectedSecond) : '') +
				   (show24Hours ?  '' : this._get(inst, 'ampmNames')[(inst._selectedHour < 12 ? 0 : 1)]));
		this._setValue(inst, currentTime);
		this._showField(inst);
	    },
		
	    /* Highlight the current time field.
	       @param  inst  (object) the instance settings 
	    */
	    _showField: function(inst) {
		var input = inst.input[0];
		if (inst.input.is(':hidden') || jQuery.timeEntry._lastInput != input) return;
		var fieldSize = 3;
		var start = (inst._field == inst._ampmField ? (inst._ampmField * fieldSize) - 1 : (inst._field * fieldSize));
		var end = start + (inst._field == inst._ampmField ? 2 : 2);
		if (input.setSelectionRange) { // Mozilla
		    input.setSelectionRange(start, end);
		}
		else if (input.createTextRange) { // IE
		    var range = input.createTextRange();
		    range.moveStart('character', start);
		    range.moveEnd('character', end - inst.input.val().length);
		    range.select();
		}
		if (!input.disabled) input.focus();
	    },
		
	    /* Ensure displayed single number has a leading zero.
	       @param  value  (number) current value
	       @return  (string) number with at least two digits 
	    */
	    _formatNumber: function(value) {
		return (value < 10 ? '0' : '') + value;
	    },
		
	    /* Update the input field and notify listeners.
	       @param  inst   (object) the instance settings
	       @param  value  (string) the new value 
	    */
	    _setValue: function(inst, value) {
		if (value != inst.input.val()) inst.input.val(value).trigger('change');
	    },
		
	    /* Move to previous/next field, or out of field altogether if appropriate.
	       @param  inst     (object) the instance settings
	       @param  offset   (number) the direction of change (-1, +1)
	       @param  moveOut  (boolean) true if can move out of the field
	       @return  (boolean) true if exitting the field, false if not 
	    */
	    _changeField: function(inst, offset, moveOut) {
		var atFirstLast = (inst.input.val() == '' || inst._field == (offset == -1 ? 0 : Math.max(1, inst._secondField, inst._ampmField)));
		if (!atFirstLast) inst._field += offset;
		this._showField(inst);
		inst._lastChr = '';
		jQuery.data(inst.input[0], PROP_NAME, inst);
		return (atFirstLast && moveOut);
	    },
		
	    /* Update the current field in the direction indicated.
	       @param  inst    (object) the instance settings
	       @param  offset  (number) the amount to change by 
	    */
	    _adjustField: function(inst, offset) {
		if (inst.input.val() == '') offset = 0;
		this._setTime(inst, new Date(0, 0, 0,
					     inst._selectedHour + (inst._field == 0 ? offset : 0) +
					     (inst._field == inst._ampmField ? offset * 12 : 0),
					     inst._selectedMinute + (inst._field == 1 ? offset : 0),
					     inst._selectedSecond + (inst._field == inst._secondField ? offset : 0)));
	    },
		
	    /* Check against minimum/maximum and display time.
	       @param  inst  (object) the instance settings
	       @param  time  (Date) an actual time or
	       (number) offset in seconds from now or
	       (string) units and periods of offsets from now 
	    */
	    _setTime: function(inst, time) {
		time = this._determineTime(inst, time);
		var fields = this._constrainTime(inst, time ?
						 [time.getHours(), time.getMinutes(), time.getSeconds()] : null);
		time = new Date(0, 0, 0, fields[0], fields[1], fields[2]);
		// Normalise to base date
		var time = this._normaliseTime(time);
		var minTime = this._normaliseTime(this._determineTime(inst, this._get(inst, 'minTime')));
		var maxTime = this._normaliseTime(this._determineTime(inst, this._get(inst, 'maxTime')));
		// Ensure it is within the bounds set
		time = (minTime && time < minTime ? minTime :
			(maxTime && time > maxTime ? maxTime : time));
		inst._selectedHour = time.getHours();
		inst._selectedMinute = time.getMinutes();
		inst._selectedSecond = time.getSeconds();
		this._showTime(inst);
		jQuery.data(inst.input[0], PROP_NAME, inst);
	    },

		/* Normalise time object to a common date.
		   @param  time  (Date) the original time
		   @return  (Date) the normalised time 
		*/
		_normaliseTime: function(time) {
		if (!time) return null;
		time.setFullYear(1900);
		time.setMonth(0);
		time.setDate(0);
		return time;
	    },
		
	    /* A time may be specified as an exact value or a relative one.
	       @param  inst     (object) the instance settings
	       @param  setting  (Date) an actual time or
	       (number) offset in seconds from now or
	       (string) units and periods of offsets from now
	       @return  (Date) the calculated time 
	    */
	    _determineTime: function(inst, setting) {
		var offsetNumeric = function(offset) { // E.g. +300, -2
		    var time = new Date();
		    time.setTime(time.getTime() + offset * 1000);
		    return time;
		};
		var offsetString = function(offset) { // E.g. '+2m', '-4h', '+3h +30m' or '12:34:56PM'
		    var fields = jQuery.timeEntry._extractTime(inst, offset); // Actual time?
		    var time = new Date();
		    var hour = (fields ? fields[0] : time.getHours());
		    var minute = (fields ? fields[1] : time.getMinutes());
		    var second = (fields ? fields[2] : time.getSeconds());
		    if (!fields) {
			var pattern = /([+-]?[0-9]+)\s*(s|S|m|M|h|H)?/g;
			var matches = pattern.exec(offset);
			while (matches) {
			    switch (matches[2] || 's') {
			    case 's' : case 'S' : second += parseInt(matches[1], 10); break;
			    case 'm' : case 'M' : minute += parseInt(matches[1], 10); break;
			    case 'h' : case 'H' : hour += parseInt(matches[1], 10); break;
			    }
			    matches = pattern.exec(offset);
			}
		    }
		    time = new Date(0, 0, 10, hour, minute, second, 0);
		    if (/^!/.test(offset)) { // No wrapping
			if (time.getDate() > 10)
			    time = new Date(0, 0, 10, 23, 59, 59);
			else if (time.getDate() < 10)
			    time = new Date(0, 0, 10, 0, 0, 0);
		    }
		    return time;
		};
		return (setting ? (typeof setting == 'string' ? offsetString(setting) :
				   (typeof setting == 'number' ? offsetNumeric(setting) : setting)) : null);
	    },
		
	    /* Update time based on keystroke entered.
	       @param  inst  (object) the instance settings
	       @param  chr   (ch) the new character 
	    */
	    _handleKeyPress: function(inst, chr) {
		if (chr == ':') this._changeField(inst, +1, false);
		else if (chr >= '0' && chr <= '9') { // Allow direct entry of time
		    var key = parseInt(chr, 10);
		    var value = parseInt(inst._lastChr + chr, 10);
		    var show24Hours = this._get(inst, 'show24Hours');
		    var hour = (inst._field != 0 ? inst._selectedHour :
				(show24Hours ? (value < 24 ? value : key) :
				 (value >= 1 && value <= 12 ? value :
				  (key > 0 ? key : inst._selectedHour)) % 12 +
				 (inst._selectedHour >= 12 ? 12 : 0)));
		    var minute = (inst._field != 1 ? inst._selectedMinute :
				  (value < 60 ? value : key));
		    var second = (inst._field != inst._secondField ? inst._selectedSecond :
				  (value < 60 ? value : key));
		    var fields = this._constrainTime(inst, [hour, minute, second]);
		    this._setTime(inst, new Date(0, 0, 0, fields[0], fields[1], fields[2]));
		    inst._lastChr = chr;
		}
		else if (!this._get(inst, 'show24Hours')) { // Set am/pm based on first char of names
		    chr = chr.toLowerCase();
		    var ampmNames = this._get(inst, 'ampmNames');
		    if ((chr == ampmNames[0].substring(0, 1).toLowerCase() && inst._selectedHour >= 12) ||
			(chr == ampmNames[1].substring(0, 1).toLowerCase() && inst._selectedHour < 12)) {
			var saveField = inst._field;
			inst._field = inst._ampmField;
			this._adjustField(inst, +1);
			inst._field = saveField;
			this._showField(inst);
		    }
		}
	    }
	});
    
    /* jQuery extend now ignores nulls!
       @param  target  (object) the object to update
       @param  props   (object) the new settings 
       @return  (object) the updated object 
    */
    function extendRemove(target, props) {
	jQuery.extend(target, props);
	for (var name in props) if (props[name] == null) target[name] = null;
	return target;
    }
    
    // Commands that don't return a jQuery object
    var getters = ['getOffset', 'getTime', 'isDisabled'];
    
    /* Attach the time entry functionality to a jQuery selection.
       @param  command  (string) the command to run (optional, default 'attach')
       @param  options  (object) the new settings to use for these countdown instances (optional)
       @return  (jQuery) for chaining further calls 
    */
    jQuery.fn.timeEntry = function(options) {
	var otherArgs = Array.prototype.slice.call(arguments, 1);
	if (typeof options == 'string' && jQuery.inArray(options, getters) > -1) {
	    return jQuery.timeEntry['_' + options + 'TimeEntry'].apply(jQuery.timeEntry, [this[0]].concat(otherArgs));
	}
	return this.each(function() {
		var nodeName = this.nodeName.toLowerCase();
		if (nodeName == 'input') {
		    if (typeof options == 'string')
			jQuery.timeEntry['_' + options + 'TimeEntry'].apply(jQuery.timeEntry, [this].concat(otherArgs));
		    else {
			// Check for settings on the control itself
			var inlineSettings = (jQuery.fn.metadata ? jQuery(this).metadata() : {});
			jQuery.timeEntry._connectTimeEntry(this, jQuery.extend(inlineSettings, options));
		    }
		} 
	    });
    };
    
    /* Initialise the time entry functionality. */
    jQuery.timeEntry = new TimeEntry(); // Singleton instance
    
})(jQuery);
