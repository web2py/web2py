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
//
		$call(this, 'ac.chap.Theme.initDefinition');
this.cssId = 'twilight';
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
this.doubleQuoteStringMarkerException = "\\";
this.wordDelimiter = /[\w\d]/;
this.indentIgnoreMarker = /[\t \s]/;
this.foldingStartMarkers = [/^\s*def|class/i];
this.foldingParityMarkers = [/do|(^\s*if)|(^\s*def)|(^\s*class)/i];
this.foldingStopMarkers = [/^\s{0,1}$/i];
this.singleRowCommentStartMarkers = ['#'];
this.multiRowCommentStartMarker = "\"\"\"";
this.multiRowCommentEndMarker = "\"\"\"";
this.stringInterpolation = ['(#\{[^\}]*\})', 1];
this.chunkRules.push([/(([^\w]|^)(\d{1,}[\d\.Ee]*)([^w]|$))/i, 3, ac.chap.CHUNK_NUMBER])
this.chunkRules.push([/(\+|\-|\*|\/|\=|\!|\^|\%|\||\&|\<|\>)/i, 0, ac.chap.CHUNK_OPERATOR])
this.chunkRules.push([/(\(|\)|\[|\]|\{|\})/i, 0, ac.chap.CHUNK_PARENTHESIS])
this.chunkRules.push([/(([^\w]|^)(elif|else|except|finally|for|if|try|while|with)([^\w]|$))/i, 3, ac.chap.CHUNK_KEYWORD])
this.chunkRules.push([/(([^\w]|^)(@[\w]*|break|continue|pass|raise|return|yield|and|in|is|not|or|as|assert|del|exec|print)([^\w]|$))/i, 3, ac.chap.CHUNK_KEYWORD_CUSTOM])
this.chunkRules.push([/((def[ ]{1,})([\w]{1,}))/i, 3, ac.chap.CHUNK_FUNCTION_NAME])
this.chunkRules.push([/(([^\w]|^)(__import__|all|abs|any|apply|callable|chr|cmp|coerce|compile|delattr|dir|divmod|eval|execfile|filter|getattr|globals|hasattr|hash|hex|id|input|intern|isinstance|issubclass|iter|len|locals|map|max|min|oct|ord|pow|range|raw_input|reduce|reload|repr|round|setattr|sorted|sum|unichr|vars|zip|basestring|bool|buffer|classmethod|complex|dict|enumerate|file|float|frozenset|int|list|long|object|open|property|reversed|set|slice|staticmethod|str|super|tuple|type|unicode|xrange)([^\w]|$))/i, 3, ac.chap.CHUNK_LIBRARY])
this.chunkRules.push([/(([^\w]|^)((__(all|bases|class|debug|dict|doc|file|members|metaclass|methods|name|slots|weakref)__)|(import|from|                        abs|add|and|call|cmp|coerce|complex|contains|del|delattr|delete|delitem|delslice|div|divmod|enter|eq|exit|float|floordiv|ge|get|getattr|getattribute|getitem|getslice|gt|hash|hex|iadd|iand|idiv|ifloordiv|ilshift|imod|imul|init|int|invert|ior|ipow|irshift|isub|iter|itruediv|ixor|le|len|long|lshift|lt|mod|mul|ne|neg|new|nonzero|oct|or|pos|pow|radd|rand|rdiv|rdivmod|repr|rfloordiv|rlshift|rmod|rmul|ror|rpow|rrshift|rshift|rsub|rtruediv|rxor|set|setattr|setitem|setslice|str|sub|truediv|unicode|xor))([^\w]|$))/i, 3, ac.chap.CHUNK_LIBRARY_CUSTOM])
}
var snippet = {};
snippet = {tab_activation: '', code: ''};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'ifmain', code: 'if __name__ == '+"'"+'__main__'+"'"+':\n	${1:main()}$0'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'try', code: 'try:\n	${1:pass}\nexcept ${2:Exception}, ${3:e}:\n	${4:raise e}\nelse:\n	${5:pass}'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'property', code: 'def ${1:foo}():\n    doc = "${2:The $1 property.}"\n    def fget(self):\n        ${3:return self._$1}\n    def fset(self, value):\n        ${4:self._$1 = value}\n    def fdel(self):\n        ${5:del self._$1}\n    return locals()\n$1 = property(**$1())$0'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: ''};
eamy.snippets.push(snippet);
snippet = {tab_activation: '__', code: '__${1:init}__'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '.', code: 'self.'};
eamy.snippets.push(snippet);
snippet = {tab_activation: '', code: ''};
eamy.snippets.push(snippet);
//snippet = {tab_activation: 'def', code: 'def ${1:fname}(${2:`if [ "$TM_CURRENT_LINE" != "" ]\n				# poor man'+"'"+'s way ... check if there is an indent or not\n				# (cuz we would have lost the class scope by this point)\n				then\n					echo "self"\n				fi`}):\n	${3/.+/"""/}${3:docstring for $1}${3/.+/"""\n/}${3/.+/\t/}${0:pass}'};
//eamy.snippets.push(snippet);
snippet = {tab_activation: 'def', code: 'def ${1:fname}(${2:`if [ "$TM_CURRENT_LINE" != "" ]\n				# poor man'+"'"+'s way ... check if there is an indent or not\n				# (cuz we would have lost the class scope by this point)\n				then\n					echo "self"\n				fi`}):\n	${3:}\n 	${0:return dict()}'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'class', code: 'class ${1:ClassName}(${2:object}):\n	${3/.+/"""/}${3:docstring for $1}${3/.+/"""\n/}${3/.+/\t/}def __init__(self${4/([^,])?(.*)/(?1:, )/}${4:arg}):\n		${5:super($1, self).__init__()}\n${4/(\A\s*,\s*\Z)|,?\s*([A-Za-z_][a-zA-Z0-9_]*)\s*(=[^,]*)?(,\s*|$)/(?2:\t\tself.$2 = $2\n)/g}		$0'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'aurm', code: '@auth.requires_membership(\'$0\'):'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'dbt', code: '${1:db_name}.define_table("${2:table_name}",\n	SQLField("${3:field_name}", "${4:string/text/password/blob/upload/boolean/integer/double/time/date/datetime/db.reference_table}", ${5:length=$6}, ${7:default="$8"}),$9\n)'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'dbf', code: 'SQLField("${1:field_name}", "${2:string/text/password/blob/upload/boolean/integer/double/time/date/datetime/db.reference_table}", ${3:length=$4}, ${5:default="$6"}),$7'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'dbi', code: '${1:db_name}.${2:table_name}.insert(\n	${3:field_name}="$4" $5\n)'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 't', code: 'T("$0")'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'rev', code: 'response.view=\'$0\''};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'ref', code: 'response.flash=\'$0\''};
eamy.snippets.push(snippet);
snippet = {tab_activation: 're', code: 'redirect(\'$0\')'};
eamy.snippets.push(snippet);
snippet = {tab_activation: 'rej', code: 'response.json=\'$0\''};
eamy.snippets.push(snippet);

