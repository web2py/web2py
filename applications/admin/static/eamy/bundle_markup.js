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


// Generated from theme definition file.
$class('ac.chap.theme.EAmy < ac.chap.Theme');

	ac.chap.theme.EAmy.prototype.initDefinition = function()
	{
//		$call(this, 'ac.chap.Theme.initDefinition');this.cssId = 'black';
//this.background = '#072240';
//this.textColor = '#DFEFFF';
//this.caretColor = 'lime';
//this.caretRowStyleActive = '#041629';
//this.selectionStyle = '#86553b';
//this.colorScheme[ac.chap.TOKEN_MULTIROW_COMMENT] = 'color:#0084FF;font-style:italic';
//this.colorScheme[ac.chap.TOKEN_SINGLEROW_COMMENT] = 'color:#0084FF;font-style:italic';
//this.colorScheme[ac.chap.TOKEN_SINGLE_QUOTED] = 'color:#00DF00';
//this.colorScheme[ac.chap.TOKEN_DOUBLE_QUOTED] = 'color:#00DF00';
//this.colorScheme[ac.chap.CHUNK_KEYWORD] = 'color:#FF9D00';
//this.colorScheme[ac.chap.CHUNK_NUMBER] = 'color:#FF5B8C';
//this.colorScheme[ac.chap.CHUNK_OPERATOR] = 'color:#FF9D00;';
//this.colorScheme[ac.chap.CHUNK_PARENTHESIS] = 'color:#FFF177';
//this.colorScheme[ac.chap.CHUNK_KEYWORD_CUSTOM] = 'color:#54FFB8';
//this.colorScheme[ac.chap.CHUNK_FUNCTION_NAME] = 'color:#FFE000';
//this.colorScheme[ac.chap.CHUNK_LIBRARY] = 'color:#71E5B6';
//this.colorScheme[ac.chap.CHUNK_LIBRARY_CUSTOM] = 'color:#FF78E5';

		$call(this, 'ac.chap.Theme.initDefinition');this.cssId = 'twilight';
this.background = '#141414';
this.textColor = '#F8F8F8';
this.caretColor = '#A7A7A7';
this.caretRowStyleActive = '#1B1B1B';
this.selectionStyle = '#3C4043';
this.colorScheme[ac.chap.TOKEN_MULTIROW_COMMENT] = 'color:#605A60;font-style:italic';
this.colorScheme[ac.chap.TOKEN_SINGLEROW_COMMENT] = 'color:#605A60;font-style:italic';
this.colorScheme[ac.chap.TOKEN_SINGLE_QUOTED] = 'color:#8B9F67';
this.colorScheme[ac.chap.TOKEN_DOUBLE_QUOTED] = 'color:#D4F29E';
this.colorScheme[ac.chap.CHUNK_KEYWORD] = 'color:#D2A964';
this.colorScheme[ac.chap.CHUNK_NUMBER] = 'color:#DE6848';
this.colorScheme[ac.chap.CHUNK_OPERATOR] = 'color:#EFC25A;';
this.colorScheme[ac.chap.CHUNK_PARENTHESIS] = 'color:#ABC4DC';
this.colorScheme[ac.chap.CHUNK_KEYWORD_CUSTOM] = 'color:#A0849E';
this.colorScheme[ac.chap.CHUNK_FUNCTION_NAME] = 'color:#DAD280';
this.colorScheme[ac.chap.CHUNK_LIBRARY] = 'color:#7286A8';
this.colorScheme[ac.chap.CHUNK_LIBRARY_CUSTOM] = 'color:#A55C29';
}


// Generated from bundle keymap definition file.
ac.chap.KeyMap.prototype.initDefinition = function()
	{
		var _ = '\n';
		this.compile
		(""+_+ "KEY: 0"
+_+ "	insert(character:true)"
+_+ "KEY: -37"
+_+ "	caret(move:'left')"
+_+ "KEY: -37+shift"
+_+ "	caret(move:'left')"
+_+ "	selection(add:true)"
+_+ "KEY: -37+ctrl"
+_+ "	caret(move:'prev_regexp', re:'[^|._A-Z ,|(|);]*$')"
+_+ "KEY: -37+alt"
+_+ "	caret(move:'prev_word')"
+_+ "KEY: -37+ctrl+shift"
+_+ "	caret(move:'prev_regexp', re:'[^|._A-Z ,|(|);]*$')"
+_+ "	selection(add:true)"
+_+ "KEY: -37+alt+shift"
+_+ "	caret(move:'prev_word')"
+_+ "	selection(add:true)"
+_+ "KEY: -37+meta"
+_+ "	caret(move:'row_start')"
+_+ "KEY: -37+meta+shift"
+_+ "	caret(move:'row_start')"
+_+ "	selection(add:true)"
+_+ "KEY: -39"
+_+ "	caret(move:'right')"
+_+ "KEY: -39+shift"
+_+ "	caret(move:'right')"
+_+ "	selection(add:true)"
+_+ "KEY: -39+ctrl"
+_+ "	caret(move:'next_regexp', re:'^[^|._A-Z ,|(|);]*')"
+_+ "KEY: -39+alt"
+_+ "	caret(move:'next_word')"
+_+ "KEY: -39+ctrl+shift"
+_+ "	caret(move:'next_regexp', re:'^[^|._A-Z ,|(|);]*')"
+_+ "	selection(add:true)"
+_+ "KEY: -39+alt+shift"
+_+ "	caret(move:'next_word')"
+_+ "	selection(add:true)"
+_+ "KEY: -39+meta"
+_+ "	caret(move:'row_end')"
+_+ "KEY: -39+meta+shift"
+_+ "	caret(move:'row_end')"
+_+ "	selection(add:true)"
+_+ "KEY: -38"
+_+ "	caret(move:'up')"
+_+ "KEY: -38+shift"
+_+ "	caret(move:'up')"
+_+ "	selection(add:true)"
+_+ "KEY: -40"
+_+ "	caret(move:'down')"
+_+ "KEY: -40+shift"
+_+ "	caret(move:'down')"
+_+ "	selection(add:true)"
+_+ "KEY: -13"
+_+ "	insert(row:true)"
+_+ "KEY: -8"
+_+ "	delete(character:true)"
+_+ "KEY: -46"
+_+ "	delete(character:false)"
+_+ "KEY: 75+ctrl+shift"
+_+ "	delete(row:true)"
+_+ "KEY: -27"
+_+ "	custom(action:'WordComplete', direction:true)"
+_+ "KEY: -27+shift"
+_+ "	custom(action:'WordComplete', direction:false)"
+_+ "KEY: -9"
+_+ "	custom(action:'SnippetComplete')"
+_+ "KEY: 123"
+_+ "	custom(action:'AutoComplete', use_selection:true, text:'}')"
+_+ "KEY: 34"
+_+ "	custom(action:'AutoComplete', use_selection:true, text:'\"')"
+_+ "KEY: 91"
+_+ "	custom(action:'AutoComplete', use_selection:true, text:']')"
+_+ "KEY: 40"
+_+ "	custom(action:'AutoComplete', use_selection:true, text:')')"
+_+ "KEY: -36"
+_+ "	caret(move:'doc_start')"
+_+ "KEY: -36+shift"
+_+ "	caret(move:'doc_start')"
+_+ "	selection(add:true)"
+_+ "KEY: -35"
+_+ "	caret(move:'doc_end')"
+_+ "KEY: -35+shift"
+_+ "	caret(move:'doc_end')"
+_+ "	selection(add:true)"
+_+ "KEY: -34+meta"
+_+ "	caret(move:'page_down')"
+_+ "KEY: -34+meta+shift"
+_+ "	caret(move:'page_down')"
+_+ "	selection(add:true)"
+_+ "KEY: -33+meta"
+_+ "	caret(move:'page_up')"
+_+ "KEY: -33+meta+shift"
+_+ "	caret(move:'page_down')"
+_+ "	selection(add:true)"
+_+ "KEY: 99+meta"
+_+ "	clipboard(copy:true)"
+_+ "KEY: 120+meta"
+_+ "	clipboard(cut:true)"
+_+ "KEY: 122+meta"
+_+ "	undo()"
+_+ "KEY: 90+meta+shift"
+_+ "	redo()"
+_+ "KEY: 97+meta"
+_+ "	selection(all:true)"
+_+ "KEY: 97+ctrl"
+_+ "	selection(all:true)"
+_+ "KEY: -113"
+_+ "	custom(action:'GoToBookmark', direction:1)"
+_+ "KEY: -113+shift"
+_+ "	custom(action:'GoToBookmark', direction:-1)"
+_+ "KEY: -113+meta"
+_+ "	custom(action:'ToggleBookmark')"
+_+ "KEY: 91+meta"
+_+ "	custom(action:'Indent', direction:'left')"
+_+ "KEY: 93+meta"
+_+ "	custom(action:'Indent', direction:'right')"
+_+ "KEY: 47+meta"
+_+ "	custom(action:'Comment')"
+_+ "KEY: 43+meta"
+_+ "	custom(action:'RuntimeOption', key:'font.size', value:'bigger')"
+_+ "KEY: 45+meta"
+_+ "	custom(action:'RuntimeOption', key:'font.size', value:'smaller')"
+_+ "KEY: 101+meta"
+_+ "	custom(action:'SetSearchKeyword')"
+_+ "KEY: 103+meta"
+_+ "	custom(action:'SearchKeyword', direction:'down')"
+_+ "KEY: 71+shift+meta"
+_+ "	custom(action:'SearchKeyword', direction:'up')"
+_+ "KEY: 102+ctrl"
+_+ "	custom(action:'SearchInteractive')"
+_+ "KEY: 83+ctrl+shift"
+_+ "	custom(action:'SearchInteractive')"
+_+ "KEY: 102+meta"
+_+ "	custom(action:'SearchInteractive')"
+_+ "KEY: -13"
+_+ "	custom(action:'SmartIndent', split_line:true, indent_tab_when_starts:'class module def if else unless rescue ensure while do __class__')"
+_+ "KEY: -13+meta"
+_+ "	custom(action:'SmartIndent', split_line:false, indent_tab_when_starts:'class module def if else unless rescue ensure while do __class__')"
+_+ "KEY: 39"
+_+ "	custom(action:'AutoComplete', use_selection:true, text:'\\'')"
)};

$class('ac.chap.lang.EAmy < ac.chap.Language');

	ac.chap.lang.EAmy.prototype.initDefinition = function()
	{
		$call(this, 'ac.chap.Language.initDefinition');
this.singleQuoteStringMarker = "'";
this.singleQuoteStringMarkerException = "\\";
this.doubleQuoteStringMarker = "\"";
this.doubleQuoteStringMarkerException = "\\"
this.wordDelimiter = /[\w\.\d]/;
this.indentIgnoreMarker = /[\.]/;
this.foldingStartMarkers = [/^\s*<(div)\b.*>/i, /^\s*<(ul)\b.*>/i];
this.foldingParityMarkers = [/^\s*<(div)\b.*>/i, /^\s*<(ul)\b.*>/i];
this.foldingStopMarkers = [/^\s*<\/(div)>/i, /^\s*<\/(ul)>/i];
this.singleRowCommentStartMarkers = [];
this.multiRowCommentStartMarker = "<!--";
this.multiRowCommentEndMarker = "-->";
this.chunkRules.push([/(([^\w]|^)(\d{1,}[\d\.Ee]*)([^w]|$))/i, 3, ac.chap.CHUNK_NUMBER])
this.chunkRules.push([/(\+|\-|\*|\/|\=|\!|\^|\%|\||\&|\<|\>)/i, 0, ac.chap.CHUNK_OPERATOR])
this.chunkRules.push([/(\(|\)|\[|\]|\{|\})/i, 0, ac.chap.CHUNK_PARENTHESIS])
this.chunkRules.push([/((<|<\/)([\w-_\:]*)([ >]))/i, 3, ac.chap.CHUNK_KEYWORD])
this.chunkRules.push([/(([ \t])([\w-_\:]*)(=$))/i, 3, ac.chap.CHUNK_KEYWORD_CUSTOM])
this.chunkRules.push([/(([^\w]|^)(!DOCTYPE)([^\w]|$))/i, 3, ac.chap.CHUNK_LIBRARY])
this.chunkRules.push([/(([^\w]|^)(\d{1,}[\d\.Ee]*)([^w]|$))/i, 3, ac.chap.CHUNK_NUMBER])
this.chunkRules.push([/(\+|\-|\*|\/|\=|\!|\^|\%|\||\&|\<|\>)/i, 0, ac.chap.CHUNK_OPERATOR])
this.chunkRules.push([/(\(|\)|\[|\]|\{|\})/i, 0, ac.chap.CHUNK_PARENTHESIS])
this.chunkRules.push([/((<|<\/)([\w-_\:]*)([ >]))/i, 3, ac.chap.CHUNK_KEYWORD])
this.chunkRules.push([/(([ \t])([\w-_\:]*)(=$))/i, 3, ac.chap.CHUNK_KEYWORD_CUSTOM])
this.chunkRules.push([/(([^\w]|^)(!DOCTYPE)([^\w]|$))/i, 3, ac.chap.CHUNK_LIBRARY])
}
var snippet = {};
snippet = {tab_activation: '', code: ''};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'ie6', code: '<!--[if IE 6]>${1:${AMY_SELECTED_TEXT:     IE Conditional Comment: Internet Explorer 6 only   }}<![endif]-->$0'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'iegte7', code: '<!--[if gte IE 7]>${1:${AMY_SELECTED_TEXT: IE Conditional Comment: Internet Explorer 7 and above }}<![endif]-->$0'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'ie5', code: '<!--[if IE 5.5]>${1:${AMY_SELECTED_TEXT:   IE Conditional Comment: Internet Explorer 5.5 only }}<![endif]-->$0'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'ie', code: '<!--[if IE]>${1:${AMY_SELECTED_TEXT:       IE Conditional Comment: Internet Explorer          }}<![endif]-->$0'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'ienot', code: '<!--[if !IE]><!-->${1:${AMY_SELECTED_TEXT:  IE Conditional Comment: NOT Internet Explorer      }}<!-- <![endif]-->$0'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'ielte6', code: '<!--[if lte IE 6]>${1:${AMY_SELECTED_TEXT: IE Conditional Comment: Internet Explorer 6 and below }}<![endif]-->$0'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: '<!--[if IE 5.0]>${1:${AMY_SELECTED_TEXT:   IE Conditional Comment: Internet Explorer 5.0 only }}<![endif]-->$0'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'ielt6', code: '<!--[if lt IE 6]>${1:${AMY_SELECTED_TEXT:  IE Conditional Comment: Internet Explorer 5.x      }}<![endif]-->$0'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: ''};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: '${0:${AMY_SELECTED_TEXT/\A<em>(.*)<\/em>\z|.*/(?1:$1:<em>$0<\/em>)/m}}'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: '${0:${AMY_SELECTED_TEXT/\A<strong>(.*)<\/strong>\z|.*/(?1:$1:<strong>$0<\/strong>)/m}}'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: ''};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: ''};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'left', code: '&#x2190;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'backtab', code: '&#x21E4;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'enter', code: '&#x2305;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'arrow', code: '&#x2192;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'option', code: '&#x2325;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'shift', code: '&#x21E7;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: '&nbsp;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'delete', code: '&#x2326;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'backspace', code: '&#x232B;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'escape', code: '&#x238B;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'tab', code: '&#x21E5;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'up', code: '&#x2191;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'control', code: '&#x2303;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'return', code: '&#x21A9;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'down', code: '&#x2193;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'command', code: '&#x2318;'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: ''};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'doctype', code: '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"\n	"http://www.w3.org/TR/html4/strict.dtd">\n'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'doctype', code: '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"\n	"http://www.w3.org/TR/html4/loose.dtd">\n'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'doctypexf', code: '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN"\n	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">\n'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'doctypext', code: '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\n	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'doctypex', code: '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"\n	"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'doctypexs', code: '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"\n	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 't', code: '<{${1:tag_name}}>$0</{$1}>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: ''};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: ''};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'body', code: '<body id="${1:${AMY_FILENAME/(.*)\..*/\L$1/}}"${2: onload="$3"}>\n	$0\n</body>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'textarea', code: '<textarea name="${1:Name}" rows="${2:8}" cols="${3:40}">$0</textarea>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'div', code: '<div${1: id="${2:name}"}>\n	${0:$AMY_SELECTED_TEXT}\n</div>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: '<br>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'title', code: '<title>${1:${AMY_FILENAME/((.+)\..*)?/(?2:$2:Page Title)/}}</title>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'movie', code: '<object width="$2" height="$3" classid="clsid:02BF25D5-8C17-4B23-BC80-D3488ABDDC6B" codebase="http://www.apple.com/qtactivex/qtplugin.cab">\n	<param name="src" value="$1">\n	<param name="controller" value="$4">\n	<param name="autoplay" value="$5">\n	<embed src="${1:movie.mov}"\n		width="${2:320}" height="${3:240}"\n		controller="${4:true}" autoplay="${5:true}"\n		scale="tofit" cache="true"\n		pluginspage="http://www.apple.com/quicktime/download/"\n	>\n</object>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'input', code: '<input type="${1:text/submit/hidden/button}" name="${2:some_name}" value="$3"${4: id="${5:$2}"}>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'head', code: '<head>\n	<meta http-equiv="Content-type" content="text/html; charset=utf-8">\n	<title>${1:${AMY_FILENAME/((.+)\..*)?/(?2:$2:Page Title)/}}</title>\n	$0\n</head>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'meta', code: '<meta name="${1:name}" content="${2:content}">'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'h1', code: '<h1 id="${1/[[:alpha:]]+|( )/(?1:_:\L$0)/g}">${1:$AMY_SELECTED_TEXT}</h1>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'form', code: '<form action="${1:${AMY_FILENAME/(.*?)\..*/$1_submit/}}" method="${2:get}" accept-charset="utf-8">\n	$0\n\n	<p><input type="submit" value="Continue &rarr;"></p>\n</form>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'link', code: '<link rel="${1:stylesheet}" href="${2:/css/master.css}" type="text/css" media="${3:screen}" title="${4:no title}" charset="${5:utf-8}">'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'style', code: '<style type="text/css" media="screen">\n	$0\n</style>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'table', code: '<table border="${1:0}"${2: cellspacing="${3:5}" cellpadding="${4:5}"}>\n	<tr><th>${5:Header}</th></tr>\n	<tr><td>${0:Data}</td></tr>\n</table>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'base', code: '<base href="$1"${2: target="$3"}>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'scriptsrc', code: '<script src="$1" type="text/javascript" charset="${3:utf-8}"></script>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'mailto', code: '<a href="mailto:${1:joe@example.com}?subject=${2:feedback}">${3:email me}</a>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'script', code: '<script type="text/javascript" charset="utf-8">\n	$0\n</script>'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'c', code: 'class="$1"'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'i', code: 'id="$1"'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'p', code: '{{pass}}'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'ex', code: '{{extend \'${1:layout.html}\'}}'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'for', code: '{{for ${1:bar} in ${2:foo}:}}\n	$0\n{{pass}}'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'if', code: '{{if ${1:foo} ${2:==/!=/=>/=</>/<} ${3:bar}:}}\n	$0\n{{pass}}'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '=', code: '{{=$0}}'};
eamy.snippets.push(snippet);


