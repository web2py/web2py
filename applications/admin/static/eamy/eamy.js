/*
 * eAmy.Offline - Amy Editor embedded for offline use.
 * http://www.april-child.com/amy
 *
 * Published under MIT License.
 * Copyright (c) 2007-2008 Petr Krontorád, April-Child.com

 Permission is hereby granted, free of charge, to any person
 obtaining a copy of this software and associated documentation
 files (the "Software"), to deal in the Software without
 restriction, including without limitation the rights to use,
 copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following
 conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 OTHER DEALINGS IN THE SOFTWARE.
  
 *
 *
 * This file is auto-generated from original Fry Framework and Amy Editor sources..
 */





/*
 * AC Fry - JavaScript Framework v1.0
 * (c)2006 Petr Krontorad, April-Child.com
 * Portions of code based on WHOA Bender Framework, (c)2002-2005 Petr Krontorad, WHOA Group.
 * http://www.april-child.com. All rights reserved.
 * See the license/license.txt for additional details regarding the license.
 * Special thanks to Matt Groening and David X. Cohen for all the robots.
 */

/* Reserving global `fry` object */
var fry = 
{
	version:1.0,
	__production_mode:false
};

// String prototype enhancements
String.prototype.camelize = function()
{
	return this.replace( /([-_].)/g, function(){ return arguments[0].substr(1).toUpperCase();} );
}

String.prototype.decamelize = function()
{
	return this.replace( /([A-Z])/g, function(){ return '-'+arguments[0].toLowerCase();} );
}

String.prototype.trim = function()
{
    return this.replace(/(^\s*)|(\s*$)/g, '' );
}

String.prototype.stripLines = function()
{
	return this.replace( /\n/g, '' );
}

String.prototype.stripMarkup = function()
{
	return this.replace( /<(.|\n)+?>/g, '' );
}

String.prototype.replaceMarkup = function( charRep )
{
	return this.replace( /(<(.|\n)+?>)/g, function()
	{
		var t = '';
		for ( var i=0; i<arguments[0].length; i++ )
		{
			t += charRep;
		}
		return t;
	} );
}

String.prototype.encodeMarkup = function()
{
	return this.replace( /&/g, '&amp;' ).replace( />/g, '&gt;' ).replace( /</g, '&lt;' );
}

String.prototype.decodeMarkup = function()
{
	return this.replace( /&lt;/g, '<' ).replace( /&gt;/g, '>' ).replace( /&amp;/g, '&' );
}

String.prototype.surround = function(t, side)
{
	side = side || 3;
	return (1==1&side?t:'')+this+(2==2&side?t:'');
}

String.prototype.surroundTag = function(t)
{
	return '<'+t+'>'+this+'</'+t+'>';
}

// example of use: var pattern = '? is ?; alert(pattern.embed('Decin', 'sunny')); pattern = '@city is @weather'; alert(pattern.embed({weather:'cloudy', city:'Decin'}))
String.prototype.embed = function()
{
	var t = this;
	if ( 1 == arguments.length && 'object' == typeof arguments[0] )
	{
		// named placeholders
		for ( var i in arguments[0] )
		{
			eval('var re=/@'+i+'/g;');
			t = t.replace(re, arguments[0][i]);
		}
	}
	else
	{
		// anonymous placeholders `?`
		for ( var i=0; i<arguments.length; i++ )
		{
			var ix = t.indexOf('?');
			if ( -1 != ix )
			{
				t = t.substr(0,ix)+arguments[i]+t.substr(ix+1);
				continue;
			}
			break;
		}
	}
	return t;
}

// Tuning helpers - dealing with user-agent differences
var $__tune = 
{
	__prop:{},
	isIE:('function' == typeof window.ActiveXObject),
	isSafari:-1!=navigator.appVersion.indexOf('AppleWebKit'),
	isOpera:-1!=navigator.appName.indexOf('pera'),
	isMac:-1!=navigator.appVersion.indexOf('intosh'),
	isGecko:false,
	node:
	{
		getOpacity:function(node)
		{
		    if ( !node || !node.style )
		    {
		        return 1.0;
		    }
			if ( $__tune.isIE )
			{
				var f = node.style.filter;
				if ( !f || -1 == f.indexOf('alpha') )
				{
					return 1.0;
				}
				return 1.0;
			}
			return parseFloat(node.style[$__tune.isGecko?'MozOpacity':'opacity'] || 1.0);
		},
		setOpacity:function(node, opacity)
		{
		    if ( !node || !node.style )
		    {
		        return;
		    }
		    if ( 0 > opacity )
		    {
		        opacity = 0;
		    }
		    if ( 1 < opacity )
		    {
		        opacity = 1;
		    }
			if ( $__tune.isIE )
			{
				node.style.filter = 'alpha(opacity='+(100*opacity)+')';
			}
			else
			{
				node.style.opacity = opacity;
				node.style.MozOpacity = opacity;
			}
		},
		getPageScrollPosition:function()
		{
			var d = document.documentElement;
			if ( d && d.scrollTop) 
			{
				return [d.scrollLeft, d.scrollTop];
			} 
			else if (document.body) 
			{
				return [document.body.scrollLeft, document.body.scrollTop];
			}
			else
			{
				return [0, 0];
			}
		}
	},
	event:
	{
		get:function(evt, type)
		{
			if ( $notset(evt.target) )
			{
				evt.target = evt.srcElement;
				evt.stopPropagation = function()
				{
					window.event.cancelBubble = true;
				};
			}
			evt.stop = function()
			{
				evt.stopPropagation();
				evt.stopped = true;
			}
			evt.$ = $(evt.target);
			if ( $notset(evt.pageX) )
			{
				evt.pageX = evt.clientX + document.body.scrollLeft;
				evt.pageY = evt.clientY + document.body.scrollTop;
			}
			evt.getOffsetX = function()
			{
				if ( $notset(evt.offsetX) )
				{
					var pos = evt.$.abspos();
					evt.offsetX = evt.pageX - pos.x;
					evt.offsetY = evt.pageY - pos.y;
				}
				return evt.offsetX;
			}
			evt.getOffsetY = function()
			{
				if ( $notset(evt.offsetY) )
				{
					var pos = evt.$.abspos();
					evt.offsetX = evt.pageX - pos.x;
					evt.offsetY = evt.pageY - pos.y;
				}
				return evt.offsetY;				
			}
			evt.isAnyControlKeyPressed = function()
			{
				return evt.metaKey||evt.ctrlKey||evt.altKey||evt.shiftKey;
			}
			evt.KEY_ESCAPE = 27;
			evt.KEY_ENTER = 13;
			evt.KEY_ARR_RIGHT = 39;
			evt.KEY_ARR_LEFT = 37;
			evt.KEY_ARR_UP = 38;
			evt.KEY_ARR_DOWN = 40;
			return evt;
		},
		addListener:function(node, type, listener)
		{
			if ( $__tune.isIE && node.attachEvent )
			{
                node.attachEvent('on'+type, listener);
			}
			else
			{
				node.addEventListener(type, listener, false);
			}
		},
		removeListener:function(node, type, listener)
		{
			if ( node.detachEvent )
			{
                node.detachEvent('on'+type, listener);
                node['on'+type] = null;
			}
			else if ( node.removeEventListener )
			{
				node.removeEventListener(type, listener, false);
			}				
		}		
	},
	behavior:
	{
		disablePageScroll:function()
		{
			if ( $notset($__tune.__prop.page_scroll) )
			{
				$__tune.__prop.page_scroll = [$().s().overflow, $().ga('scroll')];
			}
			$().s('overflow:hidden').sa('scroll', 'no');
		},
		enablePageScroll:function()
		{
			$().s('overflow:auto').sa('scroll', 'yes');
		},
		disableCombos:function()
		{
			$().g('select', function(node)
			{
				node.sa('__dis_combo', node.s().visibility);
				$(node).v(false);
			});
		},
		enableCombos:function()
		{
			$().g('select', function(node)
			{
				node.s({visibility:node.ga('__dis_combo') || 'visible'});
			});
		},
		clearSelection:function()
		{
			try
			{
				if ( window.getSelection )
				{
					if ( $__tune.isSafari )
					{
						window.getSelection().collapse();
					}
					else
					{
						window.getSelection().removeAllRanges();
					}
				}
				else
				{
					if ( document.selection )
					{
						if ( document.selection.empty )
						{
							document.selection.empty();
						}
						else
						{
							if ( document.selection.clear )
							{
								document.selection.clear();
							}
						}
					}
				}
			}
			catch (e) {}
		},
		makeBodyUnscrollable:function()
		{
			$().s('position:fixed').w(fry.ui.info.page.width);
		}
	},
	ui:
	{
		scrollbarWidth:-1!=navigator.appVersion.indexOf('intosh')?15:17
	},
	selection:
	{
		setRange:function(el, selectionStart, selectionEnd)
		{
			if (el.setSelectionRange)
			{
				el.focus();
				el.setSelectionRange(selectionStart, selectionEnd);
			}
			else if (el.createTextRange)
			{
				var range = el.createTextRange();
				range.collapse(true);
				range.moveEnd('character', selectionEnd);
				range.moveStart('character', selectionStart);
				range.select();
			}
		}
	}
}
// some browsers masks its presence having Gecko string somewhere inside its userAgent field...
$__tune.isGecko = !$__tune.isSafari&&!$__tune.isIE&&-1!=navigator.userAgent.indexOf('ecko');
$__tune.isSafari2 = $__tune.isSafari && -1 != navigator.appVersion.indexOf('Kit/4');
$__tune.isSafari3 = $__tune.isSafari && -1 != navigator.appVersion.indexOf('Kit/5');


// Node manipulations

function ACNode(node)
{
	this.$ = node;
	if ( node )
	{
		node.setAttribute('fryis', '1');		
	}
}
// `$$` creates new node
ACNode.prototype.$$ = function(tagName)
{
	return $$(tagName);
}
// *is* - tells whether node is a part of the active DOM tree (that is displayed on page). Node may exist only in memory before appending or after removing when references, in which case node.is() will return false.
ACNode.prototype.is = function()
{
	return this.$ && null != this.$.parentNode;
}
// *i*d
ACNode.prototype.i = function(id)
{
	if ( 'undefined' == typeof id )
	{
		return this.$.id||'';
	}
	this.$.id = id;
	return this;
}
// class *n*ame
ACNode.prototype.n = function(n)
{
	if ( 'undefined' == typeof n)
	{
		return this.$.className||'';
	}
	this.$.className = n;
	return this;
}
// *e*vent listener, if called with one argument only, previously registered listeners are removed
ACNode.prototype.e = function(t, c, oneUseOnly)
{
	var ser_type_id = 'fryse-'+t;
	if ( !c )
	{
		if ( null != this.$.getAttribute(ser_type_id) )
		{
			var ser_listeners = this.$.getAttribute(ser_type_id).split(',');
	//		console.log('*E* removing listeners for %s, listeners: %s', t, ser_listeners);
			for ( var i=0; i<ser_listeners.length; i++ )
			{
				$__tune.event.removeListener(this.$, t, self[ser_listeners[i]]);
				self[ser_listeners[i]] = null;
			}
			this.$['on'+t] = null;
			this.$.removeAttribute(ser_type_id);
		}
		return this;
	}
	var hash = t+(''+Math.random()).substr(2);
	var ser_listeners = null != this.$.getAttribute(ser_type_id) ? this.$.getAttribute(ser_type_id).split(',') : [];
	ser_listeners.push(hash);
	this.$.setAttribute(ser_type_id, ser_listeners.join(','));
//	console.log('*E* add listener self.%s for %s', hash, t);
	self[hash] = function(evt)
	{
		evt.removeListener = function()
		{
			$__tune.event.removeListener(evt.$.$, t, self[hash]);
//			console.log('*E* remove listener self.%s for %s', hash, t);
			c = null;
			evt = null;
			self[hash] = null;
		}
		evt = evt || self.event;
		if ( null != c )
		{
			c($__tune.event.get(evt));			
		}
		if ( null != evt )
		{
			if ( oneUseOnly )
			{
				evt.removeListener();
				return;
			}
			else if ( evt.stopped )
			{
//				console.log('*E* stop self.%s for %s', hash, t);
				evt = null;				
			}
		}
	};
	this.$.setAttribute('fryhe', 1);
	$__tune.event.addListener(this.$, t, self[hash]);
	return this;
}

function __fry_esupressed(evt)
{
	evt = evt || self.event;
	if ( !evt.stopPropagation )
	{
		evt.cancelBubble = true;
	}
	else
	{
		evt.stopPropagation();
	}
	evt = null;
	return false;
}
// *e*vent *s*upressed - special case when you want to receive an event, do nothing about it and stop it from propagating
ACNode.prototype.es = function(t)
{
	if ( $__tune.isIE && this.$.attachEvent )
	{
        this.$.attachEvent('on'+t, __fry_esupressed);
	}
	else if ( this.$.addEventListener )
	{
		this.$.addEventListener(t, __fry_esupressed, false);
	}
}
// *x* coordinate
ACNode.prototype.x = function(x)
{
	if ( 'undefined' == typeof x )
	{
		return parseInt(this.$.style.left||0);
	}
	this.$.style.left = x+'px';
	return this;
}
// *y* coordinate
ACNode.prototype.y = function(y)
{
	if ( 'undefined' == typeof y )
	{
		return parseInt(this.$.style.top||0);
	}
	this.$.style.top = y+'px';
	return this;
}
// *abs*olute page *pos*ition coordinates (you can optionally specify node to which the position is calculated), returns {x:, y:} coordinates
ACNode.prototype.abspos = function(n)
{
	if ( document.getBoxObjectFor )
	{
		var p = document.getBoxObjectFor(this.$);
		return {x:p.x, y:p.y};
	}
	if ( this.$.getBoundingClientRect )
	{
		var p = this.$.getBoundingClientRect();
		return {x:p.left+(document.documentElement.scrollLeft || document.body.scrollLeft), y:p.top+(document.documentElement.scrollTop || document.body.scrollTop)};
	}
	var p = {x:0, y:0};
	var n2 = this.$;
	while ( document.body != n2 && document != n2 && n != n2 )
	{
		p.x += n2.offsetLeft - n2.scrollLeft;
		p.y += n2.offsetTop - n2.scrollTop;
		if ( n2.offsetParent )
		{
			n2 = n2.offsetParent;
		}
		else
		{
			n2 = n2.parentNode;
		}
	}
	return p;
}
// *pos*ition, if true - absolute, false - relative
ACNode.prototype.pos = function(p)
{
	if ( 'undefined' == typeof p )
	{
		return 'absolute' == this.$.style.position;
	}
	this.$.style.position = p ? 'absolute' : 'relative';
	return this;
}
// *z*-index coordinate
ACNode.prototype.z = function(z)
{
	if ( 'undefined' == typeof z )
	{
		return parseInt(this.$.style.zIndex||0);
	}
	this.$.style.zIndex = z;
	return this;
}
// *w*idth
ACNode.prototype.w = function(w)
{
	if ( 'undefined' == typeof w )
	{
		return parseInt(this.$.style.width||this.$.offsetWidth);
	}
	this.$.style.width = w+'px';
	return this;
}
// *h*eight
ACNode.prototype.h = function(h)
{
	if ( 'undefined' == typeof h )
	{
		return parseInt(this.$.style.height||this.$.offsetHeight);
	}
	this.$.style.height = h+'px';
	if ( $__tune.isIE && 8 > h )
	{
		this.$.style.fontSize = '1px';
	}
	return this;
}
// *s*tyle information - argument can be either "{color:'red', backgroundColor:'blue'}" or "'color:red;background-color:blue'"
ACNode.prototype.s = function(s)
{
	if ( 'undefined' == typeof s )
	{
		return this.$.style;
	}
	if ( 'object' == typeof s )
	{
		for ( var n in s )
		{
			this.$.style[n] = s[n];
		}
	}
	else if ( 'string' == typeof s )
	{
		if ( '' != s )
		{
			var styles = s.split(';');
			for ( var i=0; i<styles.length; i++ )
			{
				var style = styles[i].split(':');
				if ( 2 == style.length )
				{
					this.$.style[style[0].trim().camelize()] = style[1].trim();
				}
			}
		}
	}
	return this;
}
// *o*pacity
ACNode.prototype.o = function(o)
{
	if ( 'undefined' == typeof o )
	{
		return $__tune.node.getOpacity(this.$);
	}
	$__tune.node.setOpacity(this.$, o);
	return this;
}
// *d*isplay
ACNode.prototype.d = function(d)
{
	if ( 'undefined' == typeof d )
	{
		return 'none' != this.$.style.display;
	}
	this.$.style.display = d ? 'block' : 'none';
	return this;						
}
// *v*isibility
ACNode.prototype.v = function(v)
{
	if ( 'undefined' == typeof v )
	{
		return 'hidden' != this.$.style.visibility;
	}
	this.$.style.visibility = v ? 'visible' : 'hidden';
	return this;			
}
// H*T*ML source (equivalent to infamous innerHTML, remember innerHTML is not considered *evil* here - see the KISS principle, plus it's actually faster than DOM)
ACNode.prototype.t = function(t)
{
	if ( 'undefined' == typeof t )
	{
		return this.$.innerHTML;
	}
	this.rc();
	this.$.innerHTML = t;
	return this;
}
// *p*arent node
ACNode.prototype.p = function(p)
{
	if ( 'undefined' == typeof p )
	{
		return $(this.$.parentNode);
	}
	return $(p).a(this);
}
// *g*et child node(s), the format of a query might be either `[['table',0],['tr',2],['td',4]]`, `['table',['tr',2],['td',4]]`, 'table:0/tr:2/td:4' or 'table/tr:2/td:4'. you can use `*` in path for any node
ACNode.prototype.g = function(q)
{
	var lst = [];
	if ( 'string' == typeof q )
	{
		var qt = q.split('/');
		q = [];
		for ( var i=0; i<qt.length; i++ )
		{
			var qtt = qt[i].split(':');
			q[q.length] = qtt;
		}
	}
	var lookup = function(node, qIndex)
	{
		if ( !node )
		{
			return;
		}
		var qq = q[qIndex];
		var is_final_index = q.length-1 == qIndex;
		var ls = node.getElementsByTagName(qq[0]);
		var num = ls.length;
		if ( 2 == qq.length )
		{
			// specific node required
			if ( is_final_index )
			{
				// store results
				lst.push($(ls.item(parseInt(qq[1]))));
			}
			else
			{
				lookup(ls.item(parseInt(qq[1])), qIndex+1);
			}
		}
		else
		{
			// all nodes required
			for ( var i=0; i<num; i++ )
			{
				if ( is_final_index )
				{
					lst.push($(ls.item(i)));
				}
				else
				{
					lookup(ls.item(i), qIndex+1);
				}
			}
		}
		ls = null;
	}
	lookup(this.$, 0);
	lookup = null;
	var num = lst.length;
	if ( 1 == num )
	{
		return lst[0];
	}
	else if ( 0 == num )
	{
		lst = null;
	}
	return lst;
}
// *g*et *p*arent node at some path - allows for returning grand-grand-grand...parent node. imagine node tree: `div>div>table>tbody>tr>td>` and node at `td`
// to return second div you would call `gp('tr/tbody/table/div')` or `tr/table/div:1`, first div could be acquired using `table/div:2` etc. you can use `*` for any node.
ACNode.prototype.gp = function(q)
{
	if ( 'string' == typeof q )
	{
		q = q.split('/');
	}
	var fq = [];
	for ( var i=0; i<q.length; i++ )
	{
		if ( -1 != q[i].indexOf(':') )
		{
			q[i] = q[i].split(':');
			for ( var ii=0; ii<q[i][1]; ii++ )
			{
				fq.push(q[i][0]);
			}
		}
		else
		{
			fq.push(q[i]);
		}
	}
	var c = 0;
	var p = this.$;
	while ( p && c < fq.length)
	{
		p = p.parentNode;
		if ( '*' == fq[c] || fq[c] == p.tagName.toLowerCase() )
		{
			c++;
		}
	}
	return $(p);
}
// *a*ppends child node
ACNode.prototype.a = function(n)
{
	if ( 'undefined' != typeof n['$'] )
	{
		n = n.$;
	}
	return $(this.$.appendChild(n));
}
// *a*ppend H*T*ML code - adds innerHTML to existing node code
ACNode.prototype.at = function(t)
{
	var ht = this.$.innerHTML;
	this.$.innerHTML = ht + t;
	return this;
}
// *r*emoves child node
ACNode.prototype.r = function(n)
{
	n = $(n);
	if ( null != n && n.is() )
	{
		n.rs();
	}
	return this;
}
// *r*emove *c*hildren
ACNode.prototype.rc = function()
{
	if ( !this.$ )
	{
		return this;
	}
	__fry_gcnode(this.$, true);
	return this;
}
// *r*emoves *s*elf - ! does not return self - therefor the call to .rs() must always be the last in a pipe
ACNode.prototype.rs = function()
{
	if ( !this.$ )
	{
		return;
	}
	__fry_gcnode(this.$);
	this.$ = null;
}
// *i*nserts *c*hild node before specific referenced node (rn)
ACNode.prototype.ib = function(n, rn)
{
	if ( 'undefined' != typeof n['$'] )
	{
		n = n.$;
	}
	if ( 'undefined' != typeof rn['$'] )
	{
		rn = rn.$;
	}
	return $(this.$.insertBefore(n,rn));
}
// *i*nserts *c*hild node after specific referenced node (rn)
ACNode.prototype.ia = function(n, rn)
{
	if ( 'undefined' != typeof n['$'] )
	{
		n = n.$;
	}
	if ( null == $(rn).ns() )
	{
		return $(this.$.appendChild(n));
	}
	else
	{
		return $(this.$.insertBefore(n,($(rn).ns()).$));
	}
}
// *f*irst *c*hild of the node - always returns first $-ed node (ignoring text, comment etc. nodes)
ACNode.prototype.fc = function()
{
	if ( !this.$ )
	{
		return null;
	}
	var n = this.$.firstChild;
	while ( null != n && 1 != n.nodeType )
	{
		n = n.nextSibling;
	}
	return null != n ? $(n) : null;
}
// *l*ast *c*hild of the node - always returns last $-ed node (ignoring text, comment etc. nodes)
ACNode.prototype.lc = function()
{
	if ( !this.$ )
	{
		return null;
	}
	var n = this.$.lastChild;
	while ( null != n && 1 != n.nodeType )
	{
		n = n.previousSibling;
	}
	return null != n ? $(n) : null;			
}
// *n*ext *s*ibling of the node - always returns first $-ed node (ignoring text, comment etc. nodes)
ACNode.prototype.ns = function()
{
	var n = this.$.nextSibling;
	while ( null != n && 1 != n.nodeType )
	{
		n = n.nextSibling;
	}
	return null != n ? $(n) : null;
}
// *p*revious *s*ibling of the node - always returns last $-ed node (ignoring text, comment etc. nodes)
ACNode.prototype.ps = function()
{
	var n = this.$.previousSibling;
	while ( null != n && 1 != n.nodeType )
	{
		n = n.previousSibling;
	}
	return null != n ? $(n) : null;			
}
// *g*et *a*ttribute
ACNode.prototype.ga = function(n)
{
    if ( !this.$ )
    {
        return null;
    }
	return this.$.getAttribute(n);
}
// *s*et *a*ttribute
ACNode.prototype.sa = function(n, v)
{
	this.$.setAttribute(n, v);
	return this;
}
// *r*emove *a*ttribute
ACNode.prototype.ra = function(n)
{
	this.$.removeAttribute(n);
	return this;
}
// *dup*licate node
ACNode.prototype.dup = function()
{
	return $(this.$.cloneNode(true));
}

// `$_` converts any value into string - useful for numeric values before calling for String enhanced methods.
var $_ = function(t)
{
	return ''+t;
}

// `$$` creates new node with specified tag name, returns $-ed node
var $$ = function(n)
{
	return $(document.createElement(n||'div'));
}

// returns $-ed node for existing node, argument can be either ID string or node itself (standard or $-ed). If argument is omitted, returns the body node
var $ = function(id)
{
	if ( 'undefined' == typeof id )
	{
		return $(document.body || document.getElementsByTagName('body').item(0));
	}
	if ( 'undefined' == id || null == id )
	{
		return null;
	}
	if ( 'object' != typeof id )
	{
		return new ACNode(document.getElementById(id));
	}
	else
	{
		if ( id instanceof ACNode )
		{
			return id;
		}
		if ( 1 != id.nodeType )
		{
			return null;
		}
		return new ACNode(id);
	}
}

// Language constructs

/*  $class
	======
	Creates new class, multiple class inheritance is allowed.
	Usage:
	
	$class('AClass',
	{
		construct:function(a)
		{
			this.a = a || '';
		},
		destruct:function()
		{
			$delete(this.a);
		}
	});
	AClass.prototype.hello = function(msg)
	{
		alert(msg + this.a);
	}
	$class('BClass < AClass',
	{
		construct:function(a, b)
		{
			this.b = b || '';
		}
	});
	$class('CClass');
	$class('DClass < BClass, CClass');
	DClass.prototype.hello = function(msg, msg2)
	{
		$call(this, 'AClass.hello', msg);
		alert(msg2 + this.b);
	}
*/
var $class = function(className, methods)
{
	if ( 'string' != typeof className )
	{
		throw new FryException(29, 'Class inheritance error. Undefined class name.');
	}
	var n = className.split('<');
	className = n[0].replace(/ /g, '');
	var bases = [];
	if ( 1 == n.length )
	{
		// no inheritance, will inherit from `Object`
		bases[0] = 'Object';
	}
	else
	{
		// defined inheritance, might be multiple eg. `ClassA < ClassB, ClassC`
		bases = n[1].split(',');
	}
	var getSource = function(s)
	{
		s = ''+s;
		return s.substring(s.indexOf('{')+1, s.lastIndexOf('}'));
	}
	var getParams = function(s, p)
	{
		p = p || {};
		s = ''+s;
		s = s.substring(s.indexOf('(')+1, s.indexOf(')')).split(',');
		for ( var i in s )
		{
			var n = s[i].replace(/ /g, '');
			if ( !p[n] && '' != n )
			{
				p[n] = true;
			}
		}
		return p;
	}
	var preprocessSource = function(s, cn)
	{
		// parsing source code and replacing calls to base constructor or methods
		eval('var re = /'+cn+'\.([^\\(]*)\\(([\\)]*)/g;');		
		s = s.replace(re, function()
		{
			return 'this.__'+cn+'_'+arguments[1]+'.call(this'+(''==arguments[2].replace(/ /g, '')?',':'')+arguments[2];
		});
		eval('re = /'+cn+'[^\\(]*\\(([\\)]*)/g;');
		s = s.replace(re, function()
		{
			return 'this.__'+cn+'_construct.call(this'+(''==arguments[1].replace(/ /g, '')?',':'')+arguments[1];
		});
		return s;
	}	
	methods = methods || {};
	var c_code = '';
	var d_code = '';
	var params = {};
	for ( var i in bases )
	{
		bases[i] = bases[i].replace(/ /g, '');
		if ( 'Object' == bases[i] )
		{
			continue;
		}
		eval('var b_code='+bases[i]+';');
		params = getParams(b_code, params);
		b_code = getSource(b_code);
		c_code += b_code+';';
		eval('var d_code='+bases[i]+'.prototype.destruct||"{}";');
		d_code = getSource(d_code);
		d_code += d_code+';';
	}
	params = getParams(methods.construct||'', params);
	var p = [];
	for ( var i in params)
	{
		p.push(i);
	}
	if ( methods.construct )
	{
		// own constructor defined
		oc_code = getSource(methods.construct);
		for ( var i in bases )
		{
			if ( 'Object' != bases[i] )
			{
				oc_code = preprocessSource(oc_code, bases[i]);				
			}
		}
		c_code += oc_code;
	}	
	d_code += methods.destruct ? getSource(methods.destruct) : '';
	try
	{
		eval('var newClass=function('+p.join(',')+'){'+c_code+'};');		
	}
	catch (e)
	{
		throw new FryException(30, 'Class inheritance error. Class `?`, constructor: `?`, error message: `?`.'.embed(className, c_code, e));
	}
	newClass.prototype = new Object();
	for ( var i in bases )
	{
		if ( 'Object' == bases[i] )
		{
			continue;
		}
		// creating links to base class methods
		var p_base = bases[i].replace(/\./g, '_');
		eval('for(var m in '+bases[i]+'.prototype){newClass.prototype[m]='+bases[i]+'.prototype[m]; if ("__" !=m.substr(0,2)) {newClass.prototype["__'+p_base+'_"+m]='+bases[i]+'.prototype[m];}}');
	}
	// creating class metadata for reflection
	newClass.prototype.__class_name = className;
	newClass.prototype.__base_class_names = bases;
	eval('newClass.prototype.construct=function('+p.join(',')+'){'+c_code+'};')
	eval('newClass.prototype.destruct=function(){'+d_code+'};')
	eval(className+'=newClass');
}


// $new
// ====
// Creates new object.
// Usage: $new(ClassName, [arguments])
var $new = function()
{
	if ( !arguments[0] )
	{
		throw new FryException(31, 'Object instantiation error. Invalid class provided `?`.'.embed(arguments[0]));
	}
	var arg_list = [];
	for ( var i=1; i<arguments.length; i++ )
	{
		arg_list.push('arguments['+i+']');
	}
	try
	{
		eval('var obj = new arguments[0]('+arg_list.join(',')+');');
	}
	catch(e)
	{
		throw new FryException(32, 'Object instantiation error. Class: `?`, num arguments: `?`, error message: `?`.'.embed(arguments[0].prototype.__class_name, arg_list.length, e));
	}
	return obj;
}

// $delete
// =======
// Safely deletes object (destructors of each base class are called automatically).
// Usage: $delete(object)
var $delete = function(object)
{
	if ( 'object' != typeof object )
	{
		return;
	}
	try
	{
		if ( 'string' == typeof object.__base_class_names )
		{
			var bases = object.__base_class_names.split(',');
			for ( var i in bases )
			{
				if ( 'Object' != bases[i] )
				{
					$call(object, bases[i]+'.destruct()');				
				}
			}
		}
		if ( object.destruct )
		{
			object.destruct();
		}
		delete object;
	}
	catch(e)
	{
	}
}

// $call
// =====
// Calls a method/function of specific object, typically used from within method to call some base class method.
// Usage: $call(this, 'AClass.aMethod', [arguments])
var $call = function()
{
	caller = arguments[0];
	var arg_list = [];
	for ( var i=2; i<arguments.length; i++ )
	{
		arg_list.push('arguments['+i+']');
	}
	try
	{
		eval('var r = caller.__'+arguments[1].replace(/\./g, '_')+'.call(caller'+(0!=arg_list.length?',':'')+arg_list.join(',')+');');
	}
	catch (e)
	{
		throw new FryException(32, 'Function call error. Function `?`, num arguments: ?, error: `?`.'.embed(arguments[1], arguments.length-2, e));
	}
	return r;
}

// $runafter
// =========
// Runs embedded code after specified interval (in miliseconds, value 1000 means 1 second).
/* Usage:
	$runafter(100, function()
	{
		// your code
	})
*/
var $runafter = function(t, c)
{
	setTimeout(c, t);
}
// $runinterval
// ============
// Runs embedded code from step `from` to the `to` step, each step is delayed for specified interval.
/* Usage:
	$runinterval(1, 10, 100, function(step)
	{
		// your code that will repeat ten times
	})
*/
var $runinterval = function(from, to, interval, c)
{
	var i = from;
	var control = 
	{
		from:from,
		to:to,
		stopped:false,
		stop:function()
		{
			this.stopped = true;
		}
	}
	var t = self.setInterval(function()
	{
		if ( i > to && to>=from )
		{
			self.clearInterval(t);
		}
		else
		{
			c(i, control);
			if ( control.stopped )
			{
				self.clearInterval(t);
			}
		}
		i++;
	}, interval);
}
// $dotimes
// ========
// Repeats embedded code n times.
/* Usage:
	$dotimes(20, function(i)
	{
		// your code, i is the counter parameter
	})
*/
var $dotimes = function(n, c)
{
	for ( var i=0; i<n; i++ )
	{
		c(i);
	}
}
// $foreach
// ========
// Iterates through any kind of collection - it can be practically anything you might need, from arrays, serialized XML, DOM nodes, remote results etc.
/* Usage:
	$foreach ( node.g('table/tr'), function(tr, i, control)
	{
		if ( 5 > i )
		{
			control.skip();
			return;
		}
		tr.n(0==i%2 ? 'even' : 'odd');
		if ( 20 < i )
		{
			control.stop();
		}
	})
*/
var $foreach = function(o, c)
{
	if ( !o )
	{
		c = null;
		return;
	}
	if ( 'undefined' == typeof o.length && 'function' != typeof o.__length )
	{
		c = null;
		return;
	}
	var n = 'function' == typeof o.__length ? o.__length() : o.length;
	var control = 
	{
		stopped:false,
		stop:function()
		{
			this.stopped = true;
		},
		skipped:false,
		skip:function()
		{
			this.skipped = true;
		},
		removed:false,
		remove:function(stopAfterwards)
		{
			this.removed = true;
			this.stopped = true == stopAfterwards;
		}
	}
	// cannot just extend Array.prototype for `item()` method due bug in IE6 iteration mechanism. Some day (>2010 :) this might get fixed and will become obsolete
	for ( var i=0; i<n; i++ )
	{
		var item = null;
		if ( 'function' == typeof o.item )
		{
			item = o.item(i);
		}
		else if ( 'function' == typeof o.__item )
		{
			item = o.__item(i);
		}
		else
		{
			if ( 'undefined' == typeof o[i] )
			{
				continue;
			}
			item = o[i];
		}
		c(item, 'function' == typeof o.__key ? o.__key(i) : i, control);
		if ( control.removed )
		{
			control.removed = false;
			if ( 'undefined' != typeof o[i] )
			{
				delete o[i];
			}
			else
			{
				if ( 'function' == typeof o.removeItem )
				{
					o.removeItem(i);
				}
				else if ( 'function' == typeof o.__remove )
				{
					o.remove(i);
				}
			}
		}
		if ( control.stopped )
		{
			break;
		}
		if ( control.skipped )
		{
			control.skipped = false;
			continue;
		}
	}
	control = null;
	c = null;	
}
var $notset = function(value)
{
	return ( 'undefined' == typeof value || 'undefined' == value || null == value );
}
var $isset = function(value)
{
	return ( 'undefined' != typeof value && 'undefined' != value && null != value );
}
var $getdef = function(value, defaultValue)
{
	if ( 'undefined' == typeof value || 'undefined' == value || null == value )
	{
		return defaultValue;
	}
	return value;
}

var $combofill = function(n, c)
{
	var i = -1;
	n = $(n);
	while (-1<++i)
	{
		var v = c(i);
		if ( 'object' != typeof v )
		{
			break;
		}
		var option = n.a($$('option')).t(v[1]);
		option.$.value = v[0];
		if ( v[2] )
		{
			option.sa('selected', 'selected');
		}
	}
	return n;
}
var $comboget = function(n)
{
	var v = [];
	var options = $(n).$.options;
	for ( var i=0; i<options.length; i++ )
	{
		if ( '' != options[i].selected )
		{
			v[v.length] = options[i].value;
		}
	}
	if ( 1 == v.length )
	{
		return v[0];
	}
	if ( 0 == v.length && 0 < options.length )
	{
		return options[0].value;
	}
	return v;
}
var $comboset = function(n, v)
{
	var options = $(n).$.options;
	try
	{
		for ( var i=0; i<options.length; i++ )
		{
			if ( options[i].value == v )
			{
				options[i].selected = 'selected';
			}
		}
	}
	catch(e)
	{
	}
	return $(n);
}





/* Generic exception object */
function FryException(code, message)
{
	this.code = code;
	this.message = message;
}
FryException.prototype.toString = function()
{
	return 'Fry Exception: code[?] message[?]'.embed(this.code, this.message);
}

/* Remote call support (AJAX) */
fry.remote =
{
	support:
	{
		getRequestObject: function()
		{
			var obj = null;
			try
			{
				if ( $__tune.isIE )
				{
					$foreach ( ['MSXML2.XMLHTTP.5.0', 'MSXML2.XMLHTTP.4.0', 'MSXML2.XMLHTTP.3.0','MSXML2.XMLHTTP','Microsoft.XMLHTTP'], function(progid, index, control)
					{
						try
						{
							obj = new ActiveXObject(progid);
							control.stop();
						}
						catch(e){}
					});
				}
				else
				{
					obj = new XMLHttpRequest();
				}
			}
			catch(e){}
			return obj;
		}
	},
	/* Loosely based (especially status handling code) on YUI Library */
	post:function(callback, pars, httpMethod, url)
	{
		url = url || client.conf.fry.backendURL;
		if ( !url )
		{
			throw new FryException(1, 'Undefined backend URL specified in client.conf. Use client.conf.fry.backendURL=\'{YOUR_BACKEND_SCRIPT_URL}\'; to set it.');
		}
		var obj = fry.remote.support.getRequestObject();
		if ( !obj )
		{
			throw new FryException(2, 'Unable to acquire HTTP request object. Check to see if your browser is among supported browsers.');
		}
		if ( -1 != url.indexOf('?') )
		{
			url = url.embed(pars['a']);
			delete pars['a'];
		}
		obj.open(httpMethod||'POST', url, true);
		obj.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
		var postData = '';
		for ( var name in pars )
		{
			var value = pars[name];
			if ( 'object' == typeof value )
			{
				if ( value.join )
				{
					// array
					var n = value.length;
					for ( var i=0; i<n; i++ )
					{
						value[i] = (''+value[i]).replace(/\],\[/g, '`Â§~Â§[]Â§~Â§`');
					}
					value = '['+value.join('],[')+']';
					name += '(a)';
				}
				else
				{
					// object
					var values = '[';
					for ( var i in value )
					{
						values += i+'='+(''+value[i]).replace(/\],\[/g, '`Â§~Â§[]Â§~Â§`')+'],[';
					}
					value = '[' == values ? '' : values.substring(0, values.length-2);
					name += '(o)';
				}
			}
			postData += encodeURIComponent(name)+'='+encodeURIComponent(value)+'&';
		}
		obj.send(postData);
		var poll = window.setInterval
		(
			function()
			{
				if ( 4 == obj.readyState )
				{
					window.clearInterval(poll);
					callback(obj);
				}
			},
			150
		);
	},	
	result:function(s, callbackOk, callbackError)
	{
		var httpStatus;
		var responseObject;	
		try
		{
			httpStatus = s.status;
		}
		catch(e)
		{
			httpStatus = 13030;
		}
		if ( 200 == httpStatus )
		{
			// parsing response
			var r = null;
			var headers = s.getAllResponseHeaders();
			var contentType = (-1 != headers.indexOf('/xml') && s.responseXML) ? 'text/xml' : 'text/html';
			if ( 'text/xml' == contentType )
			{
				// text/xml
				try
				{
					r = $xmlserialize(s.responseText);
				}
				catch(e)
				{
					callbackError('Error while serializing remote-side response. Probably corrupted data. Error: `?`. Sent data `?`.'.embed(e.message, s.responseText));
				}
				try
				{
					callbackOk(r);					
				}
				catch(e)
				{
					throw new FryException(45, 'fry/remote: Error while executing callback after successful remote call. Error: `?`.'.embed(e.message));
				}
			}
			else
			{
				// text/html
				var code = s.responseText.substring(0,3);
				if ( '#S#' == code )
				{
					r = s.responseText.substr(3);
					callbackOk( r );
				}
				else
				{
					if ( '' == s.responseText )
					{
						callbackError('No data returned from remote side.');
					}
					else
					{
						callbackError('Invalid data returned from remote side: `?`.'.embed(s.responseText.substr('#E#'==code?3:0)));
					}					
				}
			}
		}
		else
		{
			switch (httpStatus)
			{
				// The following case labels are wininet.dll error codes that may be encountered.
				// Server timeout
				case 12002:
				// 12029 to 12031 correspond to dropped connections.
				case 12029:
				case 12030:
				case 12031:
				// Connection closed by server.
				case 12152:
				// See above comments for variable status.
				case 13030:
				default:
				{
					if ( callbackError )
					{
						callbackError('Connection ended up with status: '+httpStatus);
					}
				};break;
			}
		}
		delete s;
	},
	upload:
	{
		lastAdapter:null,
		// using SWFUpload component
		perform:function(adapter)
		{
			var url = client.conf.fry.backendURL;
			if ( !url )
			{
				throw new FryException(19, 'Undefined backend URL specified in client.conf. Use client.conf.fry.backendURL=\'{YOUR_BACKEND_SCRIPT_URL}\'; to set it.');
			}

			fry.remote.upload.lastAdapter = adapter;
			if ( null != $('SWFUpload') )
			{
				$('SWFUpload').rs();
			}
			$().a($$()).i('SWFUpload');
			mmSWFUpload.init
			({
				thirdPartyPath : client.conf.fry.path+'3rdparty',
				upload_backend : url+'?a='+adapter.onGetRemoteActionName(),
				target : 'SWFUpload',
				allowed_filesize : adapter.allowedFileSizeInKBytes,
				allowed_filetypes : adapter.allowedFileTypes,
				upload_start_callback : 'fry_remote_upload_onStart',
				upload_progress_callback : 'fry_remote_upload_onProgress',
				upload_complete_callback : 'fry_remote_upload_onComplete',
				upload_error_callback : 'fry_remote_upload_onError',
				upload_cancel_callback : 'fry_remote_upload_onCancel',
				upload_queue_complete_callback : 'fry_remote_upload_onQueueComplete'
			});
			$('SWFUpload').pos(true).x(1).y(1).w(1).h(1);
			mmSWFUpload.callSWF();
		}
	}
};

function fry_remote_upload_onStart(f)
{
	fry.remote.upload.lastAdapter.onStart(f);
}
function fry_remote_upload_onProgress(f, b)
{
	fry.remote.upload.lastAdapter.onProgress(f, b);
}
function fry_remote_upload_onComplete(f)
{
	fry.remote.upload.lastAdapter.onEnd(false, false, f);
}
function fry_remote_upload_onError(e)
{
	fry.remote.upload.lastAdapter.onEnd(false, true, e);
}
function fry_remote_upload_onCancel()
{
	fry.remote.upload.lastAdapter.onEnd(true);
}
function fry_remote_upload_onQueueComplete()
{
	fry.remote.upload.lastAdapter.onQueueEnd();
}



$class('fry.remote.upload.Adapter',
{
	construct:function(allowedFileSizeInKBytes, allowedFileTypes, additionalRemoteActionParams)
	{
		this.allowedFileSizeInKBytes = allowedFileSizeInKBytes || 2000;
		this.allowedFileTypes = allowedFileTypes || '*';
		this.additionalRemoteActionParams = additionalRemoteActionParams || '';
	}
});
fry.remote.upload.Adapter.prototype.onStart = function(fileObj)
{
}
fry.remote.upload.Adapter.prototype.onProgress = function(fileObj, bytesLoaded)
{
}
fry.remote.upload.Adapter.prototype.onEnd = function(wasCanceled, wasError, result)
{
}
fry.remote.upload.Adapter.prototype.onQueueEnd = function()
{
}
fry.remote.upload.Adapter.prototype.onGetRemoteActionName = function()
{
	return 'upload?'.embed(this.additionalRemoteActionParams ? ',?'.embed(this.additionalRemoteActionParams) : '');
}


/*  ---------------------------------------------------------------- 
	fry.cookie namespace
*/

fry.cookie =
{
	get:function(name)
	{
		//http://www.webreference.com/js/column8/functions.html
		var dc = document.cookie;
		var prefix = name + "=";
		var begin = dc.indexOf("; " + prefix);
		if (begin == -1) 
		{
			begin = dc.indexOf(prefix);
			if (begin != 0) return null;
		} 
		else
		{
			begin += 2;			
		}
		var end = document.cookie.indexOf(";", begin);
		if (end == -1)
		{
			end = dc.length;
		}
		return unescape( dc.substring(begin + prefix.length, end) );
	},
	remove:function(name, path, domain)
	{
		if (getCookie(name)) 
		{
			document.cookie = name + "=" + ((path) ? "; path=" + path : "") + ((domain) ? "; domain=" + domain : "") + "; expires=Thu, 01-Jan-70 00:00:01 GMT";
		}
	},
	set:function(name, value, expires, path, domain, secure)
	{
		var curCookie = name + "=" + escape(value) + ((expires) ? "; expires=" + expires.toGMTString() : "") + ((path) ? "; path=" + path : "") + ((domain) ? "; domain=" + domain : "") + ((secure) ? "; secure" : "");
		document.cookie = curCookie;
	}
}


var $post = fry.remote.post;
var $result = fry.remote.result;
var $rpost = function(params, callbackOk, callbackError, method, url)
{
	method = method || 'POST';
	url = url || client.conf.fry.backendURL;
	$post( function(s) { $result( s, 
		function(r) 
		{
			callbackOk(r);
		},
		function(e) 
		{
			// result Error
			callbackError(e);
		}
		) },
		params, method, url
	);
}
var $upload = function(adapter)
{
	fry.remote.upload.perform(adapter);
}



// Fry Garbage Collector mechanism
var __gc_trash_node = null;
var __gc_running = false;
var __gc_scheduled_timers = [];
var __gc_started_at = 0;

function __fry_gcnode_inner(inode)
{
	if ( null != inode.getAttribute('frydrag') )
	{
		$(inode).removeDrag();
	}
	if ( null != inode.getAttribute('frydnd') )
	{
		$(inode).removeDnD();
	}
	if ( null == inode.getAttribute('fryis') || null == inode.getAttribute('fryhe') )
	{
		inode = null;
		return;
	}
	inode.removeAttribute('fryhe');
	var lst = inode.attributes;
	var num = lst.length;
	for ( var i=0; i<num; i++ )
	{
		var attr_name = lst.item(i).name;
		if ( attr_name && 'fryse' == attr_name.substr(0,5) )
		{
			var type = attr_name.substr(6);
			var listeners = lst.item(i).value.split(',');
			for ( var ii=0; ii<listeners.length; ii++ )
			{
				$__tune.event.removeListener(inode, type, self[listeners[ii]]);
				inode['on'+type] = null;
				self[listeners[ii]] = null;
			}
		}
		attr = null;
	}
	lst = null;
	for ( var i in inode )
	{
		if ( 'on' == i.substr(0,2) && 'function' == typeof inode[i] )
		{
			inode[i] = null;
		}
	}
	inode = null;
}

function __fry_precaunode(node)
{
	var lst = node.getElementsByTagName('*');
	for ( var i=0; i<lst.length; i++ )
	{
		if ( '' != lst.item(i).id )
		{
			lst.item(i).id = '';
		}
	}
	lst = null;
	node.id = '';
	return node;
}

function __fry_gcnode(node, skipSelf)
{
	if ( null == __gc_trash_node )
	{
		// GC not available at the moment
		if ( skipSelf )
		{
			node.innerHTML = '';
		}
		else
		{
			if ( node.parentNode )
			{
				node.parentNode.removeChild(node);
			}
		}
		return;
	}
	if ( skipSelf )
	{
		try
		{
			while ( null != node.firstChild )
			{
				__gc_trash_node.appendChild(__fry_precaunode(node.firstChild));
			}
		}
		catch(e){}
	}
	else
	{
		try
		{
			__gc_trash_node.appendChild(__fry_precaunode(node));
		}
		catch(e){}
	}
//	console.log('GC scheduled.');
	__gc_scheduled_timers[__gc_scheduled_timers.length] = setTimeout('__fry_gc_recycle()', 10000+Math.floor(10000*Math.random()));
}

function __fry_gc_time()
{
	var d = new Date();
	return 60000*d.getMinutes()+1000*d.getSeconds()+d.getMilliseconds();
}

function __fry_gc_recycle()
{
	var n = __gc_scheduled_timers.length;
	for ( var i=0; i<n; i++ )
	{
		clearTimeout(__gc_scheduled_timers[i]);
	}
	__gc_scheduled_timers = [];
	if ( __gc_running )
	{
//		console.log('GC already running.');
		return;
	}
	__gc_running = true;
	__gc_started_at = __fry_gc_time();
//	console.log('GC running for %s nodes. Started at %s', __gc_trash_node.childNodes.length, __gc_started_at);
	while ( null != __gc_trash_node.firstChild )
	{
		var node = __gc_trash_node.firstChild;
		if ( 1 == node.nodeType )
		{
			var lst = node.getElementsByTagName('*');
			var num = lst.length;
			if ( __gc_started_at < __fry_gc_time() - 2000 )
			{
//				console.log('GC did not finish on time. Stopped at %s after %s msecs of running. Number of remaining nodes: %s.', __fry_gc_time(), __fry_gc_time()-__gc_started_at, __gc_trash_node.childNodes.length);
				__gc_running = false;
				__gc_scheduled_timers[__gc_scheduled_timers.length] = setTimeout('__fry_gc_recycle()', 7000+Math.floor(7000*Math.random()));
				return;
			}
			for ( var ii=0; ii<num; ii++ )
			{
				__fry_gcnode_inner(lst.item(ii));
			}
			lst = null;
		}
		__gc_trash_node.removeChild(node);
		node = null;
	}
//	console.log('GC finished');
	__gc_running = false;
}


$__tune.event.addListener(self, 'load', function(evt)
{
	__gc_trash_node = document.getElementsByTagName('body').item(0).appendChild(document.createElement('div'));
	__gc_trash_node.style.display = 'none';		
});
$__tune.event.addListener(self, 'unload', function(evt)
{
	__gc_trash_node = $().$;
	__fry_gc_recycle();
});
/*
 * Advanced keyboard handling
 */

/*--------*/

fry.keyboard = 
{
	initialized:false,
	last_down_evt: null,
	ignore_further_events: false,
	stopped:true,
	paste: {was:false, none:function(){}},
	down: {none:function(){}},
	press: {none:function(){}},
	shared:{},
	buffer: [],
	listener: null,
	clipboard:{node:null, ie:{node:null}, pastedContent:'', copiedContent:'', content:''},
	CONTROL_CODE:1,
	ALT_KEY:2,
	CTRL_KEY: 4,
	SHIFT_KEY:8,
	META_KEY:16,
	COPY: 128,
	CUT: 256,
	PASTE: 512,
	SIG_CLIPBOARD_GET:1024
}

fry.keyboard.initialize = function()
{
	if (fry.keyboard.initialized)
	{
		fry.keyboard.start();
		return;
	}
	var react_as = 'none';
	
	if ($__tune.isGecko)
	{
		react_as = 'ff_' + ($__tune.isMac ? 'mac' : 'win');
	}
	else if ($__tune.isSafari)
	{
		react_as = 'webkit';
	}
	else if ($__tune.isIE)
	{
		react_as = 'ie';
	}
	else if ($__tune.isOpera)
	{
		react_as = 'opera';
	}
	// following scroll listeners will accomplish movement of helper textareas if page scrolls. Due focusing, page would scroll up when pressing paste combination.
	document.onscroll = function(evt)
	{
		if (fry.keyboard.clipboard.node)
		{
			fry.keyboard.clipboard.node.style.top = ($__tune.isSafari? document.body.scrollTop : document.documentElement.scrollTop) + 'px';
		}
	}
	if ($__tune.isIE)
	{
		document.body.onscroll = function(evt)
		{
			if (fry.keyboard.clipboard.node)
			{
				fry.keyboard.clipboard.node.style.top = document.documentElement.scrollTop + 'px';
			}
			if (fry.keyboard.clipboard.ie.node)
			{
				fry.keyboard.clipboard.ie.node.style.top = document.documentElement.scrollTop + 'px';
			}
		}
	}
	var code = "document.onkeydown = function(evt) {\n";
	code += "if (fry.keyboard.stopped) { return; }\n";
	code += "fry.keyboard.ignore_further_events = false;\n";
	code += "var result = null;\n";
	code += $__tune.isIE ? 'evt = event;\n' : '';
	code += (''+fry.keyboard.paste[react_as]).replace(/function[ ]+\(evt\)/, '').replace(/return /g, 'result=').replace(/^[^{]*{/, '').replace(/\}\s*$/, '').replace('fry.keyboard.shared.copy(evt);', (''+fry.keyboard.shared.copy).replace(/function[ ]+\(evt\)/, '').replace(/return /g, 'result=').replace(/^[^{]*{/, '').replace(/\}\s*$/, ''));
	code += "if (fry.keyboard.ignore_further_events) {	return;	}\n";
	code += "if (result) { fry.keyboard.prepareClipboard();	fry.keyboard.paste.was = true; fry.keyboard.clipboard.node.value = ''; fry.keyboard.clipboard.node.focus();	return true; }\n";
	code += "else { ";
	code += $__tune.isIE ? "if (86 == event.keyCode && event.ctrlKey){ fry.keyboard.clipboard.ie.node.value = ''; fry.keyboard.clipboard.ie.node.focus(); }\n" : "";
	code += "}\n";
	code += (''+fry.keyboard.down[react_as]).replace(/function[ ]+\(evt\)/, '').replace(/^[^{]*{/, '').replace(/\}\s*$/, '') + "\n}"
	code = code.replace(/fry\.keyboard\.([A-Z_]+)/g, function() {return fry.keyboard[arguments[1]];});
    // alert(code);
	eval(code);
	
	code = "document.onkeypress = function(evt)	{\n";
	code += "if (fry.keyboard.stopped || fry.keyboard.ignore_further_events) { return; }\n";
	code += "if (fry.keyboard.paste.was) {\n";
	if (!$__tune.isIE)
	{
	    code += "setTimeout(function() {\n";
		if ($__tune.isSafari)
		{
		    // bug in WebKit - append \n if inserted value ends with \n causing double \n as resulting read value
		    code += "var v = fry.keyboard.clipboard.node.value; if ('\\n\\n' == v.substr(v.length-2,2)) {v = v.substr(0, v.length-1);}fry.keyboard.clipboard.node.value = v;\n";
		}
		code += "fry.keyboard.pushKey(fry.keyboard.clipboard.node.value, fry.keyboard.CONTROL_CODE | fry.keyboard.PASTE); fry.keyboard.clipboard.node.blur(); fry.keyboard.paste.was = false;	}, 20);\n";
	}
	code += "return; }\n";
	if ($__tune.isIE)
	{
    	code += "evt = event;\n"
	}
	code += (''+fry.keyboard.press[react_as]).replace(/function[ ]+\(evt\)/, '').replace(/^[^{]*{/, '').replace(/\}\s*$/, '') + "\n}"
	code = code.replace(/fry\.keyboard\.([A-Z_]+)/g, function() {return fry.keyboard[arguments[1]];});
    // alert(code);
	eval(code);
	
	document.onkeydown2 = function(evt)
	{
		if (fry.keyboard.stopped)
		{
			return;
		}
		fry.keyboard.ignore_further_events = false;
		var result = fry.keyboard.paste[react_as](evt || event);
		if (fry.keyboard.ignore_further_events)
		{
			return;
		}
		if (result)
		{
			fry.keyboard.prepareClipboard();
			fry.keyboard.paste.was = true;
			fry.keyboard.clipboard.node.value = '';
			fry.keyboard.clipboard.node.focus();
			return true;
		}
		else
		{
			if ($__tune.isIE)
			{
				if (86 == event.keyCode && event.ctrlKey)
				{
					fry.keyboard.clipboard.ie.node.value = '';
					fry.keyboard.clipboard.ie.node.focus();
				}
			}			
		}
		return fry.keyboard.down[react_as](evt || event);
	}
	document.onkeypress2 = function(evt)
	{
		if (fry.keyboard.stopped || fry.keyboard.ignore_further_events)
		{
			return;
		}
		if (fry.keyboard.paste.was)
		{
			if (!$__tune.isIE)
			{
				setTimeout(function()
				{
					if ($__tune.isSafari)
					{
						// bug in WebKit - append \n if inserted value ends with \n causing double \n as resulting read value
						var v = fry.keyboard.clipboard.node.value;
						if ('\n\n' == v.substr(v.length-2,2))
						{
							v = v.substr(0, v.length-1);
						}
						fry.keyboard.clipboard.node.value = v;
					}
					fry.keyboard.pushKey(fry.keyboard.clipboard.node.value, fry.keyboard.CONTROL_CODE | fry.keyboard.PASTE);
					fry.keyboard.clipboard.node.blur();
					fry.keyboard.paste.was = false;
				}, 20);
			}
			return;
		}
		return fry.keyboard.press[react_as](evt || event);
	}
	if ($__tune.isIE)
	{
		fry.keyboard.prepareClipboard();
		fry.keyboard.clipboard.ie = {node:$().a($$('textarea')).pos(true).x(-2000).y(document.documentElement.scrollTop).w(20).h(20).e('paste', function(evt)
		{
			if (fry.keyboard.stopped)
			{
				return;
			}
			setTimeout(function(){
				fry.keyboard.paste.was = false;
				fry.keyboard.pushKey(fry.keyboard.clipboard.ie.node.value, fry.keyboard.CONTROL_CODE | fry.keyboard.PASTE);
			}, 10);
		}).$};
	}
	if ($__tune.isGecko && $__tune.isMac)
	{
		document.onkeyup = function(evt)
		{
			if (evt.metaKey && !evt.ctrlKey && !evt.altKey && !evt.shiftKey && 65 <= evt.keyCode && 128 >= evt.keyCode)
			{
				fry.keyboard.pushKey(evt.keyCode + 32, fry.keyboard.META_KEY);
				evt.preventDefault();
				return true;
			}
		}
	}
	fry.keyboard.initialized = true;
	fry.keyboard.start();
}

fry.keyboard.start = function()
{
	fry.keyboard.stopped = false;
}

fry.keyboard.stop = function()
{
	fry.keyboard.stopped = true;
}

fry.keyboard.disableTextfieldsEditation = function()
{
	fry.keyboard.allowTextfieldsEditation(true);
}

fry.keyboard.allowTextfieldsEditation = function(disable)
{
	var lst = document.getElementsByTagName('input');
	var n = lst.length;
	for (var i=0; i<n; i++)
	{
		var item = lst.item(i);
		if ('text' == item.type || 'password' == item.type)
		{
			if (disable)
			{
				item.onfocus = null;
				item.onblur = null;
				item.onkeydown = null;
				item.onkeypress = null;
				item.onkeyup = null;
				continue;
			}
			$(item).e('keydown', function(evt){evt.stopPropagation();}).e('keypress', function(evt){evt.stopPropagation();}).e('keyup', function(evt){evt.stopPropagation();});
			item.onfocus = function(evt)
			{
				fry.keyboard.stop();
			}
			item.onblur = function(evt)
			{
				fry.keyboard.start();
			}
		}
	}
	lst = document.getElementsByTagName('textarea');
	var n = lst.length;
	for (var i=0; i<n; i++)
	{
		var item = lst.item(i);
		if (disable)
		{
			item.onfocus = null;
			item.onblur = null;
			item.onkeydown = null;
			item.onkeypress = null;
			item.onkeyup = null;
			continue;
		}
		$(item).e('keydown', function(evt){evt.stopPropagation();}).e('keypress', function(evt){evt.stopPropagation();});
		item.onfocus = function(evt)
		{
			fry.keyboard.stop();
		}
		item.onblur = function(evt)
		{
			fry.keyboard.start();
		}
	}
}

fry.keyboard.prepareClipboard = function()
{
	if (fry.keyboard.clipboard.node)
	{
		return;
	}
	fry.keyboard.clipboard.node = $().a($$('textarea')).w(20).h(20).pos(true).x(-2000).y($__tune.isSafari? document.body.scrollTop : document.documentElement.scrollTop).$;
}

fry.keyboard.shared.copy = function(evt)
{
	fry.keyboard.prepareClipboard();
	// acquiring clipboard content to be copied into system clipboard
	fry.keyboard.clipboard.copiedContent = '';
	if (fry.keyboard.listener)
	{
		var content = fry.keyboard.listener(0, fry.keyboard.CONTROL_CODE | fry.keyboard.SIG_CLIPBOARD_GET);
		if ('string' == typeof content)
		{
			fry.keyboard.clipboard.copiedContent = content;
		}
	}
	fry.keyboard.clipboard.node.value = fry.keyboard.clipboard.copiedContent;
	fry.keyboard.clipboard.node.select();
	fry.keyboard.clipboard.node.focus();
	setTimeout('fry.keyboard.clipboard.node.blur()', 200);
	fry.keyboard.clipboard.content = fry.keyboard.clipboard.copiedContent;
	fry.keyboard.ignore_further_events = true;
	// sending control code
	fry.keyboard.pushKey(0, fry.keyboard.CONTROL_CODE | (88 == evt.keyCode ? fry.keyboard.CUT : fry.keyboard.COPY));
	return false;
}

fry.keyboard.paste.ff_win = function(evt)
{
	return 86 == evt.keyCode && 0 == evt.charCode && 86 == evt.which && evt.ctrlKey;
}

fry.keyboard.down.ff_win = function(evt)
{
	fry.keyboard.last_down_evt = evt;
	return true;
}

fry.keyboard.press.ff_win = function(evt)
{
	if (null != fry.keyboard.last_down_evt)
	{
		var mask = (evt.altKey ? 2 : 0) + (evt.ctrlKey ? 4 : 0) + (evt.shiftKey ? 8 : 0) + (evt.metaKey ? 16 : 0);
		var code = !evt.keyCode ? evt.charCode : evt.keyCode;
		if (evt.keyCode == evt.charCode && evt.keyCode == fry.keyboard.last_down_evt.charCode)
		{
			code = fry.keyboard.last_down_evt.keyCode;
		}
		if (evt.keyCode == fry.keyboard.last_down_evt.keyCode && (0 == evt.which || 32 > evt.keyCode))
		{
			// control code
			mask++;
		}
		if (!fry.keyboard.pushKey(code, mask))
		{
			return true;
		}
	}
	evt.preventDefault();
	evt.stopPropagation();
	return false;
}

fry.keyboard.paste.ff_mac = function(evt)
{
	fry.keyboard.last_down_evt = null;
	// catching Command+C, Command+X, it's a FF.mac hack
	if (evt.metaKey && ((67 == evt.keyCode && 0 == evt.charCode && 67 == evt.which) || (88 == evt.keyCode && 0 == evt.charCode && 88 == evt.which)))
	{
		return fry.keyboard.shared.copy(evt);
	}
	else
	{
    	return 86 == evt.keyCode && 0 == evt.charCode && 86 == evt.which && evt.metaKey;
	}
}

fry.keyboard.down.ff_mac = function(evt)
{
	return false;
}

fry.keyboard.press.ff_mac = function(evt)
{
	if (null != fry.keyboard.last_down_evt)
	{
		return;
	}
	var mask = (evt.altKey ? 2 : 0) + (evt.ctrlKey ? 4 : 0) + (evt.shiftKey ? 8 : 0) + (evt.metaKey ? 16 : 0);
	if (!evt.charCode || (evt.charCode == evt.keyCode))
	{
		// control code
		fry.keyboard.pushKey(evt.keyCode, 1 + mask);
	}
	else
	{
		if (!fry.keyboard.pushKey(evt.charCode, mask))
		{
			return true;
		}
	}
	evt.preventDefault();
	evt.stopPropagation();
	return false;
}

fry.keyboard.paste.webkit = function(evt)
{
	if ($__tune.isMac)
	{
		return (86 == evt.keyCode && (0 == evt.charCode || 118 == evt.charCode) && evt.metaKey);
	}
	else
	{
		return (86 == evt.keyCode && (0 == evt.charCode || 118 == evt.charCode) && evt.ctrlKey);
	}
}

fry.keyboard.down.webkit = function(evt)
{
	if (0 != evt.keyCode && (48 > evt.keyCode || (111 < evt.keyCode && 128 > evt.keyCode) || 60000 < evt.charCode))
	{
		var mask = (evt.altKey ? 2 : 0) + (evt.ctrlKey ? 4 : 0) + (evt.shiftKey ? 8 : 0) + (evt.metaKey ? 16 : 0);
		if (!evt.charCode || 111 < evt.keyCode || 32 > evt.charCode || 60000 < evt.charCode)
		{
			// control code
			fry.keyboard.pushKey(evt.keyCode, 1 + mask);
		}
		else
		{
			if (!fry.keyboard.pushKey(evt.charCode, mask))
			{
				return true;
			}
		}
		evt.preventDefault();
		evt.stopPropagation();
		fry.keyboard.last_down_evt = null;
		return false;
	}
	fry.keyboard.last_down_evt = evt;
	return true;
}

fry.keyboard.press.webkit = function(evt)
{
	if (null != fry.keyboard.last_down_evt)
	{
		var mask = (evt.altKey ? 2 : 0) + (evt.ctrlKey ? 4 : 0) + (evt.shiftKey ? 8 : 0) + (evt.metaKey ? 16 : 0);
		var code = !evt.keyCode ? evt.charCode : evt.keyCode;
		if (evt.keyCode == evt.charCode && evt.keyCode == fry.keyboard.last_down_evt.charCode && evt.keyCode > 60000)
		{
			code = fry.keyboard.last_down_evt.keyCode;
		}
		if (evt.keyCode == fry.keyboard.last_down_evt.keyCode && 48 > evt.keyCode)
		{
			// control code
			mask++;
		}
		else
		{
			var r_mask = fry.keyboard.SHIFT_KEY + fry.keyboard.META_KEY;
			if (r_mask == (mask & r_mask) && 97 <= code && 122 >= code)
			{
				code -= 32;
			}
		}
		if (!fry.keyboard.pushKey(code, mask))
		{
			return true;
		}
	}
	evt.preventDefault();
	evt.stopPropagation();
	return false;			
}

fry.keyboard.paste.ie = function(evt)
{
	if (evt.ctrlKey && (67 == evt.keyCode || 88 == evt.keyCode))
	{
		// ctrl+c, ctrl+x
		return fry.keyboard.shared.copy(evt);
	}
	else
	{
    	return false;
	}
}

fry.keyboard.down.ie = function(evt)
{
	fry.keyboard.last_down_evt = evt;
	if (48 > evt.keyCode || (111 < evt.keyCode && 128 > evt.keyCode))
	{
		// control code for IE
		var mask = 1 + (evt.altKey ? 2 : 0) + (evt.ctrlKey ? 4 : 0) + (evt.shiftKey ? 8 : 0) + (evt.metaKey ? 16 : 0);
		return !fry.keyboard.pushKey(evt.keyCode, mask)
	}
	else
	{
		var code = evt.keyCode;
		// disabling some other keys (A, F, N, R, S, T)
		if (82 == evt.keyCode || 65 == evt.keyCode || 83 == evt.keyCode || 70 == evt.keyCode || 78 == evt.keyCode || 84 == evt.keyCode)
		{
			if (!evt.shiftKey)
			{
				code += 32;
			}
			var mask = (evt.altKey ? 2 : 0) + (evt.ctrlKey ? 4 : 0) + (evt.shiftKey ? 8 : 0) + (evt.metaKey ? 16 : 0);
			return !fry.keyboard.pushKey(code, mask);
		}
	}
	return true;			
}

fry.keyboard.press.ie = function(evt)
{
	if (null != fry.keyboard.last_down_evt)
	{
		var mask = (evt.altKey ? 2 : 0) + (evt.ctrlKey ? 4 : 0) + (evt.shiftKey ? 8 : 0) + (evt.metaKey ? 16 : 0);
		return !fry.keyboard.pushKey(evt.keyCode, mask);
	}
	return false;			
}


fry.keyboard.paste.opera = function(evt)
{
	return 86 == evt.keyCode && 86 == evt.which && evt.ctrlKey;
}

fry.keyboard.down.opera = function(evt)
{
	fry.keyboard.last_down_evt = evt;
	return false;
}

fry.keyboard.press.opera = function(evt)
{
	var e = fry.keyboard.last_down_evt;
	var mask = (evt.altKey ? 2 : 0) + (evt.ctrlKey ? 4 : 0) + (evt.shiftKey ? 8 : 0) + (evt.metaKey ? 16 : 0);
	var prev_mask = (e.altKey ? 2 : 0) + (e.ctrlKey ? 4 : 0) + (e.shiftKey ? 8 : 0) + (e.metaKey ? 16 : 0);
	if ((evt.keyCode == fry.keyboard.last_down_evt.keyCode || 0 == e.keyCode) && (0 == evt.which || 48 > e.keyCode || 111 < e.keyCode))
	{
		mask++;
	}
	if (!fry.keyboard.pushKey(evt.keyCode, mask))
	{
		return true;
	}
	evt.preventDefault();
	evt.stopPropagation();
	return false;
}

fry.keyboard.addListener = function(listener)
{
	fry.keyboard.listener = listener;
}

fry.keyboard.removeListener = function(listener)
{
    fry.keyboard.listener = null;
}


fry.keyboard.pushKey = function(code, mask)
{
	if (32 == code)
	{
		mask = mask & 65534;
	}
	var was_clipboard_copy = false;
	var was_clipboard_cut = false;
	if ($__tune.isMac)
	{
		was_clipboard_copy = (99 == code) && (fry.keyboard.META_KEY == (mask & fry.keyboard.META_KEY));
		was_clipboard_cut = (120 == code) && (fry.keyboard.META_KEY == (mask & fry.keyboard.META_KEY));
	}
	else
	{
		was_clipboard_copy = (1 == code || 99 == code) && (fry.keyboard.CTRL_KEY == (mask & fry.keyboard.CTRL_KEY));
		was_clipboard_cut = (24 == code || 120 == code) && (fry.keyboard.CTRL_KEY == (mask & fry.keyboard.CTRL_KEY));
	}
	if (was_clipboard_copy || was_clipboard_cut)
	{
		fry.keyboard.prepareClipboard();
		fry.keyboard.clipboard.copiedContent = '';
		var was_custom_content = false;
		if (fry.keyboard.listener)
		{
			var content = fry.keyboard.listener(0, fry.keyboard.CONTROL_CODE | fry.keyboard.SIG_CLIPBOARD_GET);
			if ('string' == typeof content)
			{
				was_custom_content = true;
				fry.keyboard.clipboard.copiedContent = content;
			}
		}
		if (was_custom_content)
		{
			fry.keyboard.clipboard.node.value = fry.keyboard.clipboard.copiedContent;
			fry.keyboard.clipboard.node.select();
			fry.keyboard.clipboard.node.focus();
		}
		fry.keyboard.pushKey(0, fry.keyboard.CONTROL_CODE | (was_clipboard_cut ? fry.keyboard.CUT : fry.keyboard.COPY));
		fry.keyboard.clipboard.content = fry.keyboard.clipboard.copiedContent;
		// returning false will enforce propagation
		return !was_custom_content;
	}
	if (fry.keyboard.PASTE == (mask & fry.keyboard.PASTE))
	{
		fry.keyboard.clipboard.pastedContent = code;
		fry.keyboard.clipboard.content = fry.keyboard.clipboard.pastedContent;
		code = 0;
	}
	// filtering out solo-keys Ctrl, Shift, Alt that are triggered by some browsers.
	if ((17 == code && 5 == (mask & 5)) || (16 == code && 9 == (mask & 9)) || (18 == code && 3 == (mask & 3)))
	{
		return true;
	}
	// filtering out Command+V on FF.mac
	if (118 == code && 16 == mask)
	{
		return true;
	}
	if (fry.keyboard.listener)
	{
        // console.info(code);
	    if (13 != code && 0 != (mask & (fry.keyboard.CONTROL_CODE + fry.keyboard.META_KEY + fry.keyboard.CTRL_KEY)))
	    {
	        // some keystroke occured that we really want to know about the listener result, we have to call it immediatelly
			return fry.keyboard.listener(code, mask);
	    }
	    else
	    {
	        // let's ease the pain of the browser
            setTimeout('fry.keyboard.listener('+code+','+mask+')', 10);
	    }
	}
	else
	{
		fry.keyboard.buffer.unshift([code, mask]);
	}
	return true;
}

fry.keyboard.popKey = function()
{
	return fry.keyboard.buffer.pop();
}

fry.keyboard.getClipboardContent = function()
{
	return fry.keyboard.clipboard.content;
}


/*--------*/
var client = {conf:{fry:{backendURL:''}}};
var eamy = 
{
	snippets:[],
	instances:[]
};

/*
 * ac.Chap - Text Editing Component - Core
 */

if ( 'undefined' == typeof ac )
{
	var ac = {chap:{}};
}

ac.chap = 
{
	state:
	{
		active:null
	},

	TOKEN_MULTIROW_COMMENT:0,
	TOKEN_SINGLEROW_COMMENT:1,
	TOKEN_SINGLE_QUOTED:2,
	TOKEN_DOUBLE_QUOTED:3,
	TOKEN_NEWROW:4,
	TOKEN_WHITESPACE:5,
	
	ROWSTATE_NONE:0,
	ROWSTATE_FOLD_START:1,
	ROWSTATE_FOLD_STOP:2,
	ROWSTATE_FOLD_EXPAND:4,
	ROWSTATE_FOLD_COLLAPSED:8,
	ROWSTATE_SELECTION:16,
	ROWSTATE_BOOKMARK:32,
	
	CHUNK_KEYWORD:4,
	CHUNK_NUMBER:5,
	CHUNK_OPERATOR:6,
	CHUNK_PARENTHESIS:7,
	CHUNK_KEYWORD_CUSTOM:8,
	CHUNK_FUNCTION_NAME:9,
	CHUNK_LIBRARY:10,
	CHUNK_LIBRARY_CUSTOM:11,
	
	ACTION_CARET:1,
	ACTION_SELECTION:2,
	ACTION_INSERT:3,
	ACTION_UPDATE:4,
	ACTION_DELETE:5,
	ACTION_CLIPBOARD:6,
	ACTION_UNDO:7,
	ACTION_REDO:8,
	ACTION_CUSTOM:9,
	
	ACTION_RES_REDRAWCARET:1,
	ACTION_RES_REDRAWTEXT:2,
	ACTION_RES_SELECTIONCHANGED:4,
	ACTION_RES_SCROLLTOCARET:8,
	
	CKEY_NONE:0,
	CKEY_ALT:2,
	CKEY_CTRL:4,
	CKEY_SHIFT:8,
	CKEY_META:16,
	
	TRANSLOG_TYPE_INSERT:1,
	TRANSLOG_TYPE_REMOVE:2,
	
	ACTION_LISTENER_BEFORE:1,
	ACTION_LISTENER_AFTER:2,
	ACTION_LISTENER_BOTH:3
	
}



ac.chap.activeComponent = null;
ac.chap.instanceId = 1;

ac.chap.getActiveComponent = function()
{
	return ac.chap.activeComponent;
}

ac.chap.setActiveComponent = function(component)
{
	fry.keyboard.initialize();
	if (null != ac.chap.activeComponent)
	{
		ac.chap.activeComponent.blur();
	}
	ac.chap.activeComponent = component;
	if (null != component)
	{
		if (ac.widget)
		{
			ac.widget.focus(component);
		}
		ac.chap.activeComponent.focus();
	}
	else
	{
		if (!ac.widget)
		{
			fry.keyboard.stop();
		}
	}
}

ac.chap.route = function(type, windowId, viewIndex, pars)
{
	if ( null == ac.chap.activeComponent )
	{
		return;
	}
	if ( 'undefined' == typeof ac.chap.activeComponent.views[viewIndex] )
	{
		return;
	}
	switch ( type )
	{
		case 'expand-folding':
		{
			ac.chap.activeComponent.expandFolding(pars);
		}
	}
}

ac.chap.caretThread = setInterval(function()
{
	if (null != ac.chap.activeComponent)
	{
		ac.chap.activeComponent.showCaret(true, true);
	}
}, 600);

$(document.documentElement).e($__tune.isSafari2?'mousedown':'click', function(evt)
{
	var elem = evt.$.$;
	while ( null != elem && document.documentElement != elem )
	{
		if ( 'true' == elem.getAttribute('chap-view') )
		{
			evt.stop();
			return;
		}
		elem = elem.parentNode;
	}
	ac.chap.setActiveComponent(null);
});


ac.chap.keyboardListener = function(code, mask)
{
	if (null == ac.chap.activeComponent)
	{
		return;
	}
	return ac.chap.activeComponent.standaloneKeyboardListener(code, mask);
}
if ('undefined' == typeof ac['widget'])
{
	// chap is not a part of Fry MVC, must handle keyboardListener itself
	fry.keyboard.addListener(ac.chap.keyboardListener);
}

$class('ac.chap.Window',
{
	construct:function(options, userId)
	{
		this.instanceId = ac.chap.instanceId++;
		this.ident = 'ac-chap-' + this.instanceId;
		this.userId = userId | 0;
		this.caret = null;
		this.options = null;
		this.state = null;
		
		this.views = [];
		this.activeView = null;
		this.viewLayoutNodes = [];

		this.char_map = [];
		this.row_id_map = [];
		this.syntax_map = [];
		this.style_map = [];

		this.row_id_sequence = 1;
		
		this.language = null;
		this.keymap = null;
		this.snippets = [];
		this.commands = [];
		
		this.selection = null;
		this.transaction_log = [];
		this.redo_log = [];
		
		this.setOptions(options||{});
		this.setState();
	},
	destruct:function()
	{
	    $delete(this.state);
	    $delete(this.options);
	    $delete(this.char_map);
	    $delete(this.row_id_map);
	    $delete(this.syntax_map);
	    $delete(this.style_map);
		this.hide();
	    $delete(this.activeView);
	}
});

ac.chap.Window.prototype.focus = function()
{
	this.showCaret();
}

ac.chap.Window.prototype.blur = function()
{
	this.hideCaret();
}

// compatibility layer with AC Fry Widget library
ac.chap.Window.prototype.onFocus = function()
{
	ac.chap.setActiveComponent(this);
	this.focus();
}

ac.chap.Window.prototype.onBlur = function()
{
	ac.chap.setActiveComponent(null);
	this.blur();
}

ac.chap.Window.prototype.onResize = function(width, height)
{
}

ac.chap.Window.prototype.onSystemClipboardCopy = function()
{
	return this.getSelection();
}

ac.chap.Window.prototype.onSystemClipboardCut = function()
{
	this.runAction(ac.chap.ACTION_CLIPBOARD, {cut:true});
	return this.processActionResult(true, true);
}

ac.chap.Window.prototype.onSystemClipboardPaste = function(content)
{
	this.runAction(ac.chap.ACTION_CLIPBOARD, {paste:true, content:content});
	return this.processActionResult(true, true);
}

ac.chap.Window.prototype.hasKeyboardListenerActive = function()
{
	return true;
}
ac.chap.Window.prototype.onCut = function(selection, callbackOk)
{
}

ac.chap.Window.prototype.onPaste = function(selection, wasCut)
{
}

ac.chap.Window.prototype.setOptions = function(options)
{
	this.options = 
	{
		initialCaretPosition:[0,0],
		tokenizerLazyLaunch:900,
		syntaxHighlightingEnabled:true,
		remoteBackendURL:'',
		font:{
			size:11,
			family: $__tune.isMac ? "Consolas, 'Bitstream Vera Sans mono', 'Courier', 'Monaco', monospaced" : "Consolas, 'Courier New', 'Courier', monospaced",
			allowedSizes: [8, 9, 10, 11, 12, 13, 14, 17, 21, 24, 27, 30, 34, 38, 42]
		}
	};
	if ( $isset(options.initial_caret_position) )
	{
		this.options.initialCaretPosition = [options.initial_caret_position[0], options.initial_caret_position[1]];
	}
	if ( $isset(options.language) )
	{
		this.language = $new(options.language);
	}
	else
	{
		this.language = $new(ac.chap.Language);
	}
	if ( $isset(options.keymap) )
	{
		this.keymap = $new(options.keymap);
	}
	else
	{
		this.keymap = $new(ac.chap.KeyMap);
	}
	if ( $isset(options.syntaxHighlightingEnabled) )
	{
		this.options.syntaxHighlightingEnabled = options.syntaxHighlightingEnabled;
	}
	if ( $isset(options.remoteBackendURL) )
	{
		this.options.remoteBackendURL = options.remoteBackendURL;
	}
	else
	{
	    if ( client && client.conf && client.conf.fry )
	    {
	        this.options.remoteBackendURL = client.conf.fry.backendURL;
	    }
	}
	if ($isset(options.font))
	{
		if ($isset(options.font['size']))
		{
			this.options.font.size = options.font.size;			
		}
		if ($isset(options.font['family']))
		{
			this.options.font.family = options.font.family;
		}
	}
}

ac.chap.Window.prototype.setState = function()
{
	this.state =
	{
		lastKeyTimePressed:0,
		caretPhase:1,
		lastKeyCode:0,
		lastControlKey:0,
		lastCaretPosition:[],
		tokenizerTimer:null,
		scheduledTokenizerTime:0,
		transactionLogStopped:false,
		actionListeners:[],
		actionListenersStopped:false,
		caretListener:null,
		commandListener:null,
		transactionListener:[null,800],
		passThroughKeysListener:null
	}
	this.caret = 
	{
		position:[this.options.initialCaretPosition[0], this.options.initialCaretPosition[1]],
		mode:1 // 1 normal, 2 overwrite
	}
}

ac.chap.Window.prototype.addView = function(layoutNode, options, renderAfter)
{
	var view_index = this.views.length;
	this.viewLayoutNodes.push(layoutNode);
	this.views.push($new(ac.chap.View, this, view_index, options||{}));
	this.row_id_map[view_index] = [];
	if ( 0 < view_index )
	{
//		console.log(view_index);
		// creating duplicate
		var n = this.row_id_map[0].length;
		for ( var i=0; i<n; i++ )
		{
			var row = this.row_id_map[0][i];
			this.row_id_map[view_index][i] = [row[0], false, row[2], [], [], []];
		}
		//this.row_id_map[view_index] = [].concat(this.row_id_map[0].slice(0));
	}
	if ( renderAfter )
	{
		this.views[view_index].recalculateVisibleRows();
		this.views[view_index].render(this.viewLayoutNodes[view_index]);
		this.tokenize(0);
		this.renderText();
	}
//	console.log('%o', this.row_id_map[view_index]);
	return view_index;
}

ac.chap.Window.prototype.resizeView = function(viewIndex)
{
	if ( this.views[viewIndex] )
	{
		this.views[viewIndex].resize();
	}
}

ac.chap.Window.prototype.edit = function(text, setAsActive)
{
	this.char_map = [];
	for ( var i=0; i<this.views.length; i++ )
	{
//		this.row_id_map.push([]);
	}
	this.syntax_map = [];
	this.style_map = [];
	this.row_id_sequence = 1;
	this.transaction_log = [];
	this.redo_log = [];
	
	this.insertIntoCharacterMap(text, 0, 0);
	this.tokenize(0);
	this.renderText();
	setAsActive = setAsActive || true;
	if ( setAsActive )
	{
		ac.chap.setActiveComponent(this);
		if (0 < this.views.length)
		{
			this.activeView = this.views[0];
		}
	}
}

ac.chap.Window.prototype.hide = function()
{
	this.hideCaret();
	var n = this.views.length
	for ( var i=0; i<n; i++ )
	{
		this.views[i].hide();
    	$delete(this.views[i]);
	}
	$delete(this.views);
	ac.chap.setActiveComponent(null);
}

ac.chap.Window.prototype.show = function()
{
	this.render();
	ac.chap.setActiveComponent(this);
}

ac.chap.Window.prototype.showInteractiveSearch = function()
{
	if (this.activeView)
	{
		this.activeView.showInteractiveSearch();
	}
}

ac.chap.Window.prototype.hideInteractiveSearch = function()
{
	for (var i=0; i<this.views.length; i++)
	{
		this.views[i].hideInteractiveSearch();
	}
}

ac.chap.Window.prototype.toggleBookmark = function(rowIndex)
{
	var rowIndex = rowIndex || this.caret.position[0];
	for ( var i=0; i<this.views.length; i++ )
	{
		if ( 'undefined' == typeof this.row_id_map[i][rowIndex] )
		{
			return;
		}
		// marking as changed
		this.row_id_map[i][rowIndex][1] = false;
		var row_state = this.row_id_map[i][rowIndex][2];
		if ( ac.chap.ROWSTATE_BOOKMARK == (row_state & ac.chap.ROWSTATE_BOOKMARK) )
		{
			// already bookmarked
			this.row_id_map[i][rowIndex][2] &= (65535-ac.chap.ROWSTATE_BOOKMARK);
		}
		else
		{
			this.row_id_map[i][rowIndex][2] |= ac.chap.ROWSTATE_BOOKMARK;
		}
	}
}

ac.chap.Window.prototype.setRuntimeOption = function(key, value)
{
	var font_sizes = this.options.font.allowedSizes;
	var font_size = this.options.font.size;
	var redraw = false;
	if ('font' == key)
	{
		if ($isset(value['size']))
		{
			if (font_sizes[0] <= value.size && value.size <= font_sizes[font_sizes.length-1])
			{
				font_size = value.size;
				redraw = true;
			}
		}
		if ($isset(value['family']))
		{
			this.options.font.family = value.family;
		}
	}
	else if ('font.size' == key)
	{
		if ('bigger' == value)
		{
			for (var i=0; i<font_sizes.length; i++)
			{
				if (font_size < font_sizes[i])
				{
					font_size = font_sizes[i];
					break;
				}
			}
		}
		else if ('smaller' == value)
		{
			for (var i=font_sizes.length-1; i>= 0; i--)
			{
				if (font_size > font_sizes[i])
				{
					font_size = font_sizes[i];
					break;
				}
			}
		}
		else
		{
			if (font_sizes[0] <= value && value <= font_sizes[font_sizes.length-1])
			{
				font_size = value;
			}
		}
		this.options.font.size = font_size;
		redraw = true;
	}
	else if ('font.family' == key)
	{
		this.options.font.family = value;
		redraw = true;
	}
	else if ('word.wrap' == key)
	{
		if (this.activeView)
		{
			this.hideCaret();
			this.activeView.options.wordWrap = value;
			this.activeView.reloadOptions();
			this.showCaret();
		}
	}
	if (redraw)
	{
		this.hideCaret();
		var num_views = this.views.length;
		for (var i=0; i<num_views; i++)
		{
			this.views[i].reloadOptions();
		}
		this.showCaret();
	}
}

ac.chap.Window.prototype.scrollToBookmark = function(rowIndex, directionOffset)
{
	rowIndex = rowIndex || this.caret.position[0];
	var view = this.activeView;
	if (null == view)
	{
		return;
	}
	var num_rows = this.row_id_map[view.index].length;
	if (0 == num_rows)
	{
		return;
	}
	var start_index = rowIndex + directionOffset;
	if (1 == directionOffset)
	{
		num_rows = num_rows - start_index;
	}
	else
	{
		num_rows = rowIndex;
	}
	if (!this.findAndScrollToBookmark(view, start_index, num_rows, directionOffset))
	{
		// not found, try the other half reversed search
		if (1 == directionOffset)
		{
			start_index = 0;
			num_rows = rowIndex;
		}
		else
		{
			num_rows = this.row_id_map[view.index].length;
			start_index = num_rows - 1;
			num_rows -= rowIndex;
		}
		this.findAndScrollToBookmark(view, start_index, num_rows, directionOffset);
	}
}

ac.chap.Window.prototype.findAndScrollToBookmark = function(view, startIndex, numRowsToSearch, directionOffset)
{
	var i = 0;
	var active_index = startIndex;
	// console.log(startIndex, numRowsToSearch, directionOffset);
	while (i<numRowsToSearch)
	{
		// console.warn(i, active_index);
		var row_state = this.row_id_map[view.index][active_index][2];
		if (ac.chap.ROWSTATE_BOOKMARK == (row_state & ac.chap.ROWSTATE_BOOKMARK))
		{
			// found a bookmark
			view.scrollToRow(active_index, true);
			return true;
		}
		active_index += directionOffset;
		i++;
	}
	return false;
}

ac.chap.Window.prototype.setEditMode = function(mode)
{
	this.caret.mode = mode;
	ac.chap.setActiveComponent(this);
	this.tokenize();
	this.renderText();
}

ac.chap.Window.prototype.setTheme = function(theme)
{
	for ( var i=0; i<this.views.length; i++ )
	{
		this.views[i].setTheme(theme);
	}
}

ac.chap.Window.prototype.setLanguage = function(language)
{
	this.language = $new(language);
	this.tokenize();
	this.foldingize();
	this.renderText();
	this.showCaret();
}

ac.chap.Window.prototype.setSnippets = function(snippets)
{
	this.snippets = snippets;
	this.keymap.importSnippets(snippets);
}

ac.chap.Window.prototype.setCommands = function(commands)
{
	this.commands = commands;
	this.keymap.importCommands(commands);
}

ac.chap.Window.prototype.getTabelator = function(tabelator)
{
	if (0 < this.views.length)
	{
		return this.views[0].options.tabelator;
	}
	return '\t';
}

ac.chap.Window.prototype.setTabelator = function(tabelator)
{
	for ( var i=0; i<this.views.length; i++ )
	{
		this.views[i].options.tabelator = tabelator;
	}
}

ac.chap.Window.prototype.render = function()
{
	for ( var i=0; i<this.views.length; i++ )
	{
		this.views[i].render(this.viewLayoutNodes[i]);
	}
}


ac.chap.Window.prototype.getTimestamp = function()
{
	var d = new Date();
	return 60000*d.getMinutes()+1000*d.getSeconds()+d.getMilliseconds();
}

ac.chap.Window.prototype.keyboardListener = function(code, mask)
{
	var redraw_text = false;
	var redraw_caret = false;
	var scroll_to_caret = false;
	var selection_changed = false;
	this.state.lastKeyTimePressed = new Date().getTime();

	var key_code = code;
	var control_key = mask & 30;
	if (this.state.passThroughKeysListener && this.state.passThroughKeysListener(key_code, control_key))
	{
		return true;
	}
	var definition = $getdef(this.keymap.definition[key_code], this.keymap.definition[0]);
	definition = $getdef(definition[control_key], definition[ac.chap.CKEY_NONE]);
	if ( 'undefined' == typeof definition )
	{
		definition = this.keymap.definition[0][ac.chap.CKEY_NONE];
	}
	if (fry.keyboard.COPY == (mask & fry.keyboard.COPY))
	{
		return true;
	}
	// console.log(code, mask);
    var me = this;
	var num_actions = definition.length;
	for (var i=0; i<num_actions; i+=2)
	{
		var action_type = definition[i];
		var params = definition[i+1];
		params.keyCode = key_code;
		params.controlKey = control_key;
		if (!this.state.actionListenersStopped)
		{
		    var caret_row = this.caret.position[0];
		    var caret_col = this.caret.position[1];
			for (var ii in this.state.actionListeners)
			{
				var listener = this.state.actionListeners[ii];
				if (ac.chap.ACTION_LISTENER_BEFORE == (listener[0] & ac.chap.ACTION_LISTENER_BEFORE))
				{
				    if (!listener[3])
				    {
				        // synchronous
						listener[2](me, listener[1], ac.chap.ACTION_LISTENER_BEFORE, 0, action_type, params, caret_row, caret_col);
				    }
				    else
				    {
				        setTimeout(function(){listener[2](me, listener[1], ac.chap.ACTION_LISTENER_BEFORE, 0, action_type, params, caret_row, caret_col);}, 300);
				    }
				}
			}
		}
		var result = this.runAction(action_type, params);
		if  (!this.state.actionListenersStopped)
		{
		    var caret_row = this.caret.position[0];
		    var caret_col = this.caret.position[1];
			for (var ii in this.state.actionListeners)
			{
				var listener = this.state.actionListeners[ii];
				if (ac.chap.ACTION_LISTENER_AFTER == (listener[0] & ac.chap.ACTION_LISTENER_AFTER))
				{
				    if (!listener[3])
				    {
				        // synchronous
						listener[2](me, listener[1], ac.chap.ACTION_LISTENER_AFTER, result, action_type, params, caret_row, caret_col);
				    }
				    else
				    {
				        setTimeout(function(){listener[2](me, listener[1], ac.chap.ACTION_LISTENER_AFTER, result, action_type, params, caret_row, caret_col);}, 300);						        
				    }
				}
			}
		}
		if (!redraw_caret)
		{
			redraw_caret = ac.chap.ACTION_RES_REDRAWCARET == (result & ac.chap.ACTION_RES_REDRAWCARET);
		}
		if (!redraw_text)
		{
			redraw_text = ac.chap.ACTION_RES_REDRAWTEXT == (result & ac.chap.ACTION_RES_REDRAWTEXT);
		}
		if (!selection_changed)
		{
			selection_changed = ac.chap.ACTION_RES_SELECTIONCHANGED == (result & ac.chap.ACTION_RES_SELECTIONCHANGED);
		}
		if (!scroll_to_caret)
		{
			scroll_to_caret = ac.chap.ACTION_RES_SCROLLTOCARET == (result & ac.chap.ACTION_RES_SCROLLTOCARET);
		}
	}
	if (selection_changed)
	{
		redraw_caret = false;
		this.hideCaret();
	}
	else
	{
		this.state.lastCaretPosition = [this.caret.position[0], this.caret.position[1]];
		if (this.removeSelection())
		{
			redraw_text = true;
			redraw_caret = true;
		}
	}
	this.state.lastKeyCode = key_code;
	this.state.lastControlKey = control_key;
	if (scroll_to_caret)
	{
		// console.log('scroll to caret: '+this.caret.position[0]);
		this.activeView.scrollToRow(this.caret.position[0], false, true);
	}
	this.processActionResult(redraw_text, redraw_caret);
	// disabling further key actions
	return true;
}

// called if chap is not a part of Fry MVC 
ac.chap.Window.prototype.standaloneKeyboardListener = function(code, mask)
{
	if (fry.keyboard.CONTROL_CODE == (mask & fry.keyboard.CONTROL_CODE))
	{
		if (fry.keyboard.PASTE == (mask & fry.keyboard.PASTE))
		{
			// pasted text from clipboard received
			return this.onSystemClipboardPaste(fry.keyboard.getClipboardContent());
		}
		else if (fry.keyboard.CUT == (mask & fry.keyboard.CUT))
		{
			// cut, let's clear selection if it exists
			return this.onSystemClipboardCut();
		}
		else if (fry.keyboard.SIG_CLIPBOARD_GET == (mask & fry.keyboard.SIG_CLIPBOARD_GET))
		{
			// need to return selected content
			return this.onSystemClipboardCopy();
		}
		else
		{
			code = -code;
		}
	}
	return this.keyboardListener(code, mask);
}

ac.chap.Window.prototype.processActionResult = function(redrawText, redrawCaret)
{
	if ( redrawText )
	{
		var t = this.getTimestamp();
		if ( this.state.tokenizerTimer )
		{
			clearTimeout(this.state.tokenizerTimer);
		}
		if  ( this.state.scheduledTokenizerTime < t - this.options.tokenizerLazyLaunch )
		{
//			console.log('Tokenizer launched DIRECTLY at: '+this.getTimestamp());
			this.tokenize(0);
			this.state.scheduledTokenizerTime = this.getTimestamp() + this.options.tokenizerLazyLaunch;
		}
		else
		{
			var me = this;
			this.state.tokenizerTimer = setTimeout(function()
			{
//				console.log('Tokenizer launched at: '+me.getTimestamp());
				me.tokenize(0);
				me.state.scheduledTokenizerTime = me.getTimestamp();
				me.renderText();
				delete me;

			}, this.options.tokenizerLazyLaunch);
		}
		this.renderText();
	}
	if ( redrawCaret )
	{
		this.showCaret();
	}
}

ac.chap.Window.prototype.setUserId = function(userId)
{
    this.userId = userId;
    // console.info('User ID set to: %s', userId);
}

ac.chap.Window.prototype.addCaretListener = function(callback)
{
	this.state.caretListener = callback;
}

ac.chap.Window.prototype.removeCaretListener = function(callback)
{
	this.state.caretListener = null;
}

ac.chap.Window.prototype.addCommandListener = function(callback)
{
    this.state.commandListener = callback;
}

ac.chap.Window.prototype.removeCommandListener = function(callback)
{
    this.state.commandListener = null;
}

ac.chap.Window.prototype.addPassThroughKeysListener = function(callback)
{
	this.state.passThroughKeysListener = callback;
}

ac.chap.Window.prototype.removePassThroughKeysListener = function()
{
	this.state.passThroughKeysListener = null;
}

ac.chap.Window.prototype.addTransactionListener = function(callback, lazyRunMsecs)
{
    this.state.transactionListener = [callback, $getdef(lazyRunMsecs, 800)];
}

ac.chap.Window.prototype.hasTransactionListener = function()
{
	return null != this.state.transactionListener && null != this.state.transactionListener[0];
}

ac.chap.Window.prototype.removeTransactionListener = function(callback)
{
    this.state.transactionListener = null;
}

ac.chap.Window.prototype.addActionListener = function(type, action, callback, asynchronous)
{
	callbackIndex = this.state.actionListeners.length;
	this.state.actionListeners[callbackIndex] = [type, action, callback, asynchronous];
	return callbackIndex;
}

ac.chap.Window.prototype.removeActionListener = function(callbackIndex)
{
	delete this.state.actionListeners[callbackIndex];
}

ac.chap.Window.prototype.stopActionListeners = function()
{
	this.state.actionListenersStopped = true;
}

ac.chap.Window.prototype.startActionListeners = function()
{
	this.state.actionListenersStopped = false;
}

ac.chap.Window.prototype.getVariableValue = function(varName, defaultValue)
{
	var value = '';
	if ( 'CHAP_SELECTED_TEXT' == varName )
	{
		value = this.getSelection();
	}
	else if ( 'CHAP_CLIPBOARD_TEXT' == varName )
	{
		value = fry.keyboard.getClipboardContent();
	}
	else if ( 'CHAP_PREV_WORD' == varName )
	{
		value = this.getWordAt(this.caret.position[0], this.caret.position[1], -1);
	}
	else if ( 'CHAP_NEXT_WORD' == varName )
	{
		value = this.getWordAt(this.caret.position[0], this.caret.position[1], 1);
	}
	else if ( 0 == varName.indexOf('CHAP_WORD') )
	{
		words = [''];
		if ( !isNaN(varName.substr(9)) )
		{
			words = this.getWordAt(this.caret.position[0], this.caret.position[1], parseInt(varName.substr(9)));
			if ( 'string' == typeof words )
			{
				words = [words];
			}
		}
		value = words[words.length-1];
	}
	if ( '' == value || null == value )
	{
		value = defaultValue || '';
	}
	return value;
}

ac.chap.Window.prototype.runCommand = function(keyCode, controlKeysMask, caretRow, caretCol, command, params)
{
    if ( null == this.state.commandListener )
    {
        console.warn('There is no command listener defined.');
        return 0;
    }
    return this.state.commandListener(this, keyCode, controlKeysMask, caretRow, caretCol, command, params);
}

ac.chap.Window.prototype.runAction = function(actionType, params)
{
	var caret_row = this.caret.position[0];
	var caret_col = this.caret.position[1];
	var key_code = params.keyCode;
	var control_key = params.controlKey;
//	console.log('action_type:%s, params:%o', actionType, params);
	
	switch ( actionType )
	{
		case ac.chap.ACTION_CARET:
		{
			if ( $isset(params.store) )
			{
				this.state.lastCaretPosition = [caret_row, caret_col];
			}
			else if ( $isset(params.move) )
			{
				var direction = params.move;
				if ( 'left' == direction )
				{
					if ( 0 < caret_col )
					{
						caret_col--;
					}
					else
					{
						if ( 0 < caret_row )
						{
							caret_row--;
							caret_col = this.char_map[caret_row].length;
						}
					}
					this.setCaretPosition(caret_row, caret_col);
					return ac.chap.ACTION_RES_REDRAWCARET;
				}
				else if ( 'right' == direction )
				{
					if ( this.char_map[caret_row].length > caret_col )
					{
						caret_col++;
					}
					else
					{
						if ( 'undefined' != typeof this.char_map[caret_row+1] )
						{
							caret_row++;
							caret_col = 0;
						}
					}
					this.setCaretPosition(caret_row, caret_col);
					return ac.chap.ACTION_RES_REDRAWCARET;
				}
				else if ( 'up' == direction )
				{
					if ( 0 < caret_row )
					{
						var move_end = this.char_map[caret_row].length == caret_col;
						if ( move_end )
						{
							caret_col = this.char_map[caret_row-1].length;
						}
						else
						{
							caret_col = Math.min(this.char_map[caret_row-1].length, caret_col);
						}
						this.setCaretPosition(caret_row-1, caret_col);
						return ac.chap.ACTION_RES_REDRAWCARET;
					}
				}
				else if ( 'down' == direction )
				{
					if ( 'undefined' != typeof this.char_map[caret_row+1] )
					{
						var move_end = this.char_map[caret_row].length == caret_col;
						if ( move_end )
						{
							caret_col = this.char_map[caret_row+1].length;
						}
						else
						{
							caret_col = Math.min(this.char_map[caret_row+1].length, caret_col);
						}
						this.setCaretPosition(caret_row+1, caret_col);
						return ac.chap.ACTION_RES_REDRAWCARET;
					}					
				}
				else if ( 'prev_word' == direction )
				{
					if ( 0 < caret_col )
					{
						var ch = this.char_map[caret_row].charAt(caret_col-1);
						var re = this.language.wordDelimiter;
						var look_for_wch = re.test(ch);
						while ( 0 != caret_col )
						{
							ch = this.char_map[caret_row].charAt(caret_col-1);
							if ( look_for_wch != re.test(ch) )
							{
								break;
							}
							caret_col--;
						}
					}
					else
					{
						if ( 0 < caret_row )
						{
							caret_row--;
							caret_col = this.char_map[caret_row].length;
						}
					}
					this.setCaretPosition(caret_row, caret_col);
					return ac.chap.ACTION_RES_REDRAWCARET;					
				}
				else if ( 'next_word' == direction )
				{
					if ( this.char_map[caret_row].length > caret_col )
					{
						var ch = this.char_map[caret_row].charAt(caret_col);
						var re = this.language.wordDelimiter;
						var look_for_wch = re.test(ch);
						while ( this.char_map[caret_row].length > caret_col )
						{
							ch = this.char_map[caret_row].charAt(caret_col);
							if ( look_for_wch != re.test(ch) )
							{
								break;
							}
							caret_col++;
						}
					}
					else
					{
						if ( 'undefined' != typeof this.char_map[caret_row+1] )
						{
							caret_row++;
							caret_col = 0;
						}
					}
					this.setCaretPosition(caret_row, caret_col);
					return ac.chap.ACTION_RES_REDRAWCARET;
				}
				else if ( 'prev_regexp' == direction )
				{
					if ( 0 < caret_col )
					{
						var row = this.char_map[caret_row].substring(0, caret_col);
						var re = new RegExp(params['re'].replace('|', '\\'));
						var matches = re.exec(row);
						if (0 == matches.length)
						{
							console.warning('Invalid RE definition for `prev_regexp\' direction in ACTION_CARET.move action in keymap.');
							caret_col--;
						}
						else
						{
							caret_col -= matches[0].length + 1;
						}
					}
					else
					{
						if ( 0 < caret_row )
						{
							caret_row--;
							caret_col = this.char_map[caret_row].length;
						}
					}
					this.setCaretPosition(caret_row, caret_col);
					return ac.chap.ACTION_RES_REDRAWCARET;
				}
				else if ( 'next_regexp' == direction )
				{
					if ( this.char_map[caret_row].length > caret_col )
					{
						var row = this.char_map[caret_row].substr(caret_col + 1);
						var re = new RegExp(params['re'].replace('|', '\\'));
						var matches = re.exec(row);
						if (0 == matches.length)
						{
							console.warning('Invalid RE definition for `next_regexp\' direction in ACTION_CARET.move action in keymap.');
							caret_col++;
						}
						else
						{
							caret_col += matches[0].length + 1;
						}
					}
					else
					{
						if ( 'undefined' != typeof this.char_map[caret_row+1] )
						{
							caret_row++;
							caret_col = 0;
						}
					}
					this.setCaretPosition(caret_row, caret_col);
					return ac.chap.ACTION_RES_REDRAWCARET;
				}
				else if ( 'row_start' == direction )
				{
					if ( 0 < caret_col )
					{
						caret_col = 0;
						this.setCaretPosition(caret_row, caret_col);				
						return ac.chap.ACTION_RES_REDRAWCARET;
					}
				}
				else if ( 'row_end' == direction )
				{
					if ( this.char_map[caret_row].length > caret_col )
					{
						caret_col = this.char_map[caret_row].length;
						this.setCaretPosition(caret_row, caret_col);				
						return ac.chap.ACTION_RES_REDRAWCARET;
					}
				}
				else if ( 'page_up' == direction )
				{
					if (this.activeView)
					{
						var row = caret_row - this.activeView.numRows;
						if (0 > row)
						{
							row = 0;
						}
						this.setCaretPosition(row, 0 != caret_col ? this.char_map[row].length : 0);
						return ac.chap.ACTION_RES_REDRAWCARET;
					}
					return 0;
				}
				else if ( 'page_down' == direction )
				{
					if (this.activeView)
					{
						var row = caret_row + this.activeView.numRows;
						if (this.char_map.length <= row)
						{
							row = this.char_map.length-1;
						}
						this.setCaretPosition(row, 0 != caret_col ? this.char_map[row].length : 0);
						return ac.chap.ACTION_RES_REDRAWCARET;
					}
					return 0;
				}
				else if ( 'doc_start' == direction )
				{
					this.setCaretPosition(0,0);
					return ac.chap.ACTION_RES_REDRAWCARET;
				}
				else if ( 'doc_end' == direction )
				{
					var last_index = this.char_map.length-1
					this.setCaretPosition(last_index, this.char_map[last_index].length-1);
					return ac.chap.ACTION_RES_REDRAWCARET;
				}
			}
			else if ( $isset(params.moveBy) )
			{
				var offset = params.moveBy;
				if ( 'column' == offset )
				{
					//move by params.value columns, newlines are counted as column, params.value may be negative indication caret moving to the left
					if ( 0 < params.value )
					{
						var range_source = (this.char_map[caret_row].substr(caret_col)+'\n'+this.char_map.slice(caret_row+1).join('\n')).substr(0, params.value);
						range_source = range_source.split('\n');
						caret_row += range_source.length-1;
						caret_col = range_source[range_source.length-1].length + (1==range_source.length ? caret_col : 0);
					}
					else
					{
						var range_source = (this.char_map.slice(0, caret_row).join('\n')+'\n'+this.char_map[caret_row].substr(0, caret_col));
						range_source = range_source.substr(range_source.length+params.value);
						range_source = range_source.split('\n');
						caret_row -= (range_source.length-1);
						caret_col = (1==range_source.length ? caret_col : this.char_map[caret_row].length) - range_source[0].length;
					}
					this.setCaretPosition(caret_row, caret_col);
					return ac.chap.ACTION_RES_REDRAWCARET;
				}
				else if ( 'row' == offset )
				{
					// move by params.value rows
				}
				else if ( 'page' == offset )
				{
					// move by params.value pages
				}
			}
			else if ( $isset(params.moveTo) )
			{
				// move to params.moveTo[0], params.moveTo[1]
				this.setCaretPosition(params.moveTo[0], params.moveTo[1]);
				return ac.chap.ACTION_RES_REDRAWCARET;
			}
		};break;
		case ac.chap.ACTION_SELECTION:
		{
			if ( $isset(params.remove) )
			{
				var changed = this.removeSelection();
				return ac.chap.ACTION_RES_REDRAWCARET | (changed ? ac.chap.ACTION_RES_REDRAWTEXT : 0);
			}
			else if ( $isset(params.add) )
			{
				this.addSelection([caret_row, caret_col], this.state.lastCaretPosition);
				this.renderSelection();
				return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_SELECTIONCHANGED;
			}
			else if ( $isset(params.all) )
			{
				$__tune.behavior.clearSelection();
				this.addAllSelection();
				this.renderSelection();
				return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_SELECTIONCHANGED;
			}
		};break;
		case ac.chap.ACTION_INSERT:
		{
			var str = null;
			if ( $isset(params.row) )
			{
				var ins_content = '\n';
				caret_col = 0;
				// if ( 0 < caret_row )
				// {
				// 	// indenting by previous row
				// 	var t = this.char_map[caret_row];
				// 	var n = t.length;
				// 	var re = this.language.indentIgnoreMarker;
				// 	while ( caret_col<n )
				// 	{
				// 		var ch = t.charAt(caret_col);
				// 		if ( !re.test(ch) )
				// 		{
				// 			break;
				// 		}
				// 		caret_col++;
				// 	}
				// 	ins_content += t.substr(0, caret_col);
				// }
				this.insertIntoCharacterMap(ins_content);
				this.setCaretPosition(caret_row+1, caret_col);
				return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;				
			}
			else if ( $isset(params.character) )
			{
				if ( 31 < key_code || -9 == key_code )
				{
					// getting string character
					str = -9 == key_code ? '\t' : String.fromCharCode(key_code);
				}
			}
			else if ( $isset(params.string) )
			{
				str = params.string;
			}
			// inserting string if specified
			if ( null != str )
			{
				if ( null != this.selection )
				{
					// inserting into selection, first, let's remove selected chunk
					var range_from = [this.selection.startPosition[0], this.selection.startPosition[1]];
					var range_to = [this.selection.endPosition[0], this.selection.endPosition[1]];
					var switched = false;
					if ( (range_to[0] < range_from[0]) || (range_to[0] == range_from[0] && range_to[1] < range_from[1]) )
					{
						var r = range_from;
						range_from = range_to;
						range_to = r;
						switched = true;
					}
					this.removeFromCharacterMap(range_from[0], range_from[1]+(switched?0:0), range_to[0], range_to[1]+(switched?0:1));
					this.setCaretPosition(range_from[0], range_from[1]);
					caret_row = range_from[0];
//					caret_col = range_from[1] - str.length + 1;
					caret_col = range_from[1];
					this.removeSelection();
				}
				else if ( 2 == this.caret.mode )
				{
					this.removeFromCharacterMap(caret_row, caret_col);
				}
				// console.log('inserting: `%s`', str.replace(/\n/g, '$'));
				this.insertIntoCharacterMap(str);
				if ( !params.skipCaretChange )
				{
					if ( -1 == str.indexOf('\n') )
					{
						caret_col += str.length;					
					}
					else
					{
						caret_row += str.length - str.replace(/\n/g, '').length;
						caret_col = str.length - str.lastIndexOf('\n') - 1;					
					}
					this.setCaretPosition(caret_row, caret_col);					
				}
				return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;
			}			
		};break;
		case ac.chap.ACTION_UPDATE:
		{
			
		};break;
		case ac.chap.ACTION_DELETE:
		{
			if ( $isset(params.row) )
			{
				if (this.getNumRows() == caret_row+1)
				{
					if (0 == caret_row)
					{
						this.removeFromCharacterMap(caret_row, 0, caret_row, this.char_map[caret_row].length);
						this.setCaretPosition(0, 0);
					}
					else
					{
						this.removeFromCharacterMap(caret_row-1, this.char_map[caret_row-1].length, caret_row, this.char_map[caret_row].length);
						this.setCaretPosition(caret_row-1, this.char_map[caret_row-1].length);						
					}
				}
				else
				{
					this.removeFromCharacterMap(caret_row, 0, caret_row+1, 0);
				}
				return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;
			}
			else if ( $isset(params.character) )
			{
				var after_caret = !params.character;
				var proceed_delete = true;
				if ( null != this.selection )
				{
					// removing selection
					var range_from = [this.selection.startPosition[0], this.selection.startPosition[1]];
					var range_to = [this.selection.endPosition[0], this.selection.endPosition[1]];
//					var range_to = [caret_row, caret_col];
					var switched = false;
					if ( (range_to[0] < range_from[0]) || (range_to[0] == range_from[0] && range_to[1] < range_from[1]) )
					{
						var r = range_from;
						range_from = range_to;
						range_to = r;
						switched = true;
					}
					this.removeFromCharacterMap(range_from[0], range_from[1], range_to[0], range_to[1]+(switched?0:1));
					caret_row = range_from[0];
					caret_col = range_from[1]+(after_caret?0:1);
					this.removeSelection();
				}
				else
				{
					var range_from = [caret_row, caret_col];
					var range_to = [caret_row, caret_col];
					if ( after_caret )
					{
						if ( caret_col == this.char_map[range_from[0]].length )
						{
							if ( this.char_map.length-1 == caret_row )
							{
								proceed_delete = false;
							}
							else
							{
								range_to[0]++;
								range_to[1] = 0;
							}
						}
						else
						{
							range_to[1]++;
						}
					}
					else
					{
						if ( 0 == caret_col )
						{
							if ( 0 == caret_row )
							{
								proceed_delete = false;
							}
							else
							{
								range_from[0]--;
								range_from[1] = this.char_map[range_from[0]].length;
							}
						}
						else
						{
							range_from[1]--;
						}
						caret_row = range_from[0];
						caret_col = range_from[1]+1;
					}
					if ( proceed_delete )
					{
//						console.log('%o - %o', range_from, range_to);
						this.removeFromCharacterMap(range_from[0], range_from[1], range_to[0], range_to[1]);
						this.removeSelection();
					}
				}
				if ( proceed_delete )
				{
					this.setCaretPosition(caret_row, caret_col-(after_caret?0:1));
					return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;				
				}
			}
		};break;
		case ac.chap.ACTION_CLIPBOARD:
		{
			if ( $isset(params.cut) )
			{
				if (null != this.selection)
				{
					return this.runAction(ac.chap.ACTION_DELETE, {character:true});
				}
			}
			else if ( $isset(params.paste) )
			{
				this.runAction(ac.chap.ACTION_INSERT, {string:params.content})
				return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;					
			}
		};break;
		case ac.chap.ACTION_UNDO:
		{
			//console.log('UNDO');
			var num_trecords = this.transaction_log.length;
			if ( 3 < num_trecords ) // ignoring first operation since it's the original source inserted using edit() method
			{
				var operation_type = this.transaction_log[num_trecords-3];
				var params = this.transaction_log[num_trecords-2];
				var source = this.transaction_log[num_trecords-1];
				if ( ac.chap.TRANSLOG_TYPE_INSERT == operation_type )
				{
					var range_from = [params[0], params[1]];
					var range_to = [params[0], params[1]];
					range_to[0] += (source.length - source.replace(/\n/g, '').length);
					var ix = source.lastIndexOf('\n');
					range_to[1] = -1 == ix ? (range_from[1]+source.length) : (source.length - ix);
					
//					this.removeFromCharacterMap(range_from[0], range_from[1], range_to[0], range_to[1], this.redo_log);
					this.removeFromCharacterMap(range_from[0], range_from[1], range_to[0], range_to[1]);//, this.redo_log);
					caret_row = range_from[0];
					caret_col = range_from[1];
					
				}
				else if ( ac.chap.TRANSLOG_TYPE_REMOVE == operation_type )
				{
					this.insertIntoCharacterMap(source, params[0], params[1]);
					caret_row = params[2];
					caret_col = params[3];
				}
				this.setCaretPosition(caret_row, caret_col);
				this.removeSelection();
				
				this.redo_log = [].concat(this.redo_log, this.transaction_log.slice(num_trecords-3, num_trecords));
				this.transaction_log = [].concat(this.transaction_log.slice(0, num_trecords-3));

				return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;
			}
		};break;
		case ac.chap.ACTION_REDO:
		{
			var num_trecords = this.redo_log.length;
			if ( 0 < num_trecords )
			{
				var operation_type = this.redo_log[num_trecords-3];
				var params = this.redo_log[num_trecords-2];
				var source = this.redo_log[num_trecords-1];
				this.redo_log = [].concat(this.redo_log.slice(0, num_trecords-3));
				if ( ac.chap.TRANSLOG_TYPE_REMOVE == operation_type )
				{
					this.removeFromCharacterMap(params[0], params[1], params[2], params[3]);
					caret_row = params[0];
					caret_col = params[1];

					this.setCaretPosition(caret_row, caret_col);
					this.removeSelection();
				}
				else if ( ac.chap.TRANSLOG_TYPE_INSERT == operation_type )
				{
					this.runAction(ac.chap.ACTION_INSERT, {string:source});
				}
				return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;
			}
		};break;
		case ac.chap.ACTION_CUSTOM:
		{
			var action_name = 'action_?'.embed($getdef(params.action, 'NotDefined'));
			if ( !this.keymap[action_name] )
			{
				console.warn('Action `%s` not defined in the keymap.', params.action);
				action_name = 'action_NotDefined';
			}
			return this.keymap[action_name](key_code, control_key, caret_row, caret_col, this, params);
		};break;
	}
	return 0;
}

ac.chap.Window.prototype.getActiveViewIndex = function()
{
	if ( null == this.activeView )
	{
		return -1;
	}
	return this.activeView.index;
}

ac.chap.Window.prototype.getCharAt = function(row, column)
{
	row = $getdef(row, this.caret.position[0]);
	column = $getdef(column, this.caret.position[1]);
	return this.char_map[row].charAt(column);
}

ac.chap.Window.prototype.getStringAt = function(row, column, width)
{
	row = $getdef(row, this.caret.position[0]);
	column = $getdef(column, this.caret.position[1]);
	width = $getdef(width, -1);
	// defaults to string before caret
//	console.log('getStringAt: %s, %s, %s', row, column, width);
	var source = '';
	if ( 0 > width )
	{
		// will go before [row,column]
		source = this.char_map.slice(0, row).join('\n')+'\n'+this.char_map[row].substr(0, column);
		return source.substr(source.length+width);
	}
	else
	{
		// will go after [row,column]
		source = this.char_map.slice(row).join('\n').substr(column);
		return source.substr(0, width);
	}
}

ac.chap.Window.prototype.getWordAt = function(row, column, numWords)
{
	// if numWords <0 returns words before otherwise after position. if omitted, default value is -1 that is word before caret
	// also, if more than one word is required, returns array of words as result
	row = $getdef(row, this.caret.position[0]);
	column = $getdef(column, this.caret.position[1]);
	numWords = $getdef(numWords, -1);
	var words = [];
	var re = this.language.wordDelimiter;
	var required_words = numWords;
	var direction_after = 0 < numWords;
	var next_word = true;
	required_words = Math.abs(-numWords);
	if ( !direction_after )
	{
		column--;
		if ( -1 == column )
		{
			row--;
			if ( -1 == row )
			{
				return words;
			}
			column = this.char_map[row].length-1;
		}
	}
	while (true)
	{
		var ch = this.char_map[row].charAt(column)
		if ( re.test(ch) )
		{
			if ( next_word )
			{
				words.push('');
				next_word = false;
			}
			// word character found
			if ( direction_after )
			{
				words[words.length-1] += ch;				
			}
			else
			{
				words[words.length-1] = ch + words[words.length-1];
			}
		}
		else
		{
			if ( required_words == words.length )
			{
				break;				
			}
			next_word = true;
		}
		
		column += (direction_after ? 1 : -1);
		if ( 0 > column )
		{
			row--;
			if ( -1 == row )
			{
				break;
			}
			next_word = true;
			column = this.char_map[row].length-1;				
		}
		else if ( this.char_map[row].length <= column )
		{
			row++;
			if ( this.char_map.length == row )
			{
				break;
			}
			next_word = true;
			column = 0;
		}
	}
	if ( 1 == required_words )
	{
		return words[0] ? words[0] : false;
	}
	return words;
}

ac.chap.Window.prototype.getLineAt = function(row)
{
    return this.char_map[row];
}

ac.chap.Window.prototype.getText = function()
{
	return this.char_map.join('\n');
}

ac.chap.Window.prototype.getNumRows = function()
{
    return this.char_map.length;
}

ac.chap.Window.prototype.getSyntaxHighlightingSource = function()
{
	if (null != this.activeView)
	{
		return this.activeView.getSyntaxHighlightingSource();
	}
	return 'ni';
}

ac.chap.Window.prototype.getCaretAbsolutePosition = function()
{
	if ( null != this.activeView )
	{
        var pos = this.activeView.getRenderedCharPosition(this.caret.position[0], this.caret.position[1]);
    	if ( null != pos )
    	{
    	    var root_pos = this.activeView.nodeScrollArea.abspos();
    	    return [pos[0]+root_pos.x+this.activeView.options.colWidth, pos[1]+root_pos.y+this.activeView.options.rowHeight];
    	}
    }
    return null;
}

ac.chap.Window.prototype.stopTransactionLog = function()
{
	this.state.transactionLogStopped = true;
}

ac.chap.Window.prototype.startTransactionLog = function()
{
	this.state.transactionLogStopped = false;
}

ac.chap.Window.prototype.addAllSelection = function()
{
	var num_rows = this.char_map.length;
	var num_views = this.views.length;
	for ( var i=0; i<num_rows; i++ )
	{
		for ( var ii=0; ii<num_views; ii++ )
		{
			this.row_id_map[ii][i][2] = this.row_id_map[ii][i][2] | ac.chap.ROWSTATE_SELECTION;
			this.row_id_map[ii][i][5][0] = 0;
			this.row_id_map[ii][i][5][1] = this.char_map[i].length;
		}
	}
	this.selection = 
	{
		startPosition: [0, 0],
		endPosition: [num_rows-1, this.char_map[num_rows-1].length]
	}
	// var me = this;
	// $runafter(300, function()
	// {
	// 	ac.chap.nodeClipboard.$.value = me.getSelection();
	// 	delete me;
	// });
}

ac.chap.Window.prototype.addSelection = function(range_to, range_from)
{
	// console.log('Adding selection: [%i, %i]', range_to, range_from);
	var num_views = this.views.length;
	if ( null == this.selection )
	{
		// no previous selection
		range_from = range_from || range_to;		
		this.selection = {};
		this.selection.startPosition = [range_from[0], range_from[1]];
	}
	else
	{
		var start_offset = Math.min(this.selection.startPosition[0], this.selection.endPosition[0]);
		var end_offset = Math.max(this.selection.startPosition[0], this.selection.endPosition[0]);
		for ( var i=start_offset; i<=end_offset; i++ )
		{
			for ( var ii=0; ii<num_views; ii++ )
			{
				this.row_id_map[ii][i][2] = (this.row_id_map[ii][i][2] & (65535-ac.chap.ROWSTATE_SELECTION));
			}
		}
		range_from = [this.selection.startPosition[0], this.selection.startPosition[1]];
	}
	if ( (range_to[0] < range_from[0]) || (range_to[0] == range_from[0] && range_to[1] < range_from[1]) )
	{
		range_from[1]--;
	}
	else
	{
		range_to[1]--;		
	}
	this.selection.endPosition = [range_to[0], range_to[1]];
	if ( (range_to[0] < range_from[0]) || (range_to[0] == range_from[0] && range_to[1] < range_from[1]) )
	{
		var r = range_from;
		range_from = range_to;
		range_to = r;
	}
	// console.log('%o - %o', range_from, range_to);
	for ( var i=0; i<num_views; i++ )
	{
		for ( var ii=range_from[0]; ii<=range_to[0]; ii++ )
		{
//			this.row_id_map[i][ii][1] = false;
			this.row_id_map[i][ii][2] = ac.chap.ROWSTATE_SELECTION;
			var range = [0, this.char_map[ii].length];
			if ( range_from[0] == ii )
			{
				range[0] = range_from[1];
			}
			if ( range_to[0] == ii )
			{
				range[1] = range_to[1];
			}
			this.row_id_map[i][ii][5][0] = range[0];
			this.row_id_map[i][ii][5][1] = range[1];
		}
	}
	// console.log('SELECTION ranges: %o - %o', this.selection.startPosition, this.selection.endPosition);
	// console.log('CARET: %o', this.caret.position);
}

ac.chap.Window.prototype.removeSelection = function(rowIndex, colIndex)
{
	var num_views = this.views.length;
	var num_rows = this.char_map.length;
	var changed = false;
	for ( var i=0; i<num_views; i++ )
	{
		for ( var ii=0; ii<num_rows; ii++ )
		{
			var row_state = this.row_id_map[i][ii][2];
			if ( ac.chap.ROWSTATE_SELECTION == (row_state & ac.chap.ROWSTATE_SELECTION) )
			{
				this.row_id_map[i][ii][1] = false;
				this.row_id_map[i][ii][2] = row_state & (65535-ac.chap.ROWSTATE_SELECTION);
				this.row_id_map[i][ii][5][0] = null;
				this.row_id_map[i][ii][5][1] = null;
				changed = true;
			}
		}
	}
	this.selection = null;
	return changed;
}

ac.chap.Window.prototype.getSelection = function()
{
	var selection_text = '';
	if ( null != this.selection )
	{
		var range_from = [this.selection.startPosition[0], this.selection.startPosition[1]];
		var range_to = [this.selection.endPosition[0], this.selection.endPosition[1]];
		if ( (range_to[0] < range_from[0]) || (range_to[0] == range_from[0] && range_to[1] < range_from[1]) )
		{
			var r = range_from;
			range_from = range_to;
			range_to = r;			
		}
		if ( range_from[0] == range_to[0] )
		{
			selection_text = this.char_map[range_from[0]].substring(range_from[1], range_to[1]+1);
		}
		else
		{
			selection_text = this.char_map[range_from[0]].substr(range_from[1]);
			selection_text = [].concat(selection_text, this.char_map.slice(range_from[0]+1, range_to[0]), this.char_map[range_to[0]].substr(0, range_to[1]+1)).join('\n');
		}
		// console.log('SELECTION: `%s`', selection_text.replace(/\n/g, '$'));
	}
	return selection_text;	
}

ac.chap.Window.prototype.getCaretPosition = function()
{
	return [this.caret.position[0], this.caret.position[1]];
}

ac.chap.Window.prototype.setCaretPosition = function(row, column)
{
	this.caret.position[0] = parseInt(row);
	this.caret.position[1] = parseInt(column);
}

ac.chap.Window.prototype.renderText = function(forceCompleteRedraw)
{
	var num_views = this.views.length;
	for ( var i=0; i<num_views; i++ )
	{
		this.views[i].renderText(forceCompleteRedraw);
	}
}

ac.chap.Window.prototype.renderSelection = function()
{
	var num_views = this.views.length;
	for ( var i=0; i<num_views; i++ )
	{
		this.views[i].renderSelection();
	}
}

ac.chap.Window.prototype.showCaret = function(skipScroll, whenAnimating)
{
	if (new Date().getTime() - 500 < this.state.lastKeyTimePressed)
	{
		this.state.caretPhase = 1;
	}
	var num_views = this.views.length;
	for ( var i=0; i<num_views; i++ )
	{
		if ( this.activeView == this.views[i] && null == this.selection )
		{
			this.views[i].showCaret(skipScroll?true:false);
			if (null != this.state.caretListener && !whenAnimating)
			{
				// this.state.caretListener(this.caret.position[0], this.caret.position[1]);
				var listener = this.state.caretListener;
				var r = this.caret.position[0];
				var c = this.caret.position[1];
				$runafter(30, function()
				{
					listener(r, c);
					delete listener;
				});
			}
		}
		else
		{
			this.views[i].hideCaret();
		}
	}
	this.state.caretPhase = ++this.state.caretPhase & 1;
}

ac.chap.Window.prototype.hideCaret = function()
{
	var num_views = this.views.length;
	for ( var i=0; i<num_views; i++ )
	{
		this.views[i].hideCaret();
	}
}

ac.chap.Window.prototype.captureEditAreaClick = function(evt, view)
{
	evt.stop();
	this.hideInteractiveSearch();
	this.activeView = view;
	
	var pos = evt.$.abspos();
	var offset_x = evt.pageX - pos.x;
	var offset_y = evt.pageY - pos.y + ($__tune.isGecko ? view.nodeScrollArea.$.scrollTop : 0);
	var target  = evt.$.$;
	var used = false;
	while ( null != target && target.tagName && 'pre' != target.tagName.toLowerCase() )
	{
		if ( !$__tune.isOpera )
		{
			offset_x += target.offsetLeft;
			offset_y += target.offsetTop;
			used = true;
		}
		target = target.parentNode;
	}
	var row_index = this.char_map.length-1;
	if ( target.tagName && used )
	{
		offset_y -= target.offsetTop;
	}
	if ( null == target )
	{
		return;
	}
	
	var row_index = target.getAttribute ? parseInt(target.getAttribute('row-index')) : row_index;
	var num_subrows = 1;
	var col_index = 0;
	if ( view.options.wordWrap )
	{
		num_subrows = 1 + Math.floor(offset_y/view.options.rowHeight);
//		console.log(num_subrows);
	}
	var i = 0;
	var num_chars = this.char_map[row_index].length;
	var mid_char_w = view.getRenderedCharDimension()[0] / 2;
	var subrow = 0;
	var subrow_offset = 0;
//	offset_y -=
//	console.log('offsets [%s x %s]', offset_x, offset_y);
	var w = view.options.colWidth * view.numCols;
	while ( i<num_chars )
	{
		var dim = view.getRenderedStringDimension(row_index, 0, i);
		if ( (Math.floor(dim[0]/w) + 1) == num_subrows )
		{
			if ( dim[0] % w > offset_x - mid_char_w )
			{
				col_index = i;
				break;
			}
			else if ( w - mid_char_w < offset_x && (dim[0] % w + 2*mid_char_w >= offset_x))
			{
				// last char
				col_index = i+1;
				break;
			}			
		}
		i++;
	}
//	console.log('%s, %s', row_index, col_index);
	if ( i == num_chars )
	{
		col_index = i;
	}
//	console.log('CHANGE CARET to: %s', col_index);
	this.hideCaret();
	if ( evt.shiftKey )
	{
		this.addSelection([row_index, col_index], this.state.lastCaretPosition);
		this.renderText();
	}
	else
	{
		this.setCaretPosition(row_index, col_index);
		this.state.caretPhase = 1;
		view.showCaret();
		this.state.lastCaretPosition = [this.caret.position[0], this.caret.position[1]];
		if ( this.removeSelection() )
		{
			this.renderText();
		}
	}
	ac.chap.setActiveComponent(this);
}

ac.chap.Window.prototype.foldingize = function()
{
	var startRowIndex = 0;

	var source_rows = this.char_map.slice(startRowIndex);

	// creating folding info
	var n = source_rows.length;
	var foldings = [];
	var foldings_index = -1;
	for ( var i=0; i<this.language.foldingStartMarkers.length; i++ )
	{
		var re_start = this.language.foldingStartMarkers[i];
		var re_parity = this.language.foldingParityMarkers[i];
		var re_stop = this.language.foldingStopMarkers[i];


		for ( var ii=startRowIndex; ii<n; ii++ )
		{
			if ( re_start.test(this.char_map[ii]) )
			{
//				console.log('START: #%s', ii);
				foldings.push([ii, -1, 0]);
				foldings_index = foldings.length-1;
			}

			if ( null != re_parity && re_parity.exec(this.char_map[ii]) )
			{
//				console.log('PARITY: #%s', ii);
				var ix = foldings_index;
				while ( 0 <= ix )
				{
					if ( -1 == foldings[ix][1] )
					{
						foldings[ix][2]++;
						break;
					}
					ix--;
				}
//				foldings[foldings_index][2]++;
			}

			if ( re_stop.exec(this.char_map[ii]) )
			{
//				console.log('STOP: #%s', ii);
				var ix = foldings_index;
				while ( 0 <= ix )
				{
					if ( -1 == foldings[ix][1] )
					{
						foldings[ix][2]--;
						if ( 0 == foldings[ix][2] )
						{
							foldings[ix][1] = ii;							
						}
						break;
					}
					ix--;
				}
			}
		}
	}

//	console.log('%o', foldings);
	n = foldings.length;
	for ( i=0; i<n; i++ )
	{
		var fold = foldings[i];
		if ( fold[0] == fold[1] || -1 == fold[1] )
		{
			continue;
		}
		for ( var ii=0; ii<this.views.length; ii++ )
		{
			this.row_id_map[ii][fold[0]][2] |= ac.chap.ROWSTATE_FOLD_START;
			this.row_id_map[ii][fold[0]][3][0] = 0;
			this.row_id_map[ii][fold[0]][3][1] = fold[1];
			this.row_id_map[ii][fold[1]][2] |= ac.chap.ROWSTATE_FOLD_STOP;
			this.row_id_map[ii][fold[1]][3][0] = 0
			this.row_id_map[ii][fold[1]][3][1] = fold[0];
		}
	}	
}

ac.chap.Window.prototype.tokenize = function()
{
	if ( !this.options.syntaxHighlightingEnabled )
	{
		return;
	}
	var startRowIndex = 0;
	this.foldingize();
	var source = this.char_map.slice(startRowIndex).join('\n');

	var total_rows = this.char_map.length;
	var syntax_map = [];

	var ml_start = this.language.multiRowCommentStartMarker;
	var ml_end = this.language.multiRowCommentEndMarker;
//	console.log(ml_end);
	var sq = this.language.singleQuoteStringMarker;	
	var sq_exception = this.language.singleQuoteStringMarkerException;
	var dq = this.language.doubleQuoteStringMarker;
	var dq_exception = this.language.doubleQuoteStringMarkerException;
	var sl_markers = this.language.singleRowCommentStartMarkers;
	
	var cursor = {row:startRowIndex, col:0};
	var col_offset = 0;
	
	var fillRowTokens = function(tokenType, fromRowIndex, toRowIndex, pars)
	{
		pars = pars || '';
		if ( -1 == toRowIndex )
		{
			toRowIndex = total_rows;
		}
		for ( var i=fromRowIndex; i<toRowIndex; i++ )
		{
			if ( 'undefined' == typeof syntax_map[i] )
			{
				syntax_map[i] = [];
			}
			syntax_map[i] = [[tokenType, -1, -1, pars]];
		}
	}
	var ixs = [
		[ac.chap.TOKEN_MULTIROW_COMMENT, -1, ml_start, ml_end, ''],
		[ac.chap.TOKEN_SINGLE_QUOTED, -1, sq, sq, sq_exception],
		[ac.chap.TOKEN_DOUBLE_QUOTED, -1, dq, dq, dq_exception]
	];
	for ( i=0; i<sl_markers.length; i++ )
	{
		ixs.push([ac.chap.TOKEN_SINGLEROW_COMMENT, -1, sl_markers[i], '\n', '']);
	}

	while ( true )
	{
		if ( '' != ml_start )
		{
			ixs[0][1] = source.indexOf(ml_start);
		}
		if ( '' != sq )
		{
			ixs[1][1] = source.indexOf(sq);
		}
		if ( '' != dq )
		{
			ixs[2][1] = source.indexOf(dq);
		}
		for ( i=0; i<sl_markers.length; i++ )
		{
			if ( '' != sl_markers[i] )
			{
				ixs[3+i][1] = source.indexOf(sl_markers[i]);
			}
		}
		var found_marker_index = -1;
		var lowest = source.length;
		for ( i=0; i<ixs.length; i++ )
		{
			if ( -1 != ixs[i][1] )
			{
				if ( lowest > ixs[i][1] )
				{
					found_marker_index = i;
					lowest = ixs[i][1];
				}
			}
		}
		if ( -1 == found_marker_index )
		{
			break;
		}
		var start_index = ixs[found_marker_index][1];
		var skipped_source = source.substr(0, start_index);
		var num_skipped_rows = skipped_source.split('\n').length;
		cursor.row += num_skipped_rows - 1;
		cursor.col = (1 == num_skipped_rows ? col_offset : 0) + skipped_source.length - ('\n'+skipped_source).lastIndexOf('\n');
		
		if ( 'undefined' == typeof syntax_map[cursor.row] )
		{
			syntax_map[cursor.row] = [];
		}
		
		var start_marker_len = ixs[found_marker_index][2].length;
		var end_marker_len = ixs[found_marker_index][3].length;
		source = source.substr(start_index+start_marker_len);

		var token_type = ixs[found_marker_index][0];
		
		var end_index = source.indexOf(ixs[found_marker_index][3]);
		var sub_source = source;
		var end_index_offset = 0;
		var except = false;
		while ( 0 < end_index && '' != ixs[found_marker_index][4] && ixs[found_marker_index][4] == sub_source.charAt(end_index-end_marker_len) )
		{
			except = true;
			end_index_offset += end_index + end_marker_len;
			sub_source = sub_source.substr(end_index+end_marker_len);
			end_index = sub_source.indexOf(ixs[found_marker_index][3]);
		}
		if ( except && -1 != end_index )
		{
			end_index += end_index_offset;
		}
		if ( -1 == end_index )
		{
			syntax_map[cursor.row].push([token_type, cursor.col, -1, '']);
			fillRowTokens(token_type, cursor.row+1, -1);
			break;
		}
		else
		{
			var block_source = source.substr(0, end_index);
			var num_block_rows = '\n' == ixs[found_marker_index][3] ? 1 : block_source.split('\n').length;
			var cursor_col_end = block_source.length - ('\n'+block_source).lastIndexOf('\n');

			syntax_map[cursor.row].push([token_type, cursor.col, 1 == num_block_rows ? (cursor.col+end_index+start_marker_len+end_marker_len) : -1, ixs[found_marker_index][2]]);
			fillRowTokens(token_type, cursor.row+1, cursor.row+num_block_rows-1);
			if ( 1 == num_block_rows )
			{
			    col_offset = cursor.col + end_index + start_marker_len + end_marker_len;
				if ( '\n' == ixs[found_marker_index][3] )
				{
					cursor.row++;
					col_offset = 0;
				}
			}
			else
			{
				if ( 'undefined' == typeof syntax_map[cursor.row+num_block_rows] )
				{
					syntax_map[cursor.row+num_block_rows-1] = [];
				}
				syntax_map[cursor.row+num_block_rows-1].push([token_type, -1, cursor_col_end + end_marker_len, '']);
//				var a = block_source.split('\n');
				col_offset = cursor_col_end + end_marker_len;
				cursor.row += num_block_rows -1;
			}
//			console.log(num_block_rows);
			source = source.substr(end_index+end_marker_len);
		}
	}
	delete ixs;
	delete source;

	var n = Math.max(syntax_map.length, this.syntax_map.length);
	for ( i=0; i<n; i++ )
	{
		if ( 'undefined' != typeof syntax_map[i] )
		{
			if ( 'undefined' != typeof this.syntax_map[i] )
			{
				// looking for change
				if ( syntax_map[i].length == this.syntax_map[i].length )
				{
					var changed = false;
					for ( var ii=0; ii<syntax_map[i].length; ii++ )
					{
						if ( syntax_map[i][ii].length != this.syntax_map[i][ii].length )
						{
							changed = true;
							break;
						}
						if ( syntax_map[i][ii][0] != this.syntax_map[i][ii][0] || syntax_map[i][ii][1] != this.syntax_map[i][ii][1] || syntax_map[i][ii][2] != this.syntax_map[i][ii][2] || syntax_map[i][ii][3] != this.syntax_map[i][ii][3] )
						{
							changed = true;
							break;
						}
					}
					if ( !changed )
					{
						continue;
					}
				}
			}
			this.syntax_map[i] = syntax_map[i];
		}
		else
		{
			if ( 'undefined' != typeof this.syntax_map[i] )
			{
				delete this.syntax_map[i];
			}
			else
			{
				// no change
				continue;
			}
		}
		for ( var ii=0; ii<this.views.length; ii++ )
		{
			// marking row as changed
			if (this.row_id_map[ii] && this.row_id_map[ii][i])
			{
				this.row_id_map[ii][i][1] = false;
			}
		}
		// console.log('%s marked as changed.', i);
	}
	
	delete syntax_map;
	delete fillRowTokens;
}

ac.chap.Window.prototype.expandFolding = function(rowIndex)
{
	var n = this.views.length;
	for ( var i=0; i<n; i++ )
	{
		this.views[i].expandFolding(rowIndex);
	}
}

ac.chap.Window.prototype.insertIntoCharacterMap = function(source, atRow, atColumn, skipLog, userId)
{
	if ( $notset(atRow) )
	{
		atRow = this.caret.position[0];
	}
	if ( $notset(atColumn) )
	{
		atColumn = this.caret.position[1];
	}
	userId = userId|this.userId;

	if ( !skipLog && !this.state.transactionLogStopped )
	{
		this.transaction_log.push(ac.chap.TRANSLOG_TYPE_INSERT);
		this.transaction_log.push([atRow, atColumn, userId]);
		this.transaction_log.push(source);
	}
	
	var num_existing_rows = this.char_map.length;
	var new_rows = source.split('\n');
	var num_new_rows = new_rows.length;
	var num_views = this.views.length;
//	console.log('NUMVIEWS: %s', num_views);
    if ( this.hasTransactionListener() )
    {
        var me = this;
        setTimeout(function()
        {
            me.state.transactionListener[0](me, ac.chap.TRANSLOG_TYPE_INSERT, userId, atRow, atColumn, num_existing_rows, num_new_rows, source);
            me = null;
        }, this.state.transactionListener[1]);
    }
	
	var i = ii = 0;
	
	if ( 'undefined' == typeof this.char_map[atRow] )
	{
		this.char_map = this.char_map.concat(new_rows);
		for ( i=0; i<num_new_rows; i++ )
		{
			for ( ii=0; ii<num_views; ii++ )
			{
				this.row_id_map[ii][atRow+i] = [this.row_id_sequence, false, ac.chap.ROWSTATE_NONE, [], [], []];
			}
			this.row_id_sequence++;
		}
	}
	else
	{
		if ( this.char_map[atRow].length < atColumn )
		{
			atColumn = this.char_map[atRow].length;
		}
		for ( i=0; i<num_views; i++ )
		{
			this.row_id_map[i][atRow][1] = false;
		}
		if ( 1 == num_new_rows )
		{
			this.char_map[atRow] = this.char_map[atRow].substr(0, atColumn) + new_rows[0] + this.char_map[atRow].substr(atColumn);
		}
		else
		{
			var end_snippet = this.char_map[atRow].substr(atColumn);
			// console.log('end snippet: `%s`', end_snippet);
			this.char_map[atRow] = this.char_map[atRow].substr(0, atColumn) + new_rows[0];
			var last_row_index = atRow + (num_new_rows-1);
			this.char_map = [].concat(this.char_map.slice(0, atRow+1), new_rows.slice(1), this.char_map.slice(atRow+1));
			var ins_map = [];
			var start_sequence = this.row_id_sequence;
			for ( i=0; i<num_views; i++ )
			{
				ins_map[i] = [];
				start_sequence = this.row_id_sequence;
				for ( ii=1; ii<num_new_rows; ii++ )
				{
					ins_map[i][ii-1] = [start_sequence++, false, ac.chap.ROWSTATE_NONE, [], [], []];
				}
			}
			this.row_id_sequence = start_sequence;
			for ( i=0; i<num_views; i++ )
			{			
				this.row_id_map[i] = [].concat(this.row_id_map[i].slice(0, atRow+1), ins_map[i], this.row_id_map[i].slice(atRow+1));
			}
			this.char_map[last_row_index] += end_snippet;
			for ( i=0; i<num_views; i++ )
			{
				this.row_id_map[i][last_row_index][1] = false;	
			}
		}
	}
	// console.log('%o', this.char_map);
	if ( 1 < num_new_rows )
	{
		for ( i=0; i<num_views; i++ )
		{
			this.views[i].numVisibleRows += (num_new_rows-1);
		}		
	}
}

ac.chap.Window.prototype.removeFromCharacterMap = function(startRow, startCol, endRow, endCol, skipLog, userId)
{
	if ( 'undefined' == typeof endRow )
	{
		endRow = startRow;
		endCol = startCol+1;
	}
	userId = userId|this.userId;

	var source = '';
	var i = 0;
	var num_views = this.views.length;
	if ( startRow == endRow )
	{
		source = this.char_map[startRow].substring(startCol, endCol);
		this.char_map[startRow] = this.char_map[startRow].substr(0, startCol)+this.char_map[startRow].substr(endCol);
		for ( i=0; i<num_views; i++ )
		{			
			this.row_id_map[i][startRow][1] = false;
		}
	}
	else
	{
		source = this.char_map[startRow].substr(startCol) + '\n'+this.char_map.slice(startRow+1, endRow).join('\n') + '\n' + this.char_map[endRow].substr(0, endCol);

		this.char_map[startRow] = this.char_map[startRow].substr(0, startCol)+this.char_map[endRow].substr(endCol);
		this.char_map = [].concat(this.char_map.slice(0, startRow+1), this.char_map.slice(endRow+1));
		for ( i=0; i<num_views; i++ )
		{
			this.row_id_map[i][startRow][1] = false;
			this.row_id_map[i] = [].concat(this.row_id_map[i].slice(0, startRow), this.row_id_map[i].slice(endRow));
			if ( startRow < this.row_id_map[i].length-1 )
			{
				this.row_id_map[i][startRow+1][1] = false;
			}
			this.views[i].numVisibleRows -= (endRow-startRow);
		}
	}
	if ( !skipLog && !this.state.transactionLogStopped )
	{
		this.transaction_log.push(ac.chap.TRANSLOG_TYPE_REMOVE);
		this.transaction_log.push([startRow, startCol, endRow, endCol, userId|this.userId]);
		this.transaction_log.push(source);
	}
    if ( this.hasTransactionListener() )
    {
        var me = this;
        setTimeout(function()
        {
            me.state.transactionListener[0](me, ac.chap.TRANSLOG_TYPE_REMOVE, userId, startRow, startCol, endRow, endCol, source);
            me = null;
        }, this.state.transactionListener[1]);
    }
	return source;
}



/*
 * ac.Chap - Text Editing Component - Views
 */

if ( 'undefined' == typeof ac )
{
	var ac = {chap:{}};
}


$class('ac.chap.View',
{
	construct:function(window, index, options)
	{
		this.window = window;
		this.index = index;

		this.nodeScrollArea = null;
		this.nodeFillArea = null;
		this.nodeEditArea = null;
		this.nodeEditAreaCache = null;
		this.nodeCaret = null;
		this.nodeCaretRow = null;
		
		this.renderingRunning = false;
		
		this.numRows = 0;
		this.numCols = 0;
		this.wrapWidth = 0;
		this.wrapHeight = 0;

		this.startRow = 0;
		this.startCol = 0;
		
		this.startRowOffset = 0;
		this.numVisibleRows = 0;
		
		this.state = {lastCaretPosition:[-1,-1], lastCaretRenderedPosition:null};
		
		this.theme = null;
		
		this.setOptions(options);
	},
	destruct:function()
	{
		clearInterval(this.caretAnimInterval);
		$delete(this.options);
		$delete(this.theme);
	}
});

ac.chap.View.prototype.setOptions = function(options)
{
	this.options = 
	{
		tabelator:'  ',
		wordWrap:false,
		colWidth:0,
		rowHeight:0,
		caretThreadTimeout:450
	}
	if ( $isset(options.wordWrap) )
	{
		this.options.wordWrap = options.wordWrap;
	}
	if ( $isset(options.tabelator) )
	{
		this.options.tabelator = options.tabelator;
	}
	// getting column width and height
	this.calculateColRowDim();
	if ($isset(options.theme))
	{
		this.theme = $new(options.theme);
	}
	else
	{
		this.theme = $new(ac.chap.Theme);
	}
}

ac.chap.View.prototype.calculateColRowDim = function()
{
	var font_size = this.window.options.font.size;
	var node = $().a($$('span')).s('font:?px ?'.embed(font_size, this.window.options.font.family)).t('a');
	this.options.colWidth = node.$.offsetWidth;
	node.rs();
	this.options.rowHeight = font_size + Math.ceil(font_size/10);
	var row_node = document.createElement('pre');
	row_node.style.minHeight = this.options.rowHeight+'px';
	row_node.style.font = this.window.options.font.size + 'px ' + this.window.options.font.family;
	row_node.style.lineHeight = this.options.rowHeight + 'px';
	row_node.style.margin = 0;
	row_node.style.padding = 0;
	row_node.style.border = 0;
	this.options.rowTemplate = row_node;
}

ac.chap.View.prototype.setTheme = function(theme)
{
	this.theme = $new(theme);
	this.nodeRoot.s('background:?'.embed(this.theme.background));
	this.nodeScrollArea.fc().s('background:?'.embed(this.theme.background));
	$(this.nodeEditArea).s('color:?'.embed(this.theme.textColor));
	this.renderText(true);
}

ac.chap.View.prototype.getSyntaxHighlightingSource = function()
{
	function get_inner(node)
	{
		var ht = '';
		var child_nodes = node.childNodes;
		for (var i=0; i<child_nodes.length; i++)
		{
			var inner_node = child_nodes.item(i);
			if (3 == inner_node.nodeType)
			{
				ht += inner_node.data;
			}
			else if(1 == inner_node.nodeType)
			{
				ht += '<span style="color:?;background:?;font-style:?;font-weight:?;text-decoration:?;">'.embed(inner_node.style.color, inner_node.style.background, inner_node.style.fontStyle, inner_node.style.fontWeight, inner_node.style.textDecoration) + get_inner(inner_node) + '</span>';
			}
		}
		return ht;
	}
	var nodes = this.nodeEditArea.childNodes;
	var ht = '';
	for (var i=0; i<nodes.length; i++)
	{
		var pre = nodes.item(i);
		if (1 != pre.nodeType && 'pre' != node.tagName.toLowerCase())
		{
			continue;
		}
		ht += '<pre style="min-height=?">?</pre>'.embed(pre.style.minHeight, get_inner(pre));
	}
	return ht;
}

function ch_encode_markup(str)
{
    if ( -1 != str.indexOf('&') )
    {
        str = str.replace(/&/g, '&amp;');
    }
    if ( -1 != str.indexOf('>') )
    {
        str = str.replace(/>/g, '&gt;');
    }
    if ( -1 != str.indexOf('<') )
    {
        str = str.replace( /</g, '&lt;' );
    }
    /*
    if ( -1 != str.indexOf(' ') )
    {
       str = str.replace(/ /g, '&nbsp;');
    }
    */
    return str;
}

// replaces all spaces EXCEPT for those existing in inside tag definitions to &nbsp; Eg. <a href="dsds"> 1 2 3</a> = <a href="dsds">&nbsp;1&nbsp;2&nbsp;3</a>
function ch_encode_markup_spaces(str)
{
	var n = str.length - str.replace(/ /g, '').length;
	for ( var i=0; i<n; i++ )
	{
		str = str.replace(/([^ ]*) /i, function()
		{
			var is_inside = -1 != arguments[1].indexOf('<');
			is_inside = is_inside && (arguments[1].replace(/</g, '').length != arguments[1].replace(/>/g, '').length);
			return arguments[1]+(is_inside?'~`~`~`~`':'&nbsp;');
		});		
	}
	return str.replace(/~`~`~`~`/g, ' ');
}


ac.chap.View.prototype.getRenderedCharDimension = function(rowIndex, colIndex)
{
	return [this.options.colWidth, this.options.rowHeight];
}

ac.chap.View.prototype.getRenderedStringDimension = function(rowIndex, colIndex, width)
{
	if ( 'undefined' != typeof this.window.char_map[rowIndex] )
	{
		if ( colIndex < this.window.char_map[rowIndex].length )
		{
			var str = this.window.char_map[rowIndex].substr(colIndex, width);
			var ix = 0;
			var tab = this.options.tabelator;
			while ( -1 != ix )
			{
				ix = str.indexOf('\t');
				if ( -1 != ix )
				{
					str = str.substr(0,ix)+tab.substr(0, tab.length-(ix % tab.length))+str.substr(ix+1);
				}
			}
//			console.log('(getrenderedstringdimension) = [%s], ix:%s w:%s %s', this.options.colWidth*str.length, colIndex, width, str);
			return [this.options.colWidth*str.length, this.options.rowHeight];
		}
	}
	return [0,0];
}

ac.chap.View.prototype.getVirtualStringDimension = function(row, colIndex, width)
{
	if ( colIndex < row.length )
	{
		var str = row.substr(colIndex, width);
		var ix = 0;
		var tab = this.options.tabelator;
		while ( -1 != ix )
		{
			ix = str.indexOf('\t');
			if ( -1 != ix )
			{
				str = str.substr(0,ix)+tab.substr(0, tab.length-(ix % tab.length))+str.substr(ix+1);
			}
		}
//		console.log('(getrenderedstringdimension) = [%s], ix:%s w:%s %s', this.options.colWidth*str.length, colIndex, width, str);
		return [this.options.colWidth*str.length, this.options.rowHeight];
	}
	return [0,0];
}

ac.chap.View.prototype.getRenderedCharPosition = function(rowIndex, colIndex)
{
	var node_row = this.getRowNode(rowIndex);
	if ( null != node_row && null != node_row.parentNode )
	{
		var offset_x = this.getRenderedStringDimension(rowIndex, 0, colIndex)[0];
		var offset_y = 0;
		var dim = this.getRenderedCharDimension(rowIndex, colIndex);
		offset_x -= dim[0];
		if ( this.options.wordWrap )
		{
			if ( 0 < colIndex )
			{
				var w = this.options.colWidth * (this.numCols);
				offset_y = this.options.rowHeight * (Math.floor(offset_x/w));
				offset_x = (offset_x) % w;
			}
		}
		return [offset_x, node_row.offsetTop+offset_y, node_row];
	}
	return null;
}

ac.chap.View.prototype.getRowNode = function(rowIndex)
{
	return document.getElementById('row-'+this.window.instanceId+'-'+this.index+'-'+rowIndex);
}

ac.chap.View.prototype.getVirtualCharPosition = function(nodeRow, row, colIndex)
{
	var offset_x = this.getVirtualStringDimension(row, 0, colIndex)[0];
	var offset_y = 0;
	var dim = this.getRenderedCharDimension(0, colIndex);
	offset_x -= dim[0];
	if ( this.options.wordWrap )
	{
		if ( 0 < colIndex )
		{
			var w = this.options.colWidth * (this.numCols);
			offset_y = this.options.rowHeight * (Math.floor(offset_x/w));
			offset_x = (offset_x) % w;
		}
	}
	return [offset_x, nodeRow.offsetTop+offset_y];
}

ac.chap.View.prototype.showCaret = function(skipScroll)
{
	var caret_row = this.window.caret.position[0];
	var caret_col = this.window.caret.position[1];
	
	pos = this.getRenderedCharPosition(caret_row, caret_col);
	if ( null != pos )
	{
		// caret is visible
		var node_row = pos[2];
		var node = document.getElementById('ac-chap-caret-'+this.window.instanceId);
		if ( null != node )
		{
			node.parentNode.removeChild(node);
		}
		if ( 1 == this.window.state.caretPhase )
		{
			// displaying caret
			node = document.createElement('div');
			node.id = 'ac-chap-caret-'+this.window.instanceId;
			node.style.position = 'absolute';
			node.style.font = '1px arial'; // IE
			node.style.width = this.options.colWidth + 'px';
			node.style.height = this.options.rowHeight + 'px';
			pos[2] = this.options.colWidth;
			pos[3] = this.options.rowHeight;
			pos = this.theme.adjustCaretPosition(this.window.caret.mode, pos);
			node.style.left = pos[0]+'px';
			node.style.top = pos[1]+'px';
			this.theme.renderCaret(this.window.caret.mode, node);
			this.nodeCaret = node_row.appendChild(node);
			node_row.style.background = this.theme.caretRowStyleActive;
			
			if ( !skipScroll )
			{
				// might be out of borders, at least partially
				if ( 0 > node_row.offsetTop - (this.nodeScrollArea.$.scrollTop % this.options.rowHeight) )
				{
					// top margin overlay, first rendered row is partially hidden
					this.scrollToRow(caret_row);
				}
				else if ( node_row.offsetTop > this.options.rowHeight*(this.numRows-1)-$__tune.ui.scrollbarWidth )
				{
					// bottom margin overlay
					this.scrollToRow(caret_row-Math.floor(this.numRows/2));
				}
			}
			this.nodeCaretRow = node_row;
		}
		if ('undefined' != typeof this.state.lastCaretRowIndex && this.state.lastCaretRowIndex != caret_row)
		{
			var last_node_row = this.getRowNode(this.state.lastCaretRowIndex);
			if (last_node_row)
			{
				last_node_row.style.background = 'transparent';
			}
		}
		this.state.lastCaretRowIndex = caret_row;
	}
	else
	{
		if ( !skipScroll )
		{
			// scrolling into view
			this.scrollToRow(caret_row - Math.floor(this.numRows/2));			
		}
	}
}

ac.chap.View.prototype.hideCaret = function(skipCaretRow)
{
	if ( null != this.nodeCaret && null != this.nodeCaret.parentNode )
	{
		this.nodeCaret.parentNode.removeChild(this.nodeCaret);
		this.nodeCaret = null;
	}
	if ( !skipCaretRow && null != this.nodeCaretRow )
	{
//		console.log('off(hide) caret line background for %s', this.nodeCaretRow.id);
		this.nodeCaretRow.style.background = 'transparent';
	}
//	console.log('hide caret');
}

ac.chap.View.prototype.scrollToRow = function(rowIndex, setCaretToo, dontRefreshCaret)
{
	this.nodeScrollArea.$.scrollTop = this.options.rowHeight * rowIndex - Math.floor(this.nodeRoot.$.offsetHeight/3);
	if (setCaretToo)
	{
		this.window.runAction(ac.chap.ACTION_CARET, {moveTo:[rowIndex, 0]});
		this.window.runAction(ac.chap.ACTION_CARET, {move:'row_end'});
	}
	if (!dontRefreshCaret)
	{
		this.window.state.caretPhase = 1;
		this.showCaret(true);
	}
}

ac.chap.View.prototype.expandFolding = function(rowIndex)
{
	if ( 'undefined' == typeof this.window.row_id_map[this.index][rowIndex] )
	{
		return;
	}
	var row_state = this.window.row_id_map[this.index][rowIndex][2];
	if (0 == (ac.chap.ROWSTATE_FOLD_EXPAND & row_state))
	{
		return;
	}
	var end_row_index = this.window.row_id_map[this.index][rowIndex][3][1];
	this.window.row_id_map[this.index][rowIndex][2] &= (65535 - ac.chap.ROWSTATE_FOLD_EXPAND);
	this.window.row_id_map[this.index][rowIndex][1] = false;
	for ( var i=rowIndex+1; i<=end_row_index; i++ )
	{
		this.window.row_id_map[this.index][i][1] = false;
		this.window.row_id_map[this.index][i][2] &= (65535 - ac.chap.ROWSTATE_FOLD_COLLAPSED);
	}
	this.recalculateVisibleRows();
	var me = this;
	// console.log('expanding: %i, start: %i', rowIndex, end_row_index);
	$runafter(40, function(){me.renderText(true)});
}

ac.chap.View.prototype.resize = function()
{
	var h = this.nodeRoot.p().h();
	this.nodeRoot.h(h);
	$(this.nodeSidebar).h(h);
	this.nodeScrollArea.h(h);
	this.nodeFillArea.h(h-$__tune.ui.scrollbarWidth);
	$(this.nodeSelectionArea).h(h-$__tune.ui.scrollbarWidth+this.options.rowHeight);
	this.recalculateNumRows();
	this.recalculateVisibleRows();
	this.renderText(true);
}

ac.chap.View.prototype.reloadOptions = function()
{
	this.calculateColRowDim();
	this.recalculateNumCols(false, true);
	this.recalculateNumRows();
	this.recalculateVisibleRows();
	this.renderSidebarStub();
	this.renderText(true);	
}

ac.chap.View.prototype.recalculateNumCols = function(node, withoutScrollbar)
{
	node = node || this.nodeRoot;
	var w = node.$.offsetWidth;
	if (withoutScrollbar)
	{
		w -= $__tune.ui.scrollbarWidth+61;
	}
	this.numCols = Math.floor(w/this.options.colWidth);
}

ac.chap.View.prototype.recalculateNumRows = function(node)
{
	node = node || this.nodeRoot;
	this.numRows = Math.floor(node.$.offsetHeight/this.options.rowHeight);
}

ac.chap.View.prototype.showInteractiveSearch = function()
{
	this.hideInteractiveSearch();
	var pos = this.nodeRoot.abspos();
	var node = $().a($$()).pos(true).x(pos.x+58).y(pos.y).z(2000).w(this.nodeRoot.w()-$__tune.ui.scrollbarWidth-61).h(24).o(0.8);
	node.s('background:#000;border:1px solid #777;border-top:0;');
	var search_key_id = 'is_key_?'.embed(this.window.ident);
	var ht = '<table align="right" cellpadding="0" cellspacing="0" style="height:24px"><tbody><tr><td width="96%" align="right" valign="middle" style="padding-right:20px;color:#fff"></td><td valign="middle" width="2%"><input type="text" onfocus="fry.keyboard.stop()" onblur="fry.keyboard.start()" id="' + search_key_id + '" style="height:12px;padding:1px;padding-left:3px;border:1px solid #777"/></td><td valign="middle"><img src="/mm/i/theme/apple/tabpane.button.close_invert.gif" width="14" height="14" title="Close" style="margin-left:4px;margin-right:4px"/></td></tr></tbody></table>';
	node.t(ht);
	var me = this;
	var status_node = node.g('td:0');
	var search_key_node = node.g('input:0');
	var original_caret_pos = [me.window.caret.position[0], me.window.caret.position[1]];
	var last_keyword = '';
	var selection = me.window.getSelection();
	search_key_node.e('keydown', function(evt)
	{
		evt.stopPropagation();
		if (40 == evt.keyCode)
		{
			me.window.runAction(ac.chap.ACTION_CUSTOM, {action:'SearchKeyword', direction:'down'});
			me.scrollToRow(me.window.caret.position[0], false, true);
			me.window.processActionResult(true, true);
			evt.preventDefault();
			return true;
		}
		else if (38 == evt.keyCode)
		{
			me.window.runAction(ac.chap.ACTION_CUSTOM, {action:'SearchKeyword', direction:'up'});
			me.scrollToRow(me.window.caret.position[0], false, true);
			me.window.processActionResult(true, true);
			evt.preventDefault();
			return true;
		}
		else if (27 == evt.keyCode)
		{
			finish(true);
			evt.preventDefault();
			return true;
		}
		else if (13 == evt.keyCode)
		{
			finish();
			evt.preventDefault();
			return true;
		}
	}).e('keyup', function(evt)
	{
		evt.stopPropagation();
		search();
		
	}).$.focus();
	node.g('img:0').e('click', function(evt)
	{
		evt.stopPropagation();
		finish(true);
	});
	
	function finish(canceled)
	{
		if (canceled)
		{
			me.window.removeSelection();
			me.window.runAction(ac.chap.ACTION_CARET, {moveTo:[original_caret_pos[0], original_caret_pos[1]]});
			me.scrollToRow(me.window.caret.position[0], false, true);
			me.window.processActionResult(true, true);
		}
		ac.chap.setActiveComponent(me.window);
		me.hideInteractiveSearch();
	}
	
	function update_status(numFound)
	{
		status_node.t('Found <strong>?</strong> results.'.embed(numFound));
	}
	
	function search()
	{
		var keyword = search_key_node.$.value.trim();
		if ('' == keyword || last_keyword == keyword)
		{
			if ('' == keyword)
			{
				update_status(0);
			}
			return;
		}
		update_status(me.window.getText().split(keyword).length - 1);
		last_keyword = keyword;
		me.window.removeSelection();
		me.window.runAction(ac.chap.ACTION_CARET, {moveTo:[original_caret_pos[0], original_caret_pos[1]]});
		me.window.runAction(ac.chap.ACTION_CUSTOM, {action:'SetSearchKeyword', keyword:keyword});
		me.window.runAction(ac.chap.ACTION_CUSTOM, {action:'SearchKeyword', direction:'down'});
		me.scrollToRow(me.window.caret.position[0], false, true);
		me.window.processActionResult(true, true);
	}	
	
	if (null != selection)
	{
		search_key_node.$.value = selection;
		search_key_node.$.select();
		search_key_node.$.focus();
		search();
	}

	
	
	this.interactiveSearchNode = node;
}

ac.chap.View.prototype.hideInteractiveSearch = function()
{
	if (this.interactiveSearchNode && this.interactiveSearchNode.is())
	{
		this.interactiveSearchNode.rs();
	}
}

ac.chap.View.prototype.render = function(node)
{
	var w = node.$.offsetWidth;
	var h = node.$.offsetHeight;
	this.recalculateNumRows(node);
	this.recalculateNumCols(node);
	node.sa('chap-view', 'true');
	var me = this;
	this.nodeRoot = node.a($$()).pos(true).w(w).h(h).n('acw-chap').s('background:?'.embed(this.theme.background));
	this.interactiveSearchNode = null;
	
	var w_rows = 58;
	w -= w_rows;
	this.nodeSidebar = this.nodeRoot.a($$()).pos(true).x(0).y(0).w(w_rows).h(h).s('overflow:hidden').n('sidebar');

	// rendering sidebar stub
	this.renderSidebarStub();


	this.nodeScrollArea = this.nodeRoot.a($$()).pos(true).x(w_rows).y(0).w(w).h(h).n('scroll-area').s('overflow:auto');
	this.nodeScrollArea.e('scroll', function(evt)
	{
		var offset = Math.floor(me.nodeScrollArea.$.scrollTop/me.options.rowHeight);
		var map = me.window.row_id_map[me.index];
		var row_index = 0;
		for ( var i=0; i<map.length; i++ )
		{
			if ( row_index == offset )
			{
				row_index = i;
				break;
			}
//			if ( ac.chap.ROWSTATE_FOLD_EXPAND == (ac.chap.ROWSTATE_FOLD_EXPAND & map[i][2]) )
			if ( ac.chap.ROWSTATE_FOLD_EXPAND == (ac.chap.ROWSTATE_FOLD_EXPAND & map[i][2]) )
			{
				i = map[i][3][3];
			}
			row_index++;
		}
//		console.log('OFFSET %s  ROWINDEX %s', offset, row_index);
		me.startRow = row_index;
		me.startRowOffset = offset;
		if ( me == me.window.activeView )
		{
			me.hideCaret();
		}
		me.renderText();
		if ( me == me.window.activeView && me.startRow < me.window.caret.position[0] )
		{
			if ( null == me.window.selection )
			{
				me.showCaret(true);					
			}
		}
	});

	h -= $__tune.ui.scrollbarWidth;
	w -= $__tune.ui.scrollbarWidth+3;

	this.wrapWidth = w;
	this.wrapHeight = h;
	this.numCols = Math.floor(w/this.options.colWidth);

	this.nodeFillArea = this.nodeScrollArea.a($$()).pos(true).x(3).y(0).h(h).w((this.options.wordWrap?w:2000)-3).n('fill-area').s('overflow:hidden;background:?'.embed(this.theme.background));

	this.editAreaWidth = w;
	this.editAreaHeight = h;

	this.nodeSelectionArea = this.nodeFillArea.a($$()).pos(true).x(0).w(this.nodeFillArea.w()).y(0).h(h+this.options.rowHeight).n('selection-area').s('overflow:hidden').$;

	this.nodeEditArea = this.nodeFillArea.a($$()).pos(true).x(0).y(0).h(h+this.options.rowHeight).n('edit-area').s('overflow:hidden; color:?'.embed(this.theme.textColor)).e('click', function(evt)
	{
		me.window.captureEditAreaClick(evt, me);
	}).$;

	this.nodeEditAreaCache = node.a($$()).pos(true).x(-700).y(-1700).w(300).h(500).v(false).s('overflow:hidden').$;
}

ac.chap.View.prototype.renderSidebarStub = function()
{
	var node = this.nodeRoot;
	var h = node.$.offsetHeight;
	var w_rows = 58;
	
	this.nodeSidebar = $(this.nodeSidebar).rc();
	var node_sidebar_scroll = this.nodeSidebar.a($$()).pos(true).w(w_rows).h(h).x(0).y(0).s('overflow:hidden');
	var bar_offset = 0;
	var bookmark_off_y = Math.max(1, Math.floor(this.options.rowHeight - 11)/2);
	var me = this;
	for ( var i=0; i<=this.numRows; i++ )
	{
//		var bar_node = node_sidebar_scroll.a($$()).pos(true).x(10).y(bar_offset).w(30).s("font-family:'Lucida Grande', Tahoma, Arial, helvetica, sans-serif; font-size:9px; text-align:right; padding-top:1px; color:#777");
		var bar_node = node_sidebar_scroll.a($$()).w(w_rows).h(this.options.rowHeight).a($$()).pos(true).x(10).w(30).s('text-align:right;font-size:?px;color:#999;'.embed(this.window.options.font.size-2));
		bar_node.a($$('span')).s('font-size:?px;padding-top:1px'.embed(this.window.options.font.size-2));
		bar_node.a($$()).pos(true).x(-8).y(bookmark_off_y).w(11).h(11).n('void').e('click', function(evt)
		{
			evt.stop();
			var row_index = parseInt(evt.$.p().ga('row-index'));
			me.window.toggleBookmark(row_index);
			// for ( var i=0; i<me.window.views.length; i++ )
			// {
			// 	if ( 'undefined' == typeof me.window.row_id_map[i][row_index] )
			// 	{
			// 		return;
			// 	}
			// 	// marking as changed
			// 	me.window.row_id_map[i][row_index][1] = false;
			// 	var row_state = me.window.row_id_map[i][row_index][2];
			// 	if ( ac.chap.ROWSTATE_BOOKMARK == (row_state & ac.chap.ROWSTATE_BOOKMARK) )
			// 	{
			// 		// already bookmarked
			// 		me.window.row_id_map[i][row_index][2] &= (65535-ac.chap.ROWSTATE_BOOKMARK);
			// 	}
			// 	else
			// 	{
			// 		me.window.row_id_map[i][row_index][2] |= ac.chap.ROWSTATE_BOOKMARK;
			// 	}
			// }
			$runafter(100, function(){me.window.renderText()});
		});
		bar_node.a($$()).pos(true).x(34).y(bookmark_off_y-1).w(12).h(11).n('void').e('click', function(evt)
		{
			evt.stop();
			var row_index = parseInt(evt.$.p().ga('row-index'));
			for ( var i=0; i<me.window.views.length; i++ )
			{
				if ( 'undefined' == typeof me.window.row_id_map[i][row_index] )
				{
					return;
				}
//				me.window.row_id_map[i][row_index][1] = false;
				var row_state = me.window.row_id_map[i][row_index][2];
				if ( ac.chap.ROWSTATE_FOLD_EXPAND == (row_state & ac.chap.ROWSTATE_FOLD_EXPAND) )
				{
					// was collapsed, will expand
					me.window.views[i].expandFolding(row_index);
				}
				else
				{
					if ( ac.chap.ROWSTATE_FOLD_STOP == (row_state & ac.chap.ROWSTATE_FOLD_STOP) )
					{
						// end marker, getting referenced index
						row_index = me.window.row_id_map[i][row_index][3][1];
					}
					var end_row_index = me.window.row_id_map[i][row_index][3][1];
					me.window.row_id_map[i][row_index][2] |= ac.chap.ROWSTATE_FOLD_EXPAND;
					for ( var ii=row_index; ii<=end_row_index; ii++ )
					{
						me.window.row_id_map[i][ii][1] = false;
						if ( ii != row_index ) //&& ii != end_row_index )
						{
							if ( 0 == ( me.window.row_id_map[i][ii][2] & ac.chap.ROWSTATE_FOLD_COLLAPSED ) )
							{
								me.window.row_id_map[i][ii][2] |= ac.chap.ROWSTATE_FOLD_COLLAPSED;
							}
						}
					}
					me.window.views[i].recalculateVisibleRows();
//					me.window.views[i].numVisibleRows -= (end_row_index-row_index);
//					alert(me.numVisibleRows);
				}
			}
			$runafter(100, function(){me.window.renderText(true)});
		});
		bar_offset += this.options.rowHeight;
	}
	this.nodeSidebar = this.nodeSidebar.$;
}

ac.chap.View.prototype.renderChunk = function(chunk)
{
	var tokens = [];
	var n = this.window.language.chunkRules.length;
	if ( this.window.options.syntaxHighlightingEnabled )
	{
		for ( var i=0; i<n; i++ )
		{
			var m = true;
			var r_offset = 0;
			var r_chunk = chunk;
			var re = this.window.language.chunkRules[i][0];
			var result_index = this.window.language.chunkRules[i][1];
			var token_type = this.window.language.chunkRules[i][2];
			var infinite_check = 200;
			while ( '' != r_chunk && null != m )
			{
				if ( 0 == infinite_check-- )
				{
					console.warn('Error in RegExp definition (chunk): %s for: %s.', re, r_chunk);
					break;
				}
				// console.log(r_chunk);
				m = re.exec(r_chunk);
				if ( null != m)
				{
					if (!m[result_index])
					{
						console.warn('Error in RegExp definition (invalid result index: %i): %s for: %s', result_index, re, r_chunk);
						continue;
					}
					var index = m.index + m[0].indexOf(m[result_index]);
					tokens[r_offset + index] = [token_type, m[result_index]];
					r_offset += index + m[result_index].length;
					r_chunk = r_chunk.substr(index+m[result_index].length);
					// console.log('%o, index:%s, len:%s, %s', m, index, m[result_index].length, m[result_index]);
				}
			}
		}
	}
	//console.log(tokens);
	n = tokens.length;
	var font_style = ';font:' + this.window.options.font.size + 'px ' + this.window.options.font.family;
	if ( 0 < n )
	{
		var rend_chunk = '';
		var offset = 0;
		for ( i=0; i<n; i++ )
		{
			if ( 'undefined' == typeof tokens[i] || '' == tokens[i][1] )
			{
				continue;
			}
			var token = tokens[i];
			rend_chunk += ch_encode_markup(chunk.substr(offset, i-offset));
			if ( this.theme.colorScheme[token[0]] )
			{
				rend_chunk += '<span style="' + this.theme.colorScheme[token[0]] + font_style + '">' + ch_encode_markup(token[1]) + '</span>';				
			}
			else
			{
				rend_chunk += ch_encode_markup(token[1]);
			}
			i += token[1].length - 1;
			// offset = i + token[1].length;
			offset = i + 1;
			// console.log(token, offset, rend_chunk);
		}
		rend_chunk += ch_encode_markup(chunk.substr(offset));
		chunk = rend_chunk;
	}
	else
	{
		chunk = ch_encode_markup(chunk);
	}
	return chunk;
}

ac.chap.View.prototype.renderTextRow = function(node, rowIndex, renderedPreviously)
{
	var row = this.window.char_map[rowIndex];
	var rendered_row = '';
	var offset = 0;
	var font_style = ';font:' + this.window.options.font.size + 'px ' + this.window.options.font.family;
	var interpolation = this.window.language.stringInterpolation;

	var row_state = this.window.row_id_map[this.index][rowIndex][2];

	if ( 'undefined' != typeof this.window.syntax_map[rowIndex] && 0 < this.window.syntax_map[rowIndex].length )
	{
		// console.log(this.window.syntax_map[rowIndex]);
		var n = this.window.syntax_map[rowIndex].length;
		for ( var i=0; i<n; i++ )
		{
			var row_syntax = this.window.syntax_map[rowIndex][i];
			var token_type = row_syntax[0];
			var start_offset = row_syntax[1];
			if ( -1 == start_offset )
			{
				start_offset = 0;
			}
			var end_offset = row_syntax[2]

			rendered_row += this.renderChunk(row.substr(offset, start_offset-offset));
			var chunk = -1 == end_offset ? row.substr(start_offset) : row.substr(start_offset, end_offset-start_offset);
			if ( this.theme.colorScheme[token_type] )
			{
				if (interpolation && ac.chap.TOKEN_DOUBLE_QUOTED == token_type )
				{
					// console.log('interpolate: %s', chunk);
					var re = new RegExp(interpolation[0], 'i');
					var m = null;
					var new_chunk = '';
					while (true)
					{
						// console.info('passing: %s', chunk);
						m = re.exec(chunk);
						if (!m)
						{
							// console.log('nada');
							break;
						}
						// for (var i in m)
						// {
						// 	console.debug(i + ':' + m[i]);
						// }
						new_chunk += '<span style="' + this.theme.colorScheme[token_type] + font_style + '">' + ch_encode_markup(chunk.substring(0, m.index)) + '</span>';
						new_chunk += this.renderChunk(chunk.substr(m.index, m[interpolation[1]].length));
						chunk = chunk.substr(m.index + m[interpolation[1]].length);
						// console.warn(chunk);
					}
					new_chunk += '<span style="' + this.theme.colorScheme[token_type] + font_style + '">' + ch_encode_markup(chunk) + '</span>';
					// console.info(new_chunk);
					rendered_row += new_chunk;
				}
				else
				{
					rendered_row += '<span style="' + this.theme.colorScheme[token_type] + font_style + '">'+ch_encode_markup(chunk)+'</span>';					
					// console.log(rendered_row);
				}
			}
			else
			{
				rendered_row += ch_encode_markup(chunk);
			}
			offset = -1 == end_offset ? row.length : end_offset;
		}		
	}
	rendered_row += this.renderChunk(row.substr(offset));
	// console.log(rendered_row);
	// rendering custom selection (search results, errors and such)
	// !!!!!!!!!!
	// NOT USED NOW !!!!!
	// !!!!!!!!!!
	// !!!!!!!!!!
	// !!!!!!!!!!
	// !!!!!!!!!!
	if ( false && ac.chap.ROWSTATE_SELECTION == (row_state & ac.chap.ROWSTATE_SELECTION) )
	{
		var range = this.window.row_id_map[this.index][rowIndex][5];
		if ( 0 == range[0] && this.window.char_map[rowIndex].length == range[1] )
		{
			rendered_row = '<span style="width:auto;display:block;'+(''==rendered_row ? ('height:'+this.options.rowHeight+'px;'):'')+this.theme.selectionStyle+'">'+rendered_row+'</span>';
		}
		else
		{
	//		console.log(range);
			var raw = rendered_row;
			var n = raw.length;
			var col_index = 0;
			var selection_started = false;
			var offset = 0;
		//	console.log('before: %s', raw);
			for ( var i=0; i<n; i++ )
			{
				//console.log('step %s: %s', i, rendered_row);
				var ch = raw.charAt(i);
				if ( '<' == ch )
				{
					if ( selection_started )
					{
						var c = '</span>';
						rendered_row = rendered_row.substr(0, i+offset)+c+rendered_row.substr(i+offset);
						offset += c.length;
					}
					var ix = raw.substr(i).indexOf('>');
					i += ix;
		//			console.log('ix: %s', ix);

					if ( selection_started )
					{
						var c = '<span style="'+this.theme.selectionStyle+'">';
						rendered_row = rendered_row.substr(0, i+offset+1)+c+rendered_row.substr(i+offset+1);
						offset += c.length;
					}
					continue;
				}
				if ( range[0] == col_index )
				{
					selection_started = true;
					var c = '<span style="'+this.theme.selectionStyle+'">';
					rendered_row = rendered_row.substr(0, i+offset)+c+rendered_row.substr(i+offset);
					offset += c.length;
				}
				if ( selection_started && range[1]-1 < col_index )
				{
					selection_started = false;
					var c = '</span>';
					rendered_row = rendered_row.substr(0, i+offset)+c+rendered_row.substr(i+offset);
					break;
				}
				if ( '&' == ch )
				{
					if ( '&lt;' == raw.substr(i, 4) || '&gt;' == raw.substr(i, 4) )
					{
						i += 3;
					}
					else if ( '&amp;' == raw.substr(i, 5) )
					{
						i += 4;
					}
				}
				col_index++;
			}
			if ( selection_started )
			{
				rendered_row += '</span>';
			}
		}
	}
//	console.log(rendered_row);
	// making intelligent tabelators - note, using simple replace of \t doesn't work
	var ix = 0;
	var tab = this.options.tabelator;
	var raw = this.window.char_map[rowIndex];
	var tab_stack = [];
	while ( -1 != ix )
	{
		ix = raw.indexOf('\t');
		if ( -1 != ix )
		{
			var tab_length = tab.length - (ix % tab.length);
			raw = raw.substr(0,ix)+tab.substr(0, tab_length)+raw.substr(ix+1);
			tab_stack.push(tab_length);
		}
	}
	for ( var i=0; i<tab_stack.length; i++ )
	{
		rendered_row = rendered_row.replace(/\t/, tab.substr(0, tab_stack[i]));
	}
	// word wrap
	var num_subrows = 1;
	if ( this.options.wordWrap && this.numCols < raw.length )
	{
		var raw = rendered_row;

		var printable = '';
		var n = rendered_row.length;
		var offset = 1;
		for ( i=0; i<n; i++ )
		{
			var ch = rendered_row.charAt(i);
			if ( '<' == ch && 'b' != rendered_row.charAt(i+1) )
			{
				ix = rendered_row.substr(i).indexOf('>');
				if ( -1 == ix )
				{
					break;
				}
				i += ix;
				continue;
			}
			var n_ch = 0;
			if ( '&' == ch )
			{
				if ( '&lt;' == rendered_row.substr(i,4) || '&gt;' == rendered_row.substr(i,4) )
				{
					n_ch = 3;
				}
				else if ( '&amp;' == rendered_row.substr(i,5) )
				{
					n_ch = 4;
				}
			}
			printable += ch.charAt(0);
			if ( this.numCols == printable.length )
			{
				raw = raw.substr(0, i+offset+n_ch)+'<br>'+raw.substr(i+offset+n_ch);
				num_subrows++;
				offset += 4;
				printable = '';
			}
			i += n_ch;
		}
		rendered_row = raw;
	}
	if ( ac.chap.ROWSTATE_FOLD_EXPAND == (row_state & ac.chap.ROWSTATE_FOLD_EXPAND) )
	{
		var end_index = this.window.row_id_map[this.index][rowIndex][3][1];
		var content = ch_encode_markup(this.window.char_map.slice(rowIndex, end_index+1).join('\n').replace(/"/ig, "''"));
		rendered_row += '<a href="javascript:ac.chap.route(\'expand-folding\', \'window-id\', '+this.index+', '+rowIndex+')"><div class="folding-expand-inner" style="position:absolute" title="?"></div></a>'.embed(content);
	}
	node.setAttribute('num-subrows', num_subrows);
	
	if ( $__tune.isIE )
	{
		// IE trims input source in innerHTML
	    rendered_row = ch_encode_markup_spaces(rendered_row);
	}
	node.innerHTML = rendered_row;
}

ac.chap.View.prototype.recalculateVisibleRows = function()
{
	var map = this.window.row_id_map[this.index];
	var n = map.length;
	var i = 0;
	var num_visibles = 0;
	while ( i < n )
	{
		var state = map[i][2];
		if ( 0 == (ac.chap.ROWSTATE_FOLD_COLLAPSED & state) )
		{
			num_visibles++;
		}
		i++;
	}
	this.numVisibleRows = num_visibles;
}

ac.chap.View.prototype.getVisibleRowIndices = function()
{
	var map = this.window.row_id_map[this.index];
	var i = 0;
	var index = this.startRow;
	var indices = [];
	while ( i++ <= this.numRows )
	{
		if ( 'undefined' == typeof this.window.row_id_map[this.index][index] )
		{
			break;
		}
		var state = this.window.row_id_map[this.index][index][2];
		if ( ac.chap.ROWSTATE_FOLD_COLLAPSED == (ac.chap.ROWSTATE_FOLD_COLLAPSED & state) )
		{
			// collapsed
			i--;
			index++;
			continue;
		}
		indices.push(index);
		if ( ac.chap.ROWSTATE_FOLD_EXPAND == (state & ac.chap.ROWSTATE_FOLD_EXPAND) )
		{
			// collapsed folding
			var refered_row_index = this.window.row_id_map[this.index][index][3][1];
			index = refered_row_index + 1;
		}
		else
		{
			index++;
		}
	}
	return indices;
}

ac.chap.View.prototype.renderRowSidebar = function(position, rowIndex, rowNode, forceCompleteRedraw)
{
	if (!this.nodeSidebar.firstChild.childNodes.item(position))
	{
		return;
	}
	var bar_node = this.nodeSidebar.firstChild.childNodes.item(position).firstChild;
	if ( 0 == rowNode.offsetHeight )
	{
		rowNode.style.height = this.options.rowHeight;
	}
	var num_subrows = parseInt(rowNode.getAttribute('num-subrows'));
	var cache_id = forceCompleteRedraw ? 'none' : (num_subrows+':'+this.window.row_id_map[this.index][rowIndex].join('-'));
	if (bar_node.getAttribute('sidebar-cache-id') == cache_id && 'none' != cache_id)
	{
		return;
	}
	if ('none' != cache_id)
	{
		bar_node.setAttribute('sidebar-cache-id', cache_id);
		bar_node.firstChild.style.fontSize = (this.window.options.font.size-2) + 'px';
	}
	// console.log(cache_id);
	
	var row_height = num_subrows * this.options.rowHeight;
	bar_node.parentNode.style.height = row_height + 'px';
	if (forceCompleteRedraw)
	{
		bar_node.firstChild.style.fontSize = (this.window.options.font.size-2) + 'px';		
	}
	var ht = rowIndex+1;
	if ( this.options.wordWrap )
	{
		var htt = '<div style="height:'+this.options.rowHeight+'px;" class="wrapped-row"></div>';
		for ( var i=1; i<num_subrows; i++ )
		{
			ht += htt;
		}
	}
	bar_node.firstChild.innerHTML = ht;
	bar_node.setAttribute('row-index', rowIndex);

	var row_state = this.window.row_id_map[this.index][rowIndex][2];
	var fold_marker = (ac.chap.ROWSTATE_FOLD_START == (row_state & ac.chap.ROWSTATE_FOLD_START)) || (ac.chap.ROWSTATE_FOLD_STOP == (row_state & ac.chap.ROWSTATE_FOLD_STOP));
	if ( !fold_marker )
	{
		bar_node.lastChild.className = 'void';
	}
	else
	{
		bar_node.lastChild.style.display = 'block';
		if ( ac.chap.ROWSTATE_FOLD_EXPAND == (row_state & ac.chap.ROWSTATE_FOLD_EXPAND) )
		{
			// folding may expand
			bar_node.lastChild.className = 'folding-expand';
		}
		else
		{			
			if ( ac.chap.ROWSTATE_FOLD_START == (row_state & ac.chap.ROWSTATE_FOLD_START) )
			{
				// folding starts
				bar_node.lastChild.className = 'folding-start';
			}

			if ( ac.chap.ROWSTATE_FOLD_STOP == (row_state & ac.chap.ROWSTATE_FOLD_STOP) )
			{
				// folding stops
				bar_node.lastChild.className = 'folding-stop';
			}				
		}
	}
	if ( ac.chap.ROWSTATE_BOOKMARK == (row_state & ac.chap.ROWSTATE_BOOKMARK) )
	{
		// bookmark
		bar_node.firstChild.nextSibling.className = 'bookmark-default';
	}
	else
	{
		bar_node.firstChild.nextSibling.className = 'void';
	}	
}

ac.chap.View.prototype.renderSelection = function()
{
	var row_indices = this.getVisibleRowIndices();
	var num_rows = row_indices.length;
	var node_cache = document.createElement('div');
	var tab = this.options.tabelator;
	// console.log('RENDER SELECTION for: ');
	for ( var i=0; i<num_rows; i++ )
	{
		var row_index = row_indices[i];
		if (!this.window.row_id_map[this.index][row_index])
		{
			continue;
		}
		// console.log('row: %o', this.window.row_id_map[this.index][row_index]);
		var row_state = this.window.row_id_map[this.index][row_index][2];
		if ( ac.chap.ROWSTATE_SELECTION == (row_state & ac.chap.ROWSTATE_SELECTION) )
		{
			var node_row = document.getElementById('row-'+this.window.instanceId+'-'+this.index+'-'+row_index);
			if ( null == node_row )
			{
				continue;
			}
			var range = [this.window.row_id_map[this.index][row_index][5][0], this.window.row_id_map[this.index][row_index][5][1]];
			// console.log('selection range: %o', range);
//			console.log(range);
			if ( -1 == range[1] )
			{
				continue;
			}
			var render_whole_row = false;
			if ( 0 == range[0] && this.window.char_map[row_index].length == range[1] )
			{
				render_whole_row = ( this.window.row_id_map[this.index][row_index+1] && ac.chap.ROWSTATE_SELECTION == (this.window.row_id_map[this.index][row_index+1][2] & ac.chap.ROWSTATE_SELECTION) );
			}
			var cachid = range[0]+'-'+range[1];
			var node_id = 'rsel-'+this.window.instanceId+'-'+this.index+'-'+row_index;
			var node_row_selection = document.getElementById(node_id);
			if ( null != node_row_selection && node_row_selection.getAttribute('cachid') == cachid)
			{
				node_row_selection.style.top = node_row.offsetTop + 'px';
				node_cache.appendChild(node_row_selection);
			}
			else
			{
				node_row_selection = node_cache.appendChild(document.createElement('div'));
				node_row_selection.id = node_id;
				node_row_selection.style.background = this.theme.selectionStyle;
				node_row_selection.style.position = 'absolute';
				node_row_selection.style.top = node_row.offsetTop + 'px';
				node_row_selection.setAttribute('cachid', cachid);
				node_row_selection.style.height = this.options.rowHeight + 'px';
				if ( render_whole_row )
				{
					node_row_selection.style.left = '0px';
					node_row_selection.style.width = node_row.offsetWidth + 'px';
					node_row_selection.style.height = node_row.offsetHeight + 'px';
				}
				else
				{
					if ( this.options.wordWrap )
					{
						var raw_row = this.window.char_map[row_index];
						var ix_c = 0;
						var ix_r = 0;
						var offset = [0,-1, 0,-1];
						for ( var ii=0; ii<raw_row.length; ii++ )
						{
							var ch = raw_row.charAt(ii);
							if ( ii == range[0] )
							{
								offset[0] = ix_r;
								offset[1] = ix_c;
							}
							if ( '\t' == ch )
							{
								var tab_length = tab.length - (ix_c % tab.length);
								ix_c += tab_length;
							}
							else
							{
								ix_c++;
							}
							if ( ix_c > this.numCols )
							{
								ix_r++;
								ix_c -= this.numCols;
							}
							if ( ii == range[1] )
							{
								offset[2] = ix_r;
								offset[3] = ix_c;
								break;
							}
						}
						if ( -1 == offset[3] )
						{
							offset[2] = ix_r+1;//offset[0]+1;
						}
						node_row_selection.style.top = (node_row.offsetTop + this.options.rowHeight*offset[0]) + 'px';
//						console.log('%o', offset);
						if ( offset[0] == offset[2] )
						{
							// selection stays non-wrapped
							node_row_selection.style.left = offset[1]*this.options.colWidth + 'px';
							node_row_selection.style.width = ((offset[3]-offset[1])*this.options.colWidth) + 'px';
//							console.log(node_row_selection.style.width);
						}
						else
						{
							// finishing current node
							if ( -1 == offset[1] )
							{
								// caret stays on the end of the row
								node_row_selection.style.left = (ix_c*this.options.colWidth) + 'px';
								node_row_selection.style.width = (node_row.offsetWidth - (ix_c*this.options.colWidth)) + 'px';								
							}
							else
							{
								node_row_selection.style.left = (offset[1]*this.options.colWidth) + 'px';
								node_row_selection.style.width = (node_row.offsetWidth - (offset[1]*this.options.colWidth)) + 'px';								
							}
							// marking as non-cacheable
							node_row_selection.removeAttribute('cachid');
							// creating additional ones
							for ( ii=offset[0]+1; ii<=offset[2]; ii++ )
							{
								node_row_selection = node_cache.appendChild(document.createElement('div'));
								node_row_selection.style.background = this.theme.selectionStyle;
								node_row_selection.style.position = 'absolute';
								node_row_selection.style.left = '0px';
								node_row_selection.style.top = (node_row.offsetTop+ii*this.options.rowHeight) + 'px';
								node_row_selection.style.height = this.options.rowHeight + 'px';
								if ( ii != offset[2] )
								{
									node_row_selection.style.width = node_row.offsetWidth + 'px';									
								}
								else
								{
									node_row_selection.style.width = ((offset[3])*this.options.colWidth) + 'px';
								}
							}
						}
						
					}
					else
					{
						var offset_x1 = this.getRenderedStringDimension(row_index, 0, range[0])[0];
						var offset_x2 = this.getRenderedStringDimension(row_index, 0, range[1]+1)[0];
						node_row_selection.style.left = offset_x1 + 'px';
						node_row_selection.style.width = (offset_x2 - offset_x1) + 'px';
					}
				}
			}
			// console.log('selection after range: %o', this.window.row_id_map[this.index][row_index][3]);
			
		}
	}
	// console.log('%o', this.window.row_id_map[this.index][0]);
	var ht = node_cache.innerHTML;
	this.nodeSelectionArea.innerHTML = ht;
}

ac.chap.View.prototype.renderText = function(forceCompleteRedraw)
{
	var row_indices = this.getVisibleRowIndices();
	var num_rows = row_indices.length;
//	console.log('view: %s - row indices: %o', this.index, row_indices);

//	console.log('view: %s - num rows x cols [%s x %s]', this.index, this.numRows, this.numCols);
	// checking to see if only one row changed - the most usual case
	var changed_row_index = -1;
	var changed_row_position = -1;
	for ( var i=0; i<num_rows; i++ )
	{
		var row_index = row_indices[i];
		if ( !this.window.row_id_map[this.index][row_index][1] )
		{
			// changed
			if (-1 == changed_row_index)
			{
				changed_row_index = row_index;
				changed_row_position = i;
			}
			else
			{
				// more than two rows changed
//				console.log('changed on '+row_index);
				changed_row_index = -2;
				break;
			}
		}
	}
//	console.log('changed row: %s', changed_row_index);
//	console.log('rendered for %s ? %s', this.index, this.window.row_id_map[this.index][2][1] ? 'YES' : 'NO');
	var scroll_hash = this.index+'-'+row_indices.length+'-'+this.window.row_id_map[this.index][row_indices[0]][0]+'-'+this.window.row_id_map[this.index][row_indices[row_indices.length-1]][0]+'-'+this.nodeScrollArea.$.scrollHeight+'-'+Math.floor(this.nodeScrollArea.$.scrollTop/this.options.rowHeight);
//	console.log('hash: %s  changed index: %s', scroll_hash, changed_row_index);
	var already_rendered = -2 != changed_row_index && (null != this.nodeEditArea.getAttribute('last-scroll')) && (this.nodeEditArea.getAttribute('last-scroll') == scroll_hash);
	this.nodeEditArea.setAttribute('last-scroll', scroll_hash);

	if ( already_rendered && 0 <= changed_row_index )
	{
		// one row change
		var row_node = document.getElementById('row-'+this.window.instanceId+'-'+this.index+'-'+changed_row_index);
		if ( null != row_node && null != row_node.parentNode && this.window.row_id_map[this.index][changed_row_index][0] == row_node.getAttribute('row-id') )
		{
			this.renderTextRow(row_node, changed_row_index);
			if ( '' == row_node.innerHTML )
			{
				row_node.style.height = this.options.rowHeight+'px';
			}
			else
			{
				row_node.style.height = null;
			}
			this.renderRowSidebar(changed_row_position, changed_row_index, row_node);

			this.window.row_id_map[this.index][changed_row_index][1] = true;
			already_rendered = true;
//			console.log('view: %s, one row only %s', this.index, changed_row_index);
		}
	}
	var top_offset = - this.nodeScrollArea.$.scrollTop % this.options.rowHeight;
	var row_width = (this.options.wordWrap ? this.wrapWidth : this.nodeFillArea.$.offsetWidth)+'px';
	if ( forceCompleteRedraw || !already_rendered )
	{
//		var num_rendered_subrows = 0;
		for ( i=0; i<num_rows; i++ )
		{
			var row_index = row_indices[i];

			var is_row_changed = !this.window.row_id_map[this.index][row_index][1];

			// marking row as unchanged
			this.window.row_id_map[this.index][row_index][1] = true;
			
			var row_node = document.getElementById('row-'+this.window.instanceId+'-'+this.index+'-'+row_index);
			if ( !is_row_changed )
			{
				is_row_changed = (null == row_node) || (null == row_node.parentNode) || (row_node.getAttribute('row-id') != this.window.row_id_map[this.index][row_index][0]);
			}
			if ( null == row_node || null == row_node.parentNode )
			{
				is_row_changed = true;
				
				// console.log(this.options.rowTemplate);
				row_node = this.options.rowTemplate.cloneNode(false);
				row_node.id = 'row-'+this.window.instanceId+'-'+this.index+'-'+row_index;
				row_node.style.width = row_width;
				row_node.setAttribute('row-index', row_index);
			}
			if ( forceCompleteRedraw || is_row_changed )
			{
				row_node.setAttribute('row-id', this.window.row_id_map[this.index][row_index][0]);
				if (forceCompleteRedraw)
				{
					row_node.style.minHeight = this.options.rowTemplate.style.minHeight;
					row_node.style.lineHeight = this.options.rowTemplate.style.lineHeight;
					row_node.style.font = this.options.rowTemplate.style.font;
				}
				this.renderTextRow(row_node, row_index);
			}
			if ( '' == row_node.innerHTML )
			{
				row_node.style.height = this.options.rowHeight+'px';
			}
			else
			{
				row_node.style.height = null;
			}
			this.nodeEditAreaCache.appendChild(row_node);

			// rendering side bar
			this.renderRowSidebar(i, row_index, row_node, forceCompleteRedraw);
			//num_rendered_subrows += parseInt(row_node.getAttribute('num-subrows'));
		}
		// clearing remaining sidebar rows
		for ( i=num_rows; i<this.numRows; i++ )
		{
			if (this.nodeSidebar.firstChild.childNodes.item(i) && this.nodeSidebar.firstChild.childNodes.item(i).firstChild)
			{
				var bar_node = this.nodeSidebar.firstChild.childNodes.item(i).firstChild;
				bar_node.lastChild.className = 'void';
				bar_node.firstChild.nextSibling.className = 'void';
				bar_node.firstChild.innerHTML = '';
			}
		}

		this.nodeEditArea.style.top = this.nodeSelectionArea.style.top = (this.startRowOffset*this.options.rowHeight)+'px';
		if ( $__tune.isSafari )
		{
			// Safari is extremely fast when doing DOM
			this.nodeEditArea.innerHTML = '';
			while ( this.nodeEditAreaCache.firstChild )
			{
				this.nodeEditArea.appendChild(this.nodeEditAreaCache.firstChild);
			}
		}
		else
		{
			// other browsers are a bit lazy..
			var ht = this.nodeEditAreaCache.innerHTML
			this.nodeEditArea.innerHTML = ht;
			this.nodeEditAreaCache.innerHTML = '';
		}

// TODO: NNN is the number of subrows in WHOLE document.. hard to calculate on-the-fly (too slow), affects word-wrapped documents only..
//		var fill_area_h = (this.numVisibleRows+NNN)*this.options.rowHeight;
//		console.log('num visible for view :%s = %s, row_id.len = %s', this.index, this.numVisibleRows, this.window.row_id_map[this.index].length);

		var fill_area_h = (this.numVisibleRows+2)*this.options.rowHeight;
		if ( this.nodeRoot.h()-$__tune.ui.scrollbarWidth > fill_area_h )
		{
			fill_area_h = this.nodeRoot.h()-$__tune.ui.scrollbarWidth;
		}
		this.nodeFillArea.h(fill_area_h);
		
	}
	else
	{
		this.nodeEditAreaCache.innerHTML = '';
	}
	if ( parseInt(this.nodeSidebar.firstChild.style.top) != top_offset )
	{
		this.nodeSidebar.firstChild.style.top  = (top_offset)+'px';
		this.nodeSidebar.firstChild.style.height  = (this.nodeSidebar.offsetHeight - $__tune.ui.scrollbarWidth - top_offset)+'px';		
	}
	this.renderSelection();
}



/*
 * ac.Chap - Text Editing Component widget - Settings file
 */

if ( 'undefined' == typeof ac )
{
	var ac = {chap:{}};
}


$class('ac.chap.KeyMap',
{
	construct:function()
	{
		this.definition = {};
		this.isMac = true;
		this.wordCompleteCache = null;
		this.snippetCompleteCache = null;
		this.searchKeyword = '';
		this.initDefinition();
	}
});

ac.chap.KeyMap.prototype.initDefinition = function()
{
}

ac.chap.KeyMap.prototype.importCommands = function(commands)
{
	var n = commands.length;
	for ( var i=0; i<n; i++ )
	{
		var command = commands[i];
		if ( $isset(command.key_activation) )
		{
//			console.debug('Compiling key `?` for snippet #?'.embed(snippet.key_activation, i));
			this.compile("KEY: ?\ncustom(action:'RunCommand', commandIndex:?)\n".embed(command.key_activation, i));
		}
	}
}

ac.chap.KeyMap.prototype.importSnippets = function(snippets)
{
	var n = snippets.length;
	for ( var i=0; i<n; i++ )
	{
		var snippet = snippets[i];
		if ( $isset(snippet.key_activation) )
		{
//			console.debug('Compiling key `?` for snippet #?'.embed(snippet.key_activation, i));
			this.compile("KEY: ?\ncustom(action:'RunSnippet', snippetIndex:?)\n".embed(snippet.key_activation, i));
		}
	}
//	console.debug('%o',this.definition);
}

ac.chap.KeyMap.prototype.action_NotDefined = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	console.warn('There is no custom action defined for key code: %s and control keys mask: %s.', keyCode, controlKeysMask);
}

ac.chap.KeyMap.prototype.action_RunCommand = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	var command = $getdef(component.commands[params.commandIndex], null);
	if ( null == command )
	{
		console.warn('There is no command at index `%s`.', params.commandIndex);
		return;
	}
	return component.runCommand(keyCode, controlKeysMask, caretRow, caretCol, command, params);
}

ac.chap.KeyMap.prototype.action_RunSnippet = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	var snippet = $getdef(component.snippets[params.snippetIndex], null);
	if ( null == snippet )
	{
		console.warn('There is no snippet at index `%s`.', params.snippetIndex);
		return;
	}
	return this.snippetInit(snippet, component, caretRow, caretCol, true);
}

ac.chap.KeyMap.prototype.action_RunVirtualSnippet = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	var result = this.snippetInit(params.snippet, component, caretRow, caretCol, true);
	return result;
}


ac.chap.KeyMap.prototype.action_ToggleBookmark = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	component.toggleBookmark(caretRow);
	$runafter(100, function(){component.renderText()});
	return 0;
}

ac.chap.KeyMap.prototype.action_GoToBookmark = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	component.scrollToBookmark(caretRow, params['direction']);
	return 0;
}

ac.chap.KeyMap.prototype.action_WordComplete = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	if ( !component.language.wordDelimiter.test(component.getCharAt(caretRow, caretCol-1)) )
	{
		// no word char before caret
		return;
	}
	var wcc = this.wordCompleteCache;
	if ( !wcc )
	{
		wcc = {position:[-1,-1], results:[], index:-1};
	}
	var proceed_complete = false;
	if ( wcc.position[0] != caretRow || wcc.position[1] != caretCol )
	{
		// new search
		var max_words = 300;
		var words_prev = component.getWordAt(caretRow, caretCol, -max_words-1);
		var words_next = component.getWordAt(caretRow, caretCol, max_words);
		var looking_for = words_prev[0];
		var looking_for_len = looking_for.length;
//		console.log('new search for: %s', looking_for);
		var found_words = [looking_for];
		var found_words_index = '';
		for ( var i=0; i<max_words; i++ )
		{
			if ( words_prev[i+1] && words_prev[i+1].length > looking_for_len && words_prev[i+1].substr(0, looking_for_len) == looking_for )
			{
				if ( -1 == found_words_index.indexOf(' '+words_prev[i+1]) )
				{
					found_words.push(words_prev[i+1]);
					found_words_index += ' '+words_prev[i+1];
				}
			}
			if ( words_next[i] && words_next[i].length > looking_for_len && words_next[i].substr(0, looking_for_len) == looking_for )
			{
				if ( -1 == found_words_index.indexOf(' '+words_next[i]) )
				{					
					found_words.push(words_next[i]);
					found_words_index += ' '+words_next[i];
				}
			}
		}
		if ( 1 < found_words.length )
		{
//			console.log('results found: %o', found_words);
			wcc.results = found_words;
			wcc.index = 0;
			proceed_complete = true;
		}
	}
	else
	{
		proceed_complete = true;
	}
	var num_results = wcc.results.length;
	if ( proceed_complete && 0 < num_results )
	{
		var index = wcc.index;
		index += params.direction ? 1 : -1;
		if ( num_results <= index )
		{
			index = 0;
		}
		else if ( 0 > index )
		{
			index = num_results-1;
		}
//		console.log('n:%s i:%s', num_results, index);
		// let's not add the following operation to the transaction/undo log
		component.stopTransactionLog();
		component.runAction(ac.chap.ACTION_CARET, {move:'prev_word'});
		component.runAction(ac.chap.ACTION_SELECTION, {add:true});
		component.runAction(ac.chap.ACTION_DELETE, {character:false});
		component.runAction(ac.chap.ACTION_INSERT, {string:wcc.results[index]});
		component.startTransactionLog();
		wcc.index = index;
		wcc.position = [component.caret.position[0], component.caret.position[1]];
	}
	else
	{
		wcc.results = [];
	}
	this.wordCompleteCache = wcc;
	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;
}

ac.chap.KeyMap.prototype.getAffectedRows = function(component, caretRow)
{
	var from_row = caretRow;
	var to_row = caretRow;
	if (null != component.selection)
	{
		var start_pos = component.selection.startPosition[0];
		var end_pos = component.selection.endPosition[0];
		if (-1 == component.selection.endPosition[1])
		{
			end_pos--;
		}
		from_row = Math.min(start_pos, end_pos);
		to_row = Math.max(start_pos, end_pos);
	}
	return [from_row, to_row];
}

ac.chap.KeyMap.prototype.action_Indent = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	var affected_rows = this.getAffectedRows(component, caretRow);
	var tab = component.getTabelator();
	for (var i=affected_rows[0]; i<=affected_rows[1]; i++)
	{
		if ('right' == params.direction)
		{
			component.insertIntoCharacterMap(tab, i, 0);			
		}
		else
		{
			var row = component.char_map[i];
			var index = 0;
			while (('\t' == row.charAt(index) || ' ' == row.charAt(index)) && (row.length > index) && (tab.length > index)) index++;
			if (0 < index)
			{
				component.removeFromCharacterMap(i, 0, i, index);
			}
		}
	}
	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT | ac.chap.ACTION_RES_SELECTIONCHANGED;	
}

ac.chap.KeyMap.prototype.action_Comment = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	if (!component.language)
	{
		return 0;
	}
	var markers = component.language.singleRowCommentStartMarkers;
	if (0 == markers.length)
	{
		return 0;
	}
	var marker = markers[0];
	var tab = component.getTabelator();
	var affected_rows = this.getAffectedRows(component, caretRow);
	var tab = component.getTabelator();
	var prepend_text = marker + ' ';
	for (var i=affected_rows[0]; i<=affected_rows[1]; i++)
	{
		var row = component.char_map[i];
		var index = row.indexOf(marker);
		if (-1 != index && 0 == row.substring(0, index).replace(tab, '').replace(' ', ''))
		{
			// was commented
			component.removeFromCharacterMap(i, 0, i, index+marker.length);
		}
		else
		{
			// will be commented
			component.insertIntoCharacterMap(marker, i, 0);
		}
	}
	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT | ac.chap.ACTION_RES_SELECTIONCHANGED;	
}

ac.chap.KeyMap.prototype.action_RuntimeOption = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	component.setRuntimeOption(params['key'], params['value']);
	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT | ac.chap.ACTION_RES_SELECTIONCHANGED;	
}

ac.chap.KeyMap.prototype.action_SearchInteractive = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	component.showInteractiveSearch();
	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_SELECTIONCHANGED;
}

ac.chap.KeyMap.prototype.action_SetSearchKeyword = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	if (params['keyword'])
	{
		this.searchKeyword = params['keyword'];
		return 0;
	}
	if (component.selection && component.selection.startPosition[0] == component.selection.endPosition[0])
	{
		this.searchKeyword = component.getSelection();
		return ac.chap.ACTION_RES_SELECTIONCHANGED;
	}
	return 0;
}

ac.chap.KeyMap.prototype.action_SearchKeyword = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	if ('' == this.searchKeyword)
	{
		return 0;
	}
	row_index = caretRow;
	var index = 0;
	var search_down = 'down' == params['direction'];
	do
	{
		var row = component.char_map[row_index];
		var offset = 0;
		console.log(ac.chap.activeComponent.activeView);
		if (row_index == caretRow)
		{
			if (search_down)
			{
				// if (row.substring(caretCol, this.searchKeyword.length) == this.searchKeyword)
				// {
				// 	// offset = this.searchKeyword.length;
				// }
				row = row.substr(caretCol)
				offset += caretCol;
			}
			else
			{
				if (row.substring(caretCol-this.searchKeyword.length, caretCol))
				{
					offset = this.searchKeyword.length;
				}
				row = row.substring(0, caretCol - offset);
				offset = 0;
			}
		}
		index = search_down ? row.indexOf(this.searchKeyword) : row.lastIndexOf(this.searchKeyword);
		if (-1 != index)
		{
			index += offset;
			component.runAction(ac.chap.ACTION_SELECTION, {remove:true});
			component.runAction(ac.chap.ACTION_CARET, {moveTo:[row_index, index]});
			component.runAction(ac.chap.ACTION_CARET, {store:true});
			component.runAction(ac.chap.ACTION_CARET, {moveTo:[row_index, index+this.searchKeyword.length]});
			component.runAction(ac.chap.ACTION_SELECTION, {add:true});
			return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_SELECTIONCHANGED | ac.chap.ACTION_RES_SCROLLTOCARET;
		}
		row_index += search_down ? 1 : -1;
		if (search_down && row_index == component.char_map.length)
		{
			row_index = 0;
		}
		else if (!search_down && -1 == row_index)
		{
			row_index = component.char_map.length-1;
		}
	}
	while (caretRow != row_index);
	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_SELECTIONCHANGED;
}

ac.chap.KeyMap.prototype.action_SmartIndent = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	// console.log(params);
	var line = component.getLineAt(caretRow);
	var m = params['indent_tab_when_ends'] ? line.match(/^([ \t]*)(.*)$/) : line.match(/^([ \t]*)([^ \t]*)/);
	// console.log(m);
	var prepend_text = m[1];
	if (params['indent_tab_when_ends'] || params['indent_tab_when_starts'])
	{
		m[2] = m[2].trim();
		var indent_when_values = params['indent_tab_when_ends'] ? params['indent_tab_when_ends'].split(' ') : params['indent_tab_when_starts'].split(' ');
		for (var i=0; i<indent_when_values.length; i++)
		{
			if ((params['indent_tab_when_ends'] && indent_when_values[i] == m[2].substr(m[2].length-indent_when_values[i].length)) || (params['indent_tab_when_starts'] && indent_when_values[i] == m[2].substr(0, indent_when_values[i].length)))
			{
				prepend_text += component.getTabelator();
				break;
			}
		}
	}
	// console.log(prepend_text);
	if (params['split_line'])
	{
		component.runAction(ac.chap.ACTION_INSERT, {row:true});		
	}
	else
	{
		component.runAction(ac.chap.ACTION_CARET, {move:'row_end'});
		prepend_text = (params['set_char_at_end'] ? params['set_char_at_end'] : '') + '\n' + prepend_text;
	}
	// console.log('prepend_text: %s', prepend_text);
	component.runAction(ac.chap.ACTION_INSERT, {string:prepend_text});
	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;
}

ac.chap.KeyMap.prototype.action_SmartUnindent = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	if (!params['starts_with'])
	{
		console.warn('Missing starts_with parameter for SmartUnindent.');
		return 0;
	}
	if (!params['ends_with'])
	{
		console.warn('Missing ends_with parameter for SmartUnindent.');
		return 0;
	}
	// console.log(params);
	var line = component.getLineAt(caretRow);
	var starts_with = params['starts_with'].split(' ');
	var ends_with = params['ends_with'].split(' ');
	if (starts_with.length != ends_with.length)
	{
		console.warn('Non-matching start and end tokens for SmartUnindent.');
		return 0;
	}
	var trim_line = line.trim() + String.fromCharCode(keyCode);
	var proceed = false;
	for (var i=0; i<ends_with.length; i++)
	{
		if (ends_with[i] == trim_line)
		{
			proceed = true;
			break;
		}				
	}
	var prepend_text = null;
	if (proceed)
	{
		var row = caretRow - 1;
		var need_nth_match = 0;
		var match_from_end = 'end' == params['match_from'];
		while (0 <= row && null == prepend_text)
		{
			line = component.getLineAt(row);
			var m = match_from_end ? line.match(/^([ \t]*)(.*)$/) : line.match(/([ \t]*)([^ \t]*)/);
			m[2] = m[2].trim();
			
			
			for (i=0; i<ends_with.length; i++)
			{
				if ((match_from_end && ends_with[i] == m[2].substr(m[2].length-ends_with[i].length)) || (!match_from_end && ends_with[i] == m[2].substr(0, ends_with[i].length)))
				{
					need_nth_match++;
					trim_line = line.trim();
					break;
				}				
			}
			for (i=0; i<starts_with.length; i++)
			{
				if ((match_from_end && starts_with[i] == m[2].substr(m[2].length-starts_with[i].length)) || (!match_from_end && starts_with[i] == m[2].substr(0, starts_with[i].length)))
				{
					if (0 == need_nth_match)
					{
						prepend_text = m[1] + trim_line;
					}
					need_nth_match--;
					break;
				}				
			}
			// console.log('row: %i, %o', row, m);
			row--;
		}
	}
	// console.log(prepend_text);
	if (null != prepend_text)
	{
		component.runAction(ac.chap.ACTION_CARET, {move:'row_start'});
		component.runAction(ac.chap.ACTION_SELECTION, {add:true});
		component.runAction(ac.chap.ACTION_DELETE, {'char':true});
		component.runAction(ac.chap.ACTION_INSERT, {string:prepend_text});
		component.runAction(ac.chap.ACTION_CARET, {move:'row_end'});
	}
	else
	{
		component.runAction(ac.chap.ACTION_INSERT, {string:String.fromCharCode(keyCode)});
	}
	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;
}

ac.chap.KeyMap.prototype.action_AutoComplete = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	var selected_text = component.getSelection();
	var inserted_text = params.text;
	if ('' != selected_text)
	{
		component.runAction(ac.chap.ACTION_DELETE, {character:true});
		if (params['use_selection'])
		{
			inserted_text = selected_text + params.text;
		}
	}
	component.runAction(ac.chap.ACTION_INSERT, {string:String.fromCharCode(keyCode)});
	component.runAction(ac.chap.ACTION_INSERT, {string:inserted_text, skipCaretChange:'' == selected_text});
	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;
}

ac.chap.KeyMap.prototype.action_SnippetComplete = function(keyCode, controlKeysMask, caretRow, caretCol, component, params)
{
	var scc = this.snippetCompleteCache;
	var proceed_as_normal_tab = null == scc;
	var selection_changed = false;
	var tab_activation = null;

	if ( proceed_as_normal_tab )
	{
		if ( null != component.selection )
		{
			tab_activation = '';
		}
		else
		{
			if ( component.language.wordDelimiter.test(component.getCharAt(caretRow, caretCol-1)) )
			{
				tab_activation = component.getWordAt(caretRow, caretCol, -1);
			}
		}
	}

	if ( proceed_as_normal_tab && null != tab_activation )
	{
//		console.log(tab_activation);
		var snippets = component.snippets;
//		console.log('%o', snippets);
		var found_snippets = [];
		for ( var i=0; i<snippets.length; i++ )
		{
			var snippet = snippets[i];
			if ( snippet.tab_activation == tab_activation )
			{
				found_snippets.push(snippet);
			}
		}
//		console.log(found_snippets);
		if ( 0 < found_snippets.length)
		{
			return this.snippetInit(found_snippets[0], component, caretRow, caretCol, ''==tab_activation, tab_activation);
		}
	}
	if ( proceed_as_normal_tab )
	{
		if ( null != scc )
		{
			component.removeActionListener(scc.callbackIndex);
			component.removeSelection();
		}
		component.runAction(ac.chap.ACTION_INSERT, {string:'\t'});
	}
	else
	{
		// changing to next tabstop
		// stopping current listener
		component.removeActionListener(scc.callbackIndex);
		component.removeSelection();
		if ( 0 != scc.activeTabStopIndex )
		{
			// there is another possible tabstop
			var found = false;
			for ( var i=scc.activeTabStopIndex+1; i<scc.tabstops.length; i++ )
			{
				if ( scc.tabstops[i] )
				{
					scc.activeTabStopIndex = i;
					found = true;
					break;
				}
			}
			if ( !found )
			{
				// let's activate last $0 tabstop
				scc.activeTabStopIndex = 0;
			}
			// move caret to the tabstop position
			var tabstop = scc.tabstops[scc.activeTabStopIndex];
//			console.log('new active #%s', scc.activeTabStopIndex);
			for ( var tab_id in scc.tabstops )
			{
				var placeholder = scc.tabstops[tab_id];
//				console.log('#%s : %o', tab_id, placeholder);
			}
			
			component.runAction(ac.chap.ACTION_SELECTION, {remove:true});
			component.runAction(ac.chap.ACTION_CARET, {moveTo:scc.insertCaretPosition});
			component.runAction(ac.chap.ACTION_CARET, {moveBy:'column', value:tabstop[2]-(scc.wasSelection?0:scc.tabActivation.length)});

			if ( '' != tabstop[1] )
			{
				component.runAction(ac.chap.ACTION_CARET, {store:true});
				component.runAction(ac.chap.ACTION_CARET, {moveBy:'column', value:tabstop[1].length});
				component.runAction(ac.chap.ACTION_SELECTION, {add:true});
				selection_changed = true;
			}
			
			if ( 0 != scc.activeTabStopIndex )
			{
				scc.firstInitialized = true;
				// adding new listener
				scc.callbackIndex = component.addActionListener(ac.chap.ACTION_LISTENER_BOTH, this, this.snippetCompleteActionListener);
//				console.log('activating next tabstop: %s', scc.activeTabStopIndex);
			}
			else
			{
//				console.log('END at $0');
				scc = null;
			}
			this.snippetCompleteCache = scc;
		}
	}
	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT | (selection_changed ? ac.chap.ACTION_RES_SELECTIONCHANGED : 0);
}

ac.chap.KeyMap.prototype.snippetInit = function(snippet, component, caretRow, caretCol, wasSelection, tabActivation)
{
	tabActivation = tabActivation || '';
	var code = snippet.code;
	var code_chunks = [];
	var re = '';
	var m = [];
	var selection_changed = false;

	// [preprocessing - indentation]
	var indent_line = component.char_map[component.getCaretPosition()[0]];
	var indent_string = indent_line.match(/[\s]*/)[0];
	code = code.replace(/\n/g, "\n" + indent_string);

	// [preprocessing - escape]
	code = code.replace(/\\\$/g, '\0');

	// [preprocessing - simple variables]
	re = /(^|[^\\])(\${1,2})([a-zA-Z][\w_\-\+]*)/;
	while ( true )
	{
		m = re.exec(code);
		if ( null == m )
		{
			break;
		}
		var is_escaped = 2 == m[2].length;
		var var_name = m[3];
		var value = component.getVariableValue(var_name);
//debug		value = "'"+value+"\n'";
		if ( is_escaped )
		{
			value = value.replace(/'/g, "\\'").replace(/\n/g, "\\n");
		}
//		console.log('found %s = %s', var_name, value);
		code = code.substr(0, m.index+m[1].length)+value+code.substr(m.index+m[0].length);
	}

	// [preprocessing - variables with default values]
	re = /(^|[^\\])(\${1,2})\{([a-zA-Z][\w_\-\+]*)\:([^\}]*)\}/;
	while ( true )
	{
		m = re.exec(code);
		if ( null == m )
		{
			break;
		}
		var is_escaped = 2 == m[2].length;		
		var var_name = m[3];
		var default_value = m[4];
		var value = component.getVariableValue(var_name, default_value);
//debug		value = "'"+value+"\n'";
		if ( is_escaped )
		{
			value = value.replace(/'/g, "\\'").replace(/\n/g, "\\n");
		}
//		console.log('found %s (def:%s) = %s', var_name, default_value, value);
		code = code.substr(0, m.index+m[1].length)+value+code.substr(m.index+m[0].length);
	}
	
	// [preprocessing - variables with regular transformations]
	re = /(^|[^\\])(\${1,2})\{([a-zA-Z][\w_\-\+]*)\/([^\/]*)\/([^\/]*)\/([^\}]*)\}/;
	while ( true )
	{
		m = re.exec(code);
		if ( null == m )
		{
			break;
		}
		var is_escaped = 2 == m[2].length;		
		var var_name = m[3];
		var pattern = m[4];
		var replacement = m[5];
		var options = m[6];
		var value = component.getVariableValue(var_name);
//		console.log('found %s (pattern:%s  repl:%s  opt:%s) = %s', var_name, pattern, replacement, options, value);
		try
		{
			eval('value = value.replace(/?/?, "?");'.embed(pattern, options, replacement.replace(/"/g, '\"')));			
		}
		catch (e)
		{
			console.error('Snippet runtime error. Regular transformation for variable `%s`, pattern `%s`, replacement `%s` and options `%s` failed. Error: `%s`.', var_name, pattern, replacement, options, e);
		}
//		console.log('result: %s', value);
//debug		value = "'"+value+"\n'";
		if ( is_escaped )
		{
			value = value.replace(/'/g, "\\'").replace(/\n/g, "\\n");
		}
		code = code.substr(0, m.index+m[1].length)+value+code.substr(m.index+m[0].length);
	}
	
	// [preprocessing - variables with custom transformations]
	re = /(^|[^\\])(\${1,2})\{([a-zA-Z][\w_\-\+]*)\|([^\}]*)\}/;
	while ( true )
	{
		m = re.exec(code);
		if ( null == m )
		{
			break;
		}
		var is_escaped = 2 == m[2].length;
		var var_name = m[3];
		var transformation = m[4];
		var value = component.getVariableValue(var_name);
//		console.log('found %s (transformation:%s) = %s', var_name, transformation, value);
		try
		{
			if ( '.' == transformation.charAt(0) )
			{
				eval('value = value?'.embed(transformation));
			}
			else
			{
				eval('value = this.snippetTransform_?(value, component)'.embed(transformation));
			}
		}
		catch (e)
		{
			console.error('Snippet runtime error. Custom transformation for variable `%s` and transformation `%s` failed. Error: `%s`.', var_name, transformation, e);
		}
//		console.log('result: %s', value);
//debug		value = "'"+value+"\n'";
		if ( is_escaped )
		{
			value = value.replace(/'/g, "\\'").replace(/\n/g, "\\n");
		}
		code = code.substr(0, m.index+m[1].length)+value+code.substr(m.index+m[0].length);
	}	

	if ( wasSelection && null != component.selection)
	{
		component.runAction(ac.chap.ACTION_DELETE, {character:false});
		caretRow = component.caret.position[0];
		caretCol = component.caret.position[1];
	}
	
	// [executing backsticks]
	var execution_scheduled = false;

	re = /`(([^`]|\\`)*)`/;
	while ( true )
	{
		m = re.exec(code);
		if ( null == m )
		{
			break;
		}
		var exec_code = m[1];
		var code_rows = exec_code.split('\n');
		if ( 1 == code_rows )
		{
			console.warn('Snippet definition error. Backstick code too short. You might be missing declaration or there is no code body. Further execution terminated. Source: `%s`', exec_code);
			break;
		}
		var declaration = exec_code.split('\n')[0].trim();
		var body = code_rows.slice(1).join('\n');
		var output = '';
//		console.log('execute: declaration: %s body: %s', declaration, body);
		if ( '/local/javascript' == declaration )
		{
			// executing local code
//			console.log('local code');
			try
			{
				eval(body);
			}
			catch (e)
			{
				console.error('Snippet runtime error. Backstick execution of local code for declaration `%s` and source code `%s` failed. Error: `%s`.', declaration, body, e);
				break;
			}
		}
		else if ( '/remote/post' == declaration )
		{
			// executing remote post
			var action = '';
			var params = {};
			try
			{
				eval(body);
			}
			catch (e)
			{
				console.error('Snippet runtime error #01. Backstick execution of remote code for declaration `%s` and source code `%s` failed. Error: `%s`.', declaration, body, e);
				break;
			}
//			console.log('remote call');
			params.a = action;
			$rpost( params,
				function(output)
				{
					// creating virtual snippet
					var v_snippet = {};
					if ( snippet.tab_activation )
					{
						v_snippet.tab_activation = snippet.tab_activation;
					}
					if ( snippet.key_activation )
					{
						v_snippet.key_activation = snippet.key_activation;
					}
					v_snippet.code = code.substr(0, m.index)+output+code.substr(m.index+m[0].length);
					v_snippet.name = snippet.name;
//					console.log('v-snippet: %o', v_snippet);
					var result = component.runAction(ac.chap.ACTION_CUSTOM, {action:'RunVirtualSnippet', snippet:v_snippet});
					component.processActionResult(ac.chap.ACTION_RES_REDRAWTEXT==(result & ac.chap.ACTION_RES_REDRAWTEXT), ac.chap.ACTION_RES_REDRAWCARET==(result & ac.chap.ACTION_RES_REDRAWCARET));
					if ( ac.chap.ACTION_RES_SELECTIONCHANGED==(result & ac.chap.ACTION_RES_SELECTIONCHANGED) )
					{
						component.hideCaret();
					}
				},
				function(e)
				{
					console.error('Snippet runtime error #02. Backstick execution of remote code for declaration `%s` and source code `%s` failed. Error: `%s`.', declaration, body, e);
				},
				'POST', ac.chap.activeComponent.options.remoteBackendURL
			);
			execution_scheduled = true;

			if ( !wasSelection )
			{
				component.runAction(ac.chap.ACTION_CARET, {move:'prev_word'});
				component.runAction(ac.chap.ACTION_SELECTION, {add:true});
				component.runAction(ac.chap.ACTION_DELETE, {character:true});
//				selection_changed = true;
			}

			break;
		}
		code = code.substr(0, m.index)+output+code.substr(m.index+m[0].length);
	}

	if ( !execution_scheduled )
	{
		var tabstops = [];

		// [getting tabstops/placeholders]
		re = /(^|[^\\\{])\$\{(\d)\:([^\}\{]*)\}/;
		var any_change = true;
		var tab_id = 0;
		// two cycles to bypass classical recursion for nested tabstops
		while ( any_change )
		{
			any_change = false;
			code_chunks = [];
			while ( true )
			{
				m = re.exec(code);
//				console.log(code);
//				console.log(m);
				if ( null != m )
				{
					if ( m[0])
					var start_ix = m.index + m[1].length;
					tab_id = m[2];
					tabstops[tab_id] = ['ph', m[3], -1, -1];
					code_chunks.push(code.substr(0, start_ix)+'#<CHAP_PLACEHOLDER_BEGIN:'+tab_id+'>#');
					code = code.substr(start_ix+4, m[3].length)+'#<CHAP_PLACEHOLDER_END:'+tab_id+'>#'+code.substr(start_ix+m[0].length-m[1].length);
					any_change = true;
				}
				else
				{
					break;
				}
			}
			code_chunks.push(code);
			code = code_chunks.join('');
		}
		re = /#<CHAP_PLACEHOLDER_BEGIN\:(\d)>#/;
		while ( true )
		{
			m = re.exec(code)
			if ( null == m )
			{
				break;
			}
			tabstops[m[1]][1] = tabstops[m[1]][1].replace(/#<CHAP_PLACEHOLDER_(BEGIN|END):\d>#/g, '');
			tabstops[m[1]][2] = m.index;
			tabstops[m[1]][3] = tabstops[m[1]][1].length;
			code = code.substr(0, m.index)+code.substr(m.index+m[0].length).replace('#<CHAP_PLACEHOLDER_END:'+m[1]+'>#', '');
		}

		// [getting mirrors]
		re = /\{\$\{(\d)\:([^\}]*)\}\}/;
		while ( true )
		{
			m = re.exec(code)
			if ( null == m )
			{
				break;
			}
			code = code.substr(0, m.index)+m[2]+code.substr(m.index+m[0].length);
			var ix_end = code.indexOf('{$'+m[1]+'}');
			if ( -1 == ix_end )
			{
				console.error('Invalid snippet definition. Mirror `?` does not have `{$?}` mirrored location specified.'.embed(m[1], m[1]));
				break;
			}
			tabstops[m[1]] = ['mi', m[2], m.index, m[2].length, ix_end];
			if ( m.index > ix_end )
			{
				console.error('Unsupported feature. Mirror `?` should have mirrored location positioned AFTER itself.'.embed(m[1]));
			}
			code = code.substr(0, ix_end)+code.substr(ix_end+4);
		}

		// [getting tabstops]
		re = /(^|[^\\])\$(\d)/;
		while (true)
		{
			m = re.exec(code);
			if ( null == m )
			{
				break;
			}
			tab_id = m[2];
			if ( tabstops[tab_id] )
			{
				console.error('Invalid snippet definition. Tabstop `?` already defined as placeholder at position `?`. Snippet source: `?`.'.embed(tab_id, m.index, code));
				break;
			}
			var start_ix = m.index+m[1].length;
			tabstops[tab_id] = ['ts', '', start_ix, 0];
			code = code.substr(0, start_ix)+code.substr(start_ix+2);
			var offset = m[1].length + 2;
			for ( var tab_id in tabstops )
			{
				// console.log('adjusting: %s, %s < %s', tab_id, start_ix, tabstops[tab_id][2]);
				if ( 'mi' == tabstops[tab_id][0] )
				{
					if ( start_ix < tabstops[tab_id][2] )
					{
						tabstops[tab_id][2] -= offset;								
					}
					if ( start_ix < tabstops[tab_id][4] )
					{
						tabstops[tab_id][4] -= offset;								
					}
				}
				else if ( 'ph' == tabstops[tab_id][0] && start_ix < tabstops[tab_id][2] )
				{
					tabstops[tab_id][2] -= offset;
				}
			}
		}
		// $0 not defined, will be at the end of the snippet by default
		if ( !tabstops[0] )
		{
			tabstops[0] = ['ts', '', code.length, 0];
		}
	
		// [postprocessing - unescape]
		code = code.replace(/\0/g, '$');


		for ( var tab_id in tabstops )
		{
			var placeholder = tabstops[tab_id];
//			console.log('#%s : %o', tab_id, placeholder);
		}
		var scc = 
		{
			firstInitialized:true,
			insertCaretPosition:[caretRow, caretCol],
			tabstops: tabstops,
			callbackIndex: -1,
			activeTabStopIndex:tabstops[1] ? 1 : 0,
			activeTabStopRange:[],
			activeTabStopContent:'',
			activeTabStopNested:[],
			wasSelection:wasSelection,
			tabActivation:tabActivation
		}

		if ( !scc.wasSelection )
		{
			component.runAction(ac.chap.ACTION_CARET, {move:'prev_word'});
			component.runAction(ac.chap.ACTION_SELECTION, {add:true});
			component.runAction(ac.chap.ACTION_DELETE, {character:true});
		}

		var tabstop = tabstops[scc.activeTabStopIndex];
		

		component.runAction(ac.chap.ACTION_INSERT, {string:code.substr(0, tabstop[2])});
		component.runAction(ac.chap.ACTION_INSERT, {string:code.substr(tabstop[2]), skipCaretChange:true});

		// selecting default value
		var selection_changed = false;
		if ( '' != tabstop[1] )
		{
			component.runAction(ac.chap.ACTION_CARET, {store:true});
			component.runAction(ac.chap.ACTION_CARET, {moveBy:'column', value:tabstop[1].length});
			component.runAction(ac.chap.ACTION_SELECTION, {add:true});
			selection_changed = true;
		}

		if ( 0 != scc.activeTabStopIndex )
		{
			// starting action listener
			this.snippetCompleteCache = scc;					
			this.snippetCompleteCache.callbackIndex = component.addActionListener(ac.chap.ACTION_LISTENER_BOTH, this, this.snippetCompleteActionListener);
		}
	}
	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT | (selection_changed ? ac.chap.ACTION_RES_SELECTIONCHANGED : 0);
//	return ac.chap.ACTION_RES_REDRAWCARET | ac.chap.ACTION_RES_REDRAWTEXT;
}

ac.chap.KeyMap.prototype.snippetCompleteActionListener = function(component, action, type, actionResult, actionType, params, caretRow, caretCol)
{
	var scc = action.snippetCompleteCache;

	if ( ac.chap.ACTION_LISTENER_BEFORE == type && !scc.firstInitialized )
	{
		// before action listener
		// check if we are still in the tabstop range
//		var offset = component.char_map[caretRow].substr()
		// console.log('activeTabStopRange: %o', scc.activeTabStopRange);
		if ( caretRow < scc.activeTabStopRange[0] || caretRow > scc.activeTabStopRange[2] || caretCol < scc.activeTabStopRange[1] || caretCol > scc.activeTabStopRange[3] )
		{
			// out of range, canceling whole snippet logic
			component.removeActionListener(scc.callbackIndex);
			component.removeSelection();
			delete action.snippetCompleteCache;
			// console.log('CANCELED');
			return;
		}
//		console.log('before: %s - [%s,%s]', actionType, caretRow, caretCol);
	}
	else
	{
		// after action listener
		if ( scc.firstInitialized )
		{
			scc.firstInitialized = false;
			var tabstop = scc.tabstops[scc.activeTabStopIndex];
			caretCol -= tabstop[1].length;
			var code_rows = tabstop[1].split('\n');
			var num_code_rows = code_rows.length;
			var to_caret_row = caretRow + num_code_rows - 1;
			var to_caret_col = (to_caret_row == caretRow ? caretCol : 0) + code_rows[num_code_rows-1].length;
			scc.activeTabStopRange = [caretRow, caretCol, to_caret_row, to_caret_col];
			scc.stopMarker = component.char_map[to_caret_row].substr(to_caret_col);
			// creating list of nested tabstops
			for ( var i in scc.tabstops )
			{
				if ( i == scc.activeTabStopIndex )
				{
					continue;
				}
				var c_tabstop = scc.tabstops[i];
				if ( c_tabstop[2] >= tabstop[2] && (c_tabstop[2] + c_tabstop[3] <= tabstop[2] + tabstop[3]) )
				{
					scc.activeTabStopNested[i] = true;
				}
			}
			if ( 'mi' != tabstop[0] )
			{
				scc.activeTabStopContent = tabstop[1];
			}
			scc.firstRealRun = false;
			
//			action.snippetCompletePostInit(component, caretRow, caretCol);
			// console.log('firstRealRun: %o', scc.activeTabStopRange);
		}
		else
		{
			// console.log('next: %o', scc.activeTabStopRange);
			// adjust the range by finding the stop marker
			var n = component.char_map.length;
			var i = scc.activeTabStopRange[0];
			var found = false;
			var max_iter = 50;
//			var offset_range = [scc.activeTabStopRange[2], scc.activeTabStopRange[3]];
			var new_content = '';
			var old_content = scc.activeTabStopContent;
			while ( i<n && 0 < max_iter-- )
			{
				var ix = '' == scc.stopMarker ? component.char_map[i].length : component.char_map[i].indexOf(scc.stopMarker);
				if ( -1 != ix )
				{
					scc.activeTabStopRange[2] = i;
					scc.activeTabStopRange[3] = ix;
					// console.log('setting [3] to %i, stop marker: `%s`', ix, scc.stopMarker);
					new_content += (i==scc.activeTabStopRange[0]?component.char_map[i].substring(scc.activeTabStopRange[1], ix) : component.char_map[i].substr(0, ix));
					scc.activeTabStopContent = new_content;
					found = true;
					break;
				}
				new_content += (i==scc.activeTabStopRange[0]?component.char_map[i].substr(scc.activeTabStopRange[1]) : component.char_map[i])+'\n';
				i++;
			}
			if ( !scc.firstRealRun )
			{
				scc.activeTabStopContent = new_content;				
			}
			if ( !found )
			{
				// could not find stop marker, canceling whole snippet logic
				component.removeActionListener(scc.callbackIndex);
				component.removeSelection();
				delete action.snippetCompleteCache;
				// console.log('COULD NOT FIND STOPMARKER');
				return;
			}
			
			var offset = new_content.length - old_content.length;
			if ( 'mi' == scc.tabstops[scc.activeTabStopIndex][0] )
			{
				// mirror
//				console.log('Offset: %s OLD: %s NEW: %s will move: ', offset, old_content, new_content, scc.tabstops[scc.activeTabStopIndex][4]-scc.tabstops[scc.activeTabStopIndex][2]-scc.tabstops[scc.activeTabStopIndex][3]);
				//scc.tabstops[scc.activeTabStopIndex][4] += offset;
				var current_caret_pos = [component.caret.position[0], component.caret.position[1]];
				// disabling listeners
				component.stopActionListeners();
				// removing potential selection
				component.runAction(ac.chap.ACTION_SELECTION, {remove:true});
				// moving where it started
				component.runAction(ac.chap.ACTION_CARET, {moveTo:[scc.activeTabStopRange[0], scc.activeTabStopRange[1]]});
				// moving by offset and length of new content
				component.runAction(ac.chap.ACTION_CARET, {moveBy:'column', value:(1 + scc.tabstops[scc.activeTabStopIndex][4]-scc.tabstops[scc.activeTabStopIndex][2]-scc.tabstops[scc.activeTabStopIndex][3]+new_content.length)});
				if ( 0 < old_content.length )
				{
					// storing position
					component.runAction(ac.chap.ACTION_CARET, {store:true});
					// moving by old content length
//					console.log('move before delete:'+old_content.length);
					component.runAction(ac.chap.ACTION_CARET, {moveBy:'column', value:old_content.length});
					// selecting
					component.runAction(ac.chap.ACTION_SELECTION, {add:true});
					// deleting
					component.runAction(ac.chap.ACTION_DELETE, {character:false});
				}
				// inserting new content
				component.runAction(ac.chap.ACTION_INSERT, {string:new_content});
				// returning back to caret
				component.runAction(ac.chap.ACTION_CARET, {moveTo:current_caret_pos});
				// enabling listeners
				component.startActionListeners();
				//adjusting stopmarker for mirrored placeholder AFTER original
				if ( 0 < scc.tabstops[scc.activeTabStopIndex][4] )
				{
					scc.stopMarker = component.char_map[scc.activeTabStopRange[2]].substr(scc.activeTabStopRange[3]);					
				}
			}
			if ( !scc.firstRealRun )
			{
				scc.firstRealRun = true;
				if ( 'mi' == scc.tabstops[scc.activeTabStopIndex][0] && '' != scc.tabstops[scc.activeTabStopIndex][1] )
				{
					offset = new_content.length - scc.tabstops[scc.activeTabStopIndex][1].length;
				}
			}
			
//			console.log('offset: %s', offset);
			var active_offset = scc.tabstops[scc.activeTabStopIndex][2];
			if ( 0 != offset )
			{
				// changed, readjusting tabstops after this and killing all nested
				for ( i in scc.tabstops )
				{
					if ( i == scc.activeTabStopIndex )
					{
						continue;
					}
					var tabstop = scc.tabstops[i];
					if ( tabstop[2] > active_offset )
					{
						if ( scc.activeTabStopNested[i] )
						{
							// nested
							delete scc.tabstops[i];
						}
						else
						{
							tabstop[2] += offset;
							// console.log('ADJUSTING: #%s by %s, new: %s', i, offset, tabstop[2]);
						}
					}
				}
			}
		}
		// console.log('after %s(%s, %s) : %o', actionType, caretRow, caretCol, scc.activeTabStopRange);
	}
}


ac.chap.KeyMap.prototype.compile = function(source)
{
	/* example:
	
		KEY: -13+shift
			selection(add:true)
			caret(move:'up')
			
		KEY: -27
			caret(move:'row_end')
			
		...
		..
		.
	*/
	var rows = source.split('\n');
	var n =  rows.length;
	var re_definition = /^KEY\:\s*[-\d]*[\+\w\s]*$/;
	var re_chain = /^[^\(]*\(.*\)\s*$/;
	var src = '';
	var chain = [];
	var last_key_code = null;
	for ( var i=0; i<n; i++ )
	{
		rows[i] = rows[i].trim();
		if ( re_definition.test(rows[i]) )
		{
			if ( null != last_key_code )
			{
				src += chain.join(',\n');
				src += '\n];\n'
				chain = [];
			}
			var s = rows[i].split(':')[1].split('+');
			var key_code = parseInt(s[0]);
			var control_keys = ['ac.chap.CKEY_NONE'];
			for ( var ii=1; ii<s.length; ii++ )
			{
				control_keys.push('ac.chap.CKEY_'+s[ii].trim().toUpperCase());
			}
			src += "\nif('undefined'==typeof this.definition['?']) {this.definition['?']=[];}\n".embed(key_code, key_code);
			src += "this.definition['?'][?] = [\n".embed(key_code, control_keys.join('|'));
			last_key_code = key_code;
		}
		if ( re_chain.test(rows[i]) )
		{
			var ix = rows[i].indexOf('(');
			var action_type = 'ac.chap.ACTION_'+rows[i].substr(0,ix).trim().toUpperCase();
			var params = rows[i].substring(ix+1, rows[i].length-1).replace(/\:CR/g, '\\n');
			chain.push( action_type+', {'+params+'}' );
		}
	}
	if ( null != last_key_code )
	{
		src += chain.join(',\n');
		src += '\n];\n'
		chain = [];
	}
	var result = true;
	try
	{
		eval(src);
	}
	catch(e)
	{
		result = e;
		console.error('Error while compiling Chap keymap definition: %o. Compiled source: %s', e, src);
	}
	return result;
}

ac.chap.keymap = {};




$class('ac.chap.Theme',
{
	construct:function()
	{
		this.colorScheme = [];
		this.initDefinition();
	}
});

ac.chap.Theme.prototype.initDefinition = function()
{
	this.cssId = '';
	this.background = '#fff';
	this.textColor = '#000';
	this.caretRowStyleActive = '#ededed';
	this.selectionStyle = '#c4dbff';
	this.caretColor = '#000';
}

ac.chap.Theme.prototype.renderCaret = function(caretMode, node)
{
	if ( 1 == caretMode )
	{
		node.style.borderRight = '1px solid '+this.caretColor;
	}
	else
	{
		node.style.height = (parseInt(node.style.height)-1)+'px';
		node.style.borderBottom = '1px solid '+this.caretColor;
	}
}

ac.chap.Theme.prototype.adjustCaretPosition = function(caretMode, pos)
{
	if ( 1 == caretMode )
	{
		pos[0]++;
	}
	else
	{
		pos[0] += pos[2];
	}
	return pos;
}

ac.chap.theme = {};



$class('ac.chap.Language',
{
	construct:function()
	{
		this.foldingStartMarkers = [];
		this.foldingStopMarkers = [];
		this.singleRowCommentStartMarkers = [];
		this.multiRowCommentStartMarker = '';
		this.multiRowCommentEndMarker = '';
		this.initDefinition();
	}
});

ac.chap.Language.prototype.initDefinition = function()
{
	this.singleQuoteStringMarker = "'";
	this.singleQuoteStringMarkerException = '\\';
	this.doubleQuoteStringMarker = '"';
	this.doubleQuoteStringMarkerException = '\\';
	this.chunkRules = 
	[
		[/(([^\w]|^)(\d{1,}[\d\.Ee]*)([^w]|$))/i, 3, ac.chap.CHUNK_NUMBER],
		[/(\+|\-|\*|\/|\=|\!|\^|\%|\||\&|\<|\>)/i, 0, ac.chap.CHUNK_OPERATOR],
		[/(\(|\)|\[|\]|\{|\})/i, 0, ac.chap.CHUNK_PARENTHESIS]
	];
	this.wordDelimiter = /[\w\.\d]/;
	this.indentIgnoreMarker = /[\.]/;
}


ac.chap.lang = {};






/* loader stuff - you are free to modify as needed */


// !! Make sure, bundle_*.js is loaded prior launching this function - the bundle defines ac.chap.langEAmy, EAmyJavaScript etc.
function showEditor(templateNode)
{
	var source = templateNode.value;
	templateNode = $(templateNode);
	var w = templateNode.w();
	var h = templateNode.h();
	
	var node = templateNode.p().ib($$(), templateNode).w(w).h(h);
	templateNode.d(false);
	
	var language = ac.chap.lang.JavaScript;
	var keymap = ac.chap.keymap.EAmyJavaScript;

	var instance = $new(ac.chap.Window, {language:ac.chap.lang.EAmy, keymap:ac.chap.Keymap});
	instance.addView(node, {theme:ac.chap.theme.EAmy, rowHeight:11, colWidth:7, wordWrap:true, tabelator:'    '});

	instance.show();
	instance.setSnippets(eamy.snippets);
	instance.keymap.importSnippets(eamy.snippets);
	instance.edit(source);
	eamy.instances.push(instance);

}

// !! Remove from here and include in your <head> section if you want.
// document.write('<link rel="stylesheet" href="eamy/style.css" type="text/css" media="screen" title="no title" charset="utf-8" />');


// Performed upon loading the page. You are free to remove it and call the showEditor() (or modified version of it) in order to launch the editing component. Code of the showEditor should give you enough clue.
$__tune.event.addListener(self, 'load', function(evt)
{
    // this is basically a search for any <textarea> with -amy-enabled attribute, which is replaced by editing component
	var lst = document.getElementsByTagName('textarea');
	for (var i=0; i<lst.length; i++)
	{
		var node = lst.item(i);
		if ('true' == node.getAttribute('-amy-enabled'))
		{
			showEditor(node);
			var form_node = node;
			while (document != form_node.parentNode)
			{
				if ('form' == form_node.tagName.toLowerCase())
				{
					// changing the submit handler
					eamy.action = form_node.action;
					eamy.form = form_node;
					eamy.textarea = node;
					form_node.action = null;
					form_node.onsubmit = function() {setTimeout('eamy.submit()', 50); return false;}
				}
				form_node = form_node.parentNode;
			}
			break;
		}
	}		
});


// this is called upon submitting the form, feel free to use the code as a reference for your own handling. The important thing is actually only getting the component and retrieving its content: var edited_source = eamy.instances[0].getText();  // that's it :), the rest you can change as you wish (posting via AJAX or whatever..)
eamy.submit = function()
{
	eamy.form.action = eamy.action;
	eamy.form.onsubmit = null;
	if ($__tune.isSafari2)
	{
		eamy.textarea.innerHTML = eamy.instances[0].getText();
	}
	else
	{
		eamy.textarea.value = eamy.instances[0].getText();
	}
	eamy.form.submit();
}

if (!self['console'])
{
	var console = {info:function(){}};
	console.log = console.error = console.warn = console.info;
	
}


