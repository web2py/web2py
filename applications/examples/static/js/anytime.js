/* anytimec.js 4.1112H (anytime.js 4.1112H)
Copyright 2008-2010 Andrew M. Andrews III (www.AMA3.com). Some Rights 
Reserved. This work licensed under the Creative Commons Attribution-
Noncommercial-Share Alike 3.0 Unported License except in jurisdicitons
for which the license has been ported by Creative Commons International,
where the work is licensed under the applicable ported license instead.
For a copy of the unported license, visit
http://creativecommons.org/licenses/by-nc-sa/3.0/
or send a letter to Creative Commons, 171 Second Street, Suite 300,
San Francisco, California, 94105, USA.  For ported versions of the
license, visit http://creativecommons.org/international/
Any+Time is a trademark of Andrew M. Andrews III. */
var AnyTime={pad:function(val,len)
{var str=String(Math.abs(val));while(str.length<len)
str='0'+str;if(val<0)
str='-'+str;return str;}};(function($)
{var __oneDay=(24*60*60*1000);var __daysIn=[31,28,31,30,31,30,31,31,30,31,30,31];var __iframe=null;var __initialized=false;var __msie6=(navigator.userAgent.indexOf('MSIE 6')>0);var __msie7=(navigator.userAgent.indexOf('MSIE 7')>0);var __pickers=[];jQuery.prototype.AnyTime_picker=function(options)
{return this.each(function(i){AnyTime.picker(this.id,options);});}
jQuery.prototype.AnyTime_noPicker=function()
{return this.each(function(i){AnyTime.noPicker(this.id);});}
jQuery.prototype.AnyTime_height=function(inclusive)
{return(__msie6?Number(this.css('height').replace(/[^0-9]/g,'')):this.outerHeight(inclusive));};jQuery.prototype.AnyTime_width=function(inclusive)
{return(__msie6?(1+Number(this.css('width').replace(/[^0-9]/g,''))):this.outerWidth(inclusive));};jQuery.prototype.AnyTime_current=function(isCurrent,isLegal)
{if(isCurrent)
{this.removeClass('AnyTime-out-btn ui-state-default ui-state-disabled ui-state-highlight');this.addClass('AnyTime-cur-btn ui-state-default ui-state-highlight');}
else
{this.removeClass('AnyTime-cur-btn ui-state-highlight');if(!isLegal)
this.addClass('AnyTime-out-btn ui-state-disabled');else
this.removeClass('AnyTime-out-btn ui-state-disabled');}};jQuery.prototype.AnyTime_clickCurrent=function()
{this.find('.AnyTime-cur-btn').triggerHandler('click');}
$(document).ready(function()
{if(__msie6)
{__iframe=$('<iframe frameborder="0" scrolling="no"></iframe>');__iframe.src="javascript:'<html></html>';";$(__iframe).css({display:'block',height:'1px',left:'0',top:'0',width:'1px',zIndex:0});$(document.body).append(__iframe);}
for(var id in __pickers)
if(!Array.prototype[id])
__pickers[id].onReady();__initialized=true;});AnyTime.Converter=function(options)
{var _flen=0;var _longDay=9;var _longMon=9;var _shortDay=6;var _shortMon=3;var _offAl=Number.MIN_VALUE;var _offCap=Number.MIN_VALUE;var _offF=Number.MIN_VALUE;var _offFSI=(-1);var _offP=Number.MIN_VALUE;var _offPSI=(-1);var _captureOffset=false;this.fmt='%Y-%m-%d %T';this.dAbbr=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];this.dNames=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];this.eAbbr=['BCE','CE'];this.mAbbr=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];this.mNames=['January','February','March','April','May','June','July','August','September','October','November','December'];this.baseYear=null;this.dAt=function(str,pos)
{return((str.charCodeAt(pos)>='0'.charCodeAt(0))&&(str.charCodeAt(pos)<='9'.charCodeAt(0)));};this.format=function(date)
{var d=new Date(date.getTime());if((_offAl==Number.MIN_VALUE)&&(_offF!=Number.MIN_VALUE))
d.setTime((d.getTime()+(d.getTimezoneOffset()*60000))+(_offF*60000));var t;var str='';for(var f=0;f<_flen;f++)
{if(this.fmt.charAt(f)!='%')
str+=this.fmt.charAt(f);else
{var ch=this.fmt.charAt(f+1)
switch(ch)
{case'a':str+=this.dAbbr[d.getDay()];break;case'B':if(d.getFullYear()<0)
str+=this.eAbbr[0];break;case'b':str+=this.mAbbr[d.getMonth()];break;case'C':if(d.getFullYear()>0)
str+=this.eAbbr[1];break;case'c':str+=d.getMonth()+1;break;case'd':t=d.getDate();if(t<10)str+='0';str+=String(t);break;case'D':t=String(d.getDate());str+=t;if((t.length==2)&&(t.charAt(0)=='1'))
str+='th';else
{switch(t.charAt(t.length-1))
{case'1':str+='st';break;case'2':str+='nd';break;case'3':str+='rd';break;default:str+='th';break;}}
break;case'E':str+=this.eAbbr[(d.getFullYear()<0)?0:1];break;case'e':str+=d.getDate();break;case'H':t=d.getHours();if(t<10)str+='0';str+=String(t);break;case'h':case'I':t=d.getHours()%12;if(t==0)
str+='12';else
{if(t<10)str+='0';str+=String(t);}
break;case'i':t=d.getMinutes();if(t<10)str+='0';str+=String(t);break;case'k':str+=d.getHours();break;case'l':t=d.getHours()%12;if(t==0)
str+='12';else
str+=String(t);break;case'M':str+=this.mNames[d.getMonth()];break;case'm':t=d.getMonth()+1;if(t<10)str+='0';str+=String(t);break;case'p':str+=((d.getHours()<12)?'AM':'PM');break;case'r':t=d.getHours()%12;if(t==0)
str+='12:';else
{if(t<10)str+='0';str+=String(t)+':';}
t=d.getMinutes();if(t<10)str+='0';str+=String(t)+':';t=d.getSeconds();if(t<10)str+='0';str+=String(t);str+=((d.getHours()<12)?'AM':'PM');break;case'S':case's':t=d.getSeconds();if(t<10)str+='0';str+=String(t);break;case'T':t=d.getHours();if(t<10)str+='0';str+=String(t)+':';t=d.getMinutes();if(t<10)str+='0';str+=String(t)+':';t=d.getSeconds();if(t<10)str+='0';str+=String(t);break;case'W':str+=this.dNames[d.getDay()];break;case'w':str+=d.getDay();break;case'Y':str+=AnyTime.pad(d.getFullYear(),4);break;case'y':t=d.getFullYear()%100;str+=AnyTime.pad(t,2);break;case'Z':str+=AnyTime.pad(Math.abs(d.getFullYear()),4);break;case'z':str+=Math.abs(d.getFullYear());break;case'%':str+='%';break;case'#':t=(_offAl!=Number.MIN_VALUE)?_offAl:(_offF==Number.MIN_VALUE)?(0-d.getTimezoneOffset()):_offF;if(t>=0)
str+='+';str+=t;break;case'@':t=(_offAl!=Number.MIN_VALUE)?_offAl:(_offF==Number.MIN_VALUE)?(0-d.getTimezoneOffset()):_offF;if(AnyTime.utcLabel&&AnyTime.utcLabel[t])
{if((_offFSI>0)&&(_offFSI<AnyTime.utcLabel[t].length))
str+=AnyTime.utcLabel[t][_offFSI];else
str+=AnyTime.utcLabel[t][0];break;}
str+='UTC';ch=':';case'+':case'-':case':':case';':t=(_offAl!=Number.MIN_VALUE)?_offAl:(_offF==Number.MIN_VALUE)?(0-d.getTimezoneOffset()):_offF;if(t<0)
str+='-';else
str+='+';t=Math.abs(t);str+=((ch=='+')||(ch==':'))?AnyTime.pad(Math.floor(t/60),2):Math.floor(t/60);if((ch==':')||(ch==';'))
str+=':';str+=AnyTime.pad(t%60,2);break;case'f':case'j':case'U':case'u':case'V':case'v':case'X':case'x':throw'%'+ch+' not implemented by AnyTime.Converter';default:str+=this.fmt.substr(f,2);}
f++;}}
return str;};this.getUtcParseOffsetCaptured=function()
{return _offCap;};this.getUtcParseOffsetSubIndex=function()
{return _offPSI;};this.parse=function(str)
{_offCap=_offP;_offPSI=(-1);var era=1;var time=new Date(4,0,1,0,0,0,0);var slen=str.length;var s=0;var tzSign=1,tzOff=_offP;var i,matched,sub,sublen,temp;for(var f=0;f<_flen;f++)
{if(this.fmt.charAt(f)=='%')
{var ch=this.fmt.charAt(f+1);switch(ch)
{case'a':matched=false;for(sublen=0;s+sublen<slen;sublen++)
{sub=str.substr(s,sublen);for(i=0;i<12;i++)
if(this.dAbbr[i]==sub)
{matched=true;s+=sublen;break;}
if(matched)
break;}
if(!matched)
throw'unknown weekday: '+str.substr(s);break;case'B':sublen=this.eAbbr[0].length;if((s+sublen<=slen)&&(str.substr(s,sublen)==this.eAbbr[0]))
{era=(-1);s+=sublen;}
break;case'b':matched=false;for(sublen=0;s+sublen<slen;sublen++)
{sub=str.substr(s,sublen);for(i=0;i<12;i++)
if(this.mAbbr[i]==sub)
{time.setMonth(i);matched=true;s+=sublen;break;}
if(matched)
break;}
if(!matched)
throw'unknown month: '+str.substr(s);break;case'C':sublen=this.eAbbr[1].length;if((s+sublen<=slen)&&(str.substr(s,sublen)==this.eAbbr[1]))
s+=sublen;break;case'c':if((s+1<slen)&&this.dAt(str,s+1))
{time.setMonth((Number(str.substr(s,2))-1)%12);s+=2;}
else
{time.setMonth((Number(str.substr(s,1))-1)%12);s++;}
break;case'D':if((s+1<slen)&&this.dAt(str,s+1))
{time.setDate(Number(str.substr(s,2)));s+=4;}
else
{time.setDate(Number(str.substr(s,1)));s+=3;}
break;case'd':time.setDate(Number(str.substr(s,2)));s+=2;break;case'E':sublen=this.eAbbr[0].length;if((s+sublen<=slen)&&(str.substr(s,sublen)==this.eAbbr[0]))
{era=(-1);s+=sublen;}
else if((s+(sublen=this.eAbbr[1].length)<=slen)&&(str.substr(s,sublen)==this.eAbbr[1]))
s+=sublen;else
throw'unknown era: '+str.substr(s);break;case'e':if((s+1<slen)&&this.dAt(str,s+1))
{time.setDate(Number(str.substr(s,2)));s+=2;}
else
{time.setDate(Number(str.substr(s,1)));s++;}
break;case'f':s+=6;break;case'H':time.setHours(Number(str.substr(s,2)));s+=2;break;case'h':case'I':time.setHours(Number(str.substr(s,2)));s+=2;break;case'i':time.setMinutes(Number(str.substr(s,2)));s+=2;break;case'k':if((s+1<slen)&&this.dAt(str,s+1))
{time.setHours(Number(str.substr(s,2)));s+=2;}
else
{time.setHours(Number(str.substr(s,1)));s++;}
break;case'l':if((s+1<slen)&&this.dAt(str,s+1))
{time.setHours(Number(str.substr(s,2)));s+=2;}
else
{time.setHours(Number(str.substr(s,1)));s++;}
break;case'M':matched=false;for(sublen=_shortMon;s+sublen<=slen;sublen++)
{if(sublen>_longMon)
break;sub=str.substr(s,sublen);for(i=0;i<12;i++)
{if(this.mNames[i]==sub)
{time.setMonth(i);matched=true;s+=sublen;break;}}
if(matched)
break;}
break;case'm':time.setMonth((Number(str.substr(s,2))-1)%12);s+=2;break;case'p':if(time.getHours()==12)
{if(str.charAt(s)=='A')
time.setHours(0);}
else if(str.charAt(s)=='P')
time.setHours(time.getHours()+12);s+=2;break;case'r':time.setHours(Number(str.substr(s,2)));time.setMinutes(Number(str.substr(s+3,2)));time.setSeconds(Number(str.substr(s+6,2)));if(time.getHours()==12)
{if(str.charAt(s)=='A')
time.setHours(0);}
else if(str.charAt(s)=='P')
time.setHours(time.getHours()+12);s+=10;break;case'S':case's':time.setSeconds(Number(str.substr(s,2)));s+=2;break;case'T':time.setHours(Number(str.substr(s,2)));time.setMinutes(Number(str.substr(s+3,2)));time.setSeconds(Number(str.substr(s+6,2)));s+=8;break;case'W':matched=false;for(sublen=_shortDay;s+sublen<=slen;sublen++)
{if(sublen>_longDay)
break;sub=str.substr(s,sublen);for(i=0;i<7;i++)
{if(this.dNames[i]==sub)
{matched=true;s+=sublen;break;}}
if(matched)
break;}
break;case'w':s+=1;break;case'Y':i=4;if(str.substr(s,1)=='-')
i++;time.setFullYear(Number(str.substr(s,i)));s+=i;break;case'y':i=2;if(str.substr(s,1)=='-')
i++;temp=Number(str.substr(s,i));if(typeof(this.baseYear)=='number')
temp+=this.baseYear;else if(temp<70)
temp+=2000;else
temp+=1900;time.setFullYear(temp);s+=i;break;case'Z':time.setFullYear(Number(str.substr(s,4)));s+=4;break;case'z':i=0;while((s<slen)&&this.dAt(str,s))
i=(i*10)+Number(str.charAt(s++));time.setFullYear(i);break;case'#':if(str.charAt(s++)=='-')
tzSign=(-1);for(tzOff=0;(s<slen)&&(String(i=Number(str.charAt(s)))==str.charAt(s));s++)
tzOff=(tzOff*10)+i;tzOff*=tzSign;break;case'@':_offPSI=(-1);if(AnyTime.utcLabel)
{matched=false;for(tzOff in AnyTime.utcLabel)
if(!Array.prototype[tzOff])
{for(i=0;i<AnyTime.utcLabel[tzOff].length;i++)
{sub=AnyTime.utcLabel[tzOff][i];sublen=sub.length;if((s+sublen<=slen)&&(str.substr(s,sublen)==sub))
{s+=sublen;matched=true;break;}}
if(matched)
break;}
if(matched)
{_offPSI=i;tzOff=Number(tzOff);break;}}
if((s+9<slen)||(str.substr(s,3)!="UTC"))
throw'unknown time zone: '+str.substr(s);s+=3;ch=':';case'-':case'+':case':':case';':if(str.charAt(s++)=='-')
tzSign=(-1);tzOff=Number(str.charAt(s));if((ch=='+')||(ch==':')||((s+3<slen)&&(String(Number(str.charAt(s+3)))!==str.charAt(s+3))))
tzOff=(tzOff*10)+Number(str.charAt(++s));tzOff*=60;if((ch==':')||(ch==';'))
s++;tzOff=(tzOff+Number(str.substr(++s,2)))*tzSign;s+=2;break;case'j':case'U':case'u':case'V':case'v':case'X':case'x':throw'%'+this.fmt.charAt(f+1)+' not implemented by AnyTime.Converter';case'%':default:throw'%'+this.fmt.charAt(f+1)+' reserved for future use';break;}
f++;}
else if(this.fmt.charAt(f)!=str.charAt(s))
throw str+' is not in "'+this.fmt+'" format';else
s++;}
if(era<0)
time.setFullYear(0-time.getFullYear());if(tzOff!=Number.MIN_VALUE)
{if(_captureOffset)
_offCap=tzOff;else
time.setTime((time.getTime()-(tzOff*60000))-(time.getTimezoneOffset()*60000));}
return time;};this.setUtcFormatOffsetAlleged=function(offset)
{var prev=_offAl;_offAl=offset;return prev;};this.setUtcFormatOffsetSubIndex=function(subIndex)
{var prev=_offFSI;_offFSI=subIndex;return prev;};(function(_this)
{var i,len;options=jQuery.extend(true,{},options||{});if(options.baseYear)
_this.baseYear=Number(options.baseYear);if(options.format)
_this.fmt=options.format;_flen=_this.fmt.length;if(options.dayAbbreviations)
_this.dAbbr=$.makeArray(options.dayAbbreviations);if(options.dayNames)
{_this.dNames=$.makeArray(options.dayNames);_longDay=1;_shortDay=1000;for(i=0;i<7;i++)
{len=_this.dNames[i].length;if(len>_longDay)
_longDay=len;if(len<_shortDay)
_shortDay=len;}}
if(options.eraAbbreviations)
_this.eAbbr=$.makeArray(options.eraAbbreviations);if(options.monthAbbreviations)
_this.mAbbr=$.makeArray(options.monthAbbreviations);if(options.monthNames)
{_this.mNames=$.makeArray(options.monthNames);_longMon=1;_shortMon=1000;for(i=0;i<12;i++)
{len=_this.mNames[i].length;if(len>_longMon)
_longMon=len;if(len<_shortMon)
_shortMon=len;}}
if(typeof options.utcFormatOffsetImposed!="undefined")
_offF=options.utcFormatOffsetImposed;if(typeof options.utcParseOffsetAssumed!="undefined")
_offP=options.utcParseOffsetAssumed;if(options.utcParseOffsetCapture)
_captureOffset=true;})(this);};AnyTime.noPicker=function(id)
{if(__pickers[id])
{__pickers[id].cleanup();delete __pickers[id];}};AnyTime.picker=function(id,options)
{if(__pickers[id])
throw'Cannot create another AnyTime picker for "'+id+'"';var _this=null;__pickers[id]={twelveHr:false,ajaxOpts:null,denyTab:true,askEra:false,cloak:null,conv:null,bMinW:0,bMinH:0,dMinW:0,dMinH:0,div:null,dB:null,dD:null,dY:null,dMo:null,dDoM:null,hDoM:null,hMo:null,hTitle:null,hY:null,dT:null,dH:null,dM:null,dS:null,dO:null,earliest:null,fBtn:null,fDOW:0,hBlur:null,hClick:null,hFocus:null,hKeydown:null,hKeypress:null,id:null,inp:null,latest:null,lastAjax:null,lostFocus:false,lX:'X',lY:'Year',lO:'Time Zone',oBody:null,oConv:null,oCur:null,oDiv:null,oLab:null,oListMinW:0,oMinW:0,oSel:null,offMin:Number.MIN_VALUE,offSI:-1,offStr:"",pop:true,time:null,tMinW:0,tMinH:0,url:null,wMinW:0,wMinH:0,yAhead:null,y0XXX:null,yCur:null,yDiv:null,yLab:null,yNext:null,yPast:null,yPrior:null,initialize:function(id)
{_this=this;this.id='AnyTime--'+id.replace(/[^-_.A-Za-z0-9]/g,'--AnyTime--');options=jQuery.extend(true,{},options||{});options.utcParseOffsetCapture=true;this.conv=new AnyTime.Converter(options);if(options.placement)
{if(options.placement=='inline')
this.pop=false;else if(options.placement!='popup')
throw'unknown placement: '+options.placement;}
if(options.ajaxOptions)
{this.ajaxOpts=jQuery.extend({},options.ajaxOptions);if(!this.ajaxOpts.success)
this.ajaxOpts.success=function(data,status){_this.inp.val(data);};}
if(options.earliest)
{if(typeof options.earliest.getTime=='function')
this.earliest=options.earliest.getTime();else
this.earliest=this.conv.parse(options.earliest.toString());}
if(options.firstDOW)
{if((options.firstDOW<0)||(options.firstDOW>6))
throw new Exception('illegal firstDOW: '+options.firstDOW);this.fDOW=options.firstDOW;}
if(options.latest)
{if(typeof options.latest.getTime=='function')
this.latest=options.latest.getTime();else
this.latest=this.conv.parse(options.latest.toString());}
this.lX=options.labelDismiss||'X';this.lY=options.labelYear||'Year';this.lO=options.labelTimeZone||'Time Zone';var i;var t;var lab;var shownFields=0;var format=this.conv.fmt;if(typeof options.askEra!='undefined')
this.askEra=options.askEra;else
this.askEra=(format.indexOf('%B')>=0)||(format.indexOf('%C')>=0)||(format.indexOf('%E')>=0);var askYear=(format.indexOf('%Y')>=0)||(format.indexOf('%y')>=0)||(format.indexOf('%Z')>=0)||(format.indexOf('%z')>=0);var askMonth=(format.indexOf('%b')>=0)||(format.indexOf('%c')>=0)||(format.indexOf('%M')>=0)||(format.indexOf('%m')>=0);var askDoM=(format.indexOf('%D')>=0)||(format.indexOf('%d')>=0)||(format.indexOf('%e')>=0);var askDate=askYear||askMonth||askDoM;this.twelveHr=(format.indexOf('%h')>=0)||(format.indexOf('%I')>=0)||(format.indexOf('%l')>=0)||(format.indexOf('%r')>=0);var askHour=this.twelveHr||(format.indexOf('%H')>=0)||(format.indexOf('%k')>=0)||(format.indexOf('%T')>=0);var askMinute=(format.indexOf('%i')>=0)||(format.indexOf('%r')>=0)||(format.indexOf('%T')>=0);var askSec=((format.indexOf('%r')>=0)||(format.indexOf('%S')>=0)||(format.indexOf('%s')>=0)||(format.indexOf('%T')>=0));if(askSec&&(typeof options.askSecond!='undefined'))
askSec=options.askSecond;var askOff=((format.indexOf('%#')>=0)||(format.indexOf('%+')>=0)||(format.indexOf('%-')>=0)||(format.indexOf('%:')>=0)||(format.indexOf('%;')>=0)||(format.indexOf('%<')>=0)||(format.indexOf('%>')>=0)||(format.indexOf('%@')>=0));var askTime=askHour||askMinute||askSec||askOff;if(askOff)
this.oConv=new AnyTime.Converter({format:options.formatUtcOffset||format.match(/\S*%[-+:;<>#@]\S*/g).join(' ')});this.inp=$(document.getElementById(id));this.div=$('<div class="AnyTime-win AnyTime-pkr ui-widget ui-widget-content ui-corner-all" style="width:0;height:0" id="'+this.id+'" aria-live="off"/>');this.inp.after(this.div);this.wMinW=this.div.outerWidth(!$.browser.safari);this.wMinH=this.div.AnyTime_height(true);this.hTitle=$('<h5 class="AnyTime-hdr ui-widget-header ui-corner-top"/>');this.div.append(this.hTitle);this.dB=$('<div class="AnyTime-body" style="width:0;height:0"/>');this.div.append(this.dB);this.bMinW=this.dB.outerWidth(true);this.bMinH=this.dB.AnyTime_height(true);if(options.hideInput)
this.inp.css({border:0,height:'1px',margin:0,padding:0,width:'1px'});t=null;var xDiv=null;if(this.pop)
{xDiv=$('<div class="AnyTime-x-btn ui-state-default">'+this.lX+'</div>');this.hTitle.append(xDiv);xDiv.click(function(e){_this.dismiss(e);});}
lab='';if(askDate)
{this.dD=$('<div class="AnyTime-date" style="width:0;height:0"/>');this.dB.append(this.dD);this.dMinW=this.dD.outerWidth(true);this.dMinH=this.dD.AnyTime_height(true);if(askYear)
{this.yLab=$('<h6 class="AnyTime-lbl AnyTime-lbl-yr">'+this.lY+'</h6>');this.dD.append(this.yLab);this.dY=$('<ul class="AnyTime-yrs ui-helper-reset" />');this.dD.append(this.dY);this.yPast=this.btn(this.dY,'<',this.newYear,['yrs-past'],'- '+this.lY);this.yPrior=this.btn(this.dY,'1',this.newYear,['yr-prior'],'-1 '+this.lY);this.yCur=this.btn(this.dY,'2',this.newYear,['yr-cur'],this.lY);this.yCur.removeClass('ui-state-default');this.yCur.addClass('AnyTime-cur-btn ui-state-default ui-state-highlight');this.yNext=this.btn(this.dY,'3',this.newYear,['yr-next'],'+1 '+this.lY);this.yAhead=this.btn(this.dY,'>',this.newYear,['yrs-ahead'],'+ '+this.lY);shownFields++;}
if(askMonth)
{lab=options.labelMonth||'Month';this.hMo=$('<h6 class="AnyTime-lbl AnyTime-lbl-month">'+lab+'</h6>');this.dD.append(this.hMo);this.dMo=$('<ul class="AnyTime-mons" />');this.dD.append(this.dMo);for(i=0;i<12;i++)
{var mBtn=this.btn(this.dMo,this.conv.mAbbr[i],function(event)
{var elem=$(event.target);if(elem.hasClass("AnyTime-out-btn"))
return;var mo=event.target.AnyTime_month;var t=new Date(this.time.getTime());if(t.getDate()>__daysIn[mo])
t.setDate(__daysIn[mo])
t.setMonth(mo);this.set(t);this.upd(elem);},['mon','mon'+String(i+1)],lab+' '+this.conv.mNames[i]);mBtn[0].AnyTime_month=i;}
shownFields++;}
if(askDoM)
{lab=options.labelDayOfMonth||'Day of Month';this.hDoM=$('<h6 class="AnyTime-lbl AnyTime-lbl-dom">'+lab+'</h6>');this.dD.append(this.hDoM);this.dDoM=$('<table border="0" cellpadding="0" cellspacing="0" class="AnyTime-dom-table"/>');this.dD.append(this.dDoM);t=$('<thead class="AnyTime-dom-head"/>');this.dDoM.append(t);var tr=$('<tr class="AnyTime-dow"/>');t.append(tr);for(i=0;i<7;i++)
tr.append('<th class="AnyTime-dow AnyTime-dow'+String(i+1)+'">'+this.conv.dAbbr[(this.fDOW+i)%7]+'</th>');var tbody=$('<tbody class="AnyTime-dom-body" />');this.dDoM.append(tbody);for(var r=0;r<6;r++)
{tr=$('<tr class="AnyTime-wk AnyTime-wk'+String(r+1)+'"/>');tbody.append(tr);for(i=0;i<7;i++)
this.btn(tr,'x',function(event)
{var elem=$(event.target);if(elem.hasClass("AnyTime-out-btn"))
return;var dom=Number(elem.html());if(dom)
{var t=new Date(this.time.getTime());t.setDate(dom);this.set(t);this.upd(elem);}},['dom'],lab);}
shownFields++;}}
if(askTime)
{var tensDiv,onesDiv;this.dT=$('<div class="AnyTime-time" style="width:0;height:0" />');this.dB.append(this.dT);this.tMinW=this.dT.outerWidth(true);this.tMinH=this.dT.AnyTime_height(true);if(askHour)
{this.dH=$('<div class="AnyTime-hrs"/>');this.dT.append(this.dH);lab=options.labelHour||'Hour';this.dH.append($('<h6 class="AnyTime-lbl AnyTime-lbl-hr">'+lab+'</h6>'));var amDiv=$('<ul class="AnyTime-hrs-am"/>');this.dH.append(amDiv);var pmDiv=$('<ul class="AnyTime-hrs-pm"/>');this.dH.append(pmDiv);for(i=0;i<12;i++)
{if(this.twelveHr)
{if(i==0)
t='12am';else
t=String(i)+'am';}
else
t=AnyTime.pad(i,2);this.btn(amDiv,t,this.newHour,['hr','hr'+String(i)],lab+' '+t);if(this.twelveHr)
{if(i==0)
t='12pm';else
t=String(i)+'pm';}
else
t=i+12;this.btn(pmDiv,t,this.newHour,['hr','hr'+String(i+12)],lab+' '+t);}
shownFields++;}
if(askMinute)
{this.dM=$('<div class="AnyTime-mins"/>');this.dT.append(this.dM);lab=options.labelMinute||'Minute';this.dM.append($('<h6 class="AnyTime-lbl AnyTime-lbl-min">'+lab+'</h6>'));tensDiv=$('<ul class="AnyTime-mins-tens"/>');this.dM.append(tensDiv);for(i=0;i<6;i++)
this.btn(tensDiv,i,function(event)
{var elem=$(event.target);if(elem.hasClass("AnyTime-out-btn"))
return;var t=new Date(this.time.getTime());t.setMinutes((Number(elem.text())*10)+(this.time.getMinutes()%10));this.set(t);this.upd(elem);},['min-ten','min'+i+'0'],lab+' '+i+'0');for(;i<12;i++)
this.btn(tensDiv,' ',$.noop,['min-ten','min'+i+'0'],lab+' '+i+'0').addClass('AnyTime-min-ten-btn-empty ui-state-default ui-state-disabled');onesDiv=$('<ul class="AnyTime-mins-ones"/>');this.dM.append(onesDiv);for(i=0;i<10;i++)
this.btn(onesDiv,i,function(event)
{var elem=$(event.target);if(elem.hasClass("AnyTime-out-btn"))
return;var t=new Date(this.time.getTime());t.setMinutes((Math.floor(this.time.getMinutes()/10)*10)+Number(elem.text()));this.set(t);this.upd(elem);},['min-one','min'+i],lab+' '+i);for(;i<12;i++)
this.btn(onesDiv,' ',$.noop,['min-one','min'+i+'0'],lab+' '+i).addClass('AnyTime-min-one-btn-empty ui-state-default ui-state-disabled');shownFields++;}
if(askSec)
{this.dS=$('<div class="AnyTime-secs"/>');this.dT.append(this.dS);lab=options.labelSecond||'Second';this.dS.append($('<h6 class="AnyTime-lbl AnyTime-lbl-sec">'+lab+'</h6>'));tensDiv=$('<ul class="AnyTime-secs-tens"/>');this.dS.append(tensDiv);for(i=0;i<6;i++)
this.btn(tensDiv,i,function(event)
{var elem=$(event.target);if(elem.hasClass("AnyTime-out-btn"))
return;var t=new Date(this.time.getTime());t.setSeconds((Number(elem.text())*10)+(this.time.getSeconds()%10));this.set(t);this.upd(elem);},['sec-ten','sec'+i+'0'],lab+' '+i+'0');for(;i<12;i++)
this.btn(tensDiv,' ',$.noop,['sec-ten','sec'+i+'0'],lab+' '+i+'0').addClass('AnyTime-sec-ten-btn-empty ui-state-default ui-state-disabled');onesDiv=$('<ul class="AnyTime-secs-ones"/>');this.dS.append(onesDiv);for(i=0;i<10;i++)
this.btn(onesDiv,i,function(event)
{var elem=$(event.target);if(elem.hasClass("AnyTime-out-btn"))
return;var t=new Date(this.time.getTime());t.setSeconds((Math.floor(this.time.getSeconds()/10)*10)+Number(elem.text()));this.set(t);this.upd(elem);},['sec-one','sec'+i],lab+' '+i);for(;i<12;i++)
this.btn(onesDiv,' ',$.noop,['sec-one','sec'+i+'0'],lab+' '+i).addClass('AnyTime-sec-one-btn-empty ui-state-default ui-state-disabled');shownFields++;}
if(askOff)
{this.dO=$('<div class="AnyTime-offs" />');this.dT.append(this.dO);this.oMinW=this.dO.outerWidth(true);this.oLab=$('<h6 class="AnyTime-lbl AnyTime-lbl-off">'+this.lO+'</h6>');this.dO.append(this.oLab);var offDiv=$('<ul class="AnyTime-off-list ui-helper-reset" />');this.dO.append(offDiv);this.oCur=this.btn(offDiv,'',this.newOffset,['off','off-cur'],lab);this.oCur.removeClass('ui-state-default');this.oCur.addClass('AnyTime-cur-btn ui-state-default ui-state-highlight');this.oCur.css({overflow:"hidden"});this.oSel=this.btn(offDiv,'±',this.newOffset,['off','off-select'],'+/- '+this.lO);this.oListMinW=this.oCur.outerWidth(true)+this.oSel.outerWidth(true);shownFields++;}}
if(options.labelTitle)
this.hTitle.append(options.labelTitle);else if(shownFields>1)
this.hTitle.append('Select a '+(askDate?(askTime?'Date and Time':'Date'):'Time'));else
this.hTitle.append('Select');try
{this.time=this.conv.parse(this.inp.val());this.offMin=this.conv.getUtcParseOffsetCaptured();this.offSI=this.conv.getUtcParseOffsetSubIndex();}
catch(e)
{this.time=new Date();}
this.lastAjax=this.time;if(this.pop)
{this.div.hide();if(__iframe)
__iframe.hide();this.div.css('position','absolute');}
this.inp.blur(this.hBlur=function(e)
{_this.inpBlur(e);});this.inp.click(this.hClick=function(e)
{_this.showPkr(e);});this.inp.focus(this.hFocus=function(e)
{if(_this.lostFocus)
_this.showPkr(e);_this.lostFocus=false;});this.inp.keydown(this.hKeydown=function(e)
{_this.key(e);});this.inp.keypress(this.hKeypress=function(e)
{if($.browser.opera&&_this.denyTab)
e.preventDefault();});this.div.click(function(e)
{_this.lostFocus=false;_this.inp.focus();});$(window).resize(function(e)
{_this.pos(e);});if(__initialized)
this.onReady();},ajax:function()
{if(this.ajaxOpts&&(this.time.getTime()!=this.lastAjax.getTime()))
{try
{var opts=jQuery.extend({},this.ajaxOpts);if(typeof opts.data=='object')
opts.data[this.inp[0].name||this.inp[0].id]=this.inp.val();else
{var opt=(this.inp[0].name||this.inp[0].id)+'='+encodeURI(this.inp.val());if(opts.data)
opts.data+='&'+opt;else
opts.data=opt;}
$.ajax(opts);this.lastAjax=this.time;}
catch(e)
{}}
return;},askOffset:function(event)
{if(!this.oDiv)
{this.makeCloak();this.oDiv=$('<div class="AnyTime-win AnyTime-off-selector ui-widget ui-widget-content ui-corner-all" style="position:absolute" />');this.div.append(this.oDiv);var title=$('<h5 class="AnyTime-hdr AnyTime-hdr-off-selector ui-widget-header ui-corner-top" />');this.oDiv.append(title);this.oBody=$('<div class="AnyTime-body AnyTime-body-off-selector" style="overflow:auto;white-space:nowrap" />');this.oDiv.append(this.oBody);var oBHS=this.oBody.AnyTime_height(true);var oBWS=this.oBody.AnyTime_width(true);var oTWS=title.AnyTime_width(true);var xDiv=$('<div class="AnyTime-x-btn ui-state-default">'+this.lX+'</div>');title.append(xDiv);xDiv.click(function(e){_this.dismissODiv(e);});title.append(this.lO);if(__msie6||__msie7)
title.width(String(this.lO.length*0.8)+"em");var oBW=title.AnyTime_width(true)-oBWS;var cont=$('<ul class="AnyTime-off-off" />');var last=null;this.oBody.append(cont);var useSubIndex=(this.oConv.fmt.indexOf('%@')>=0);var btnW=0;if(AnyTime.utcLabel)
for(var o=-720;o<720;o++)
if(AnyTime.utcLabel[o])
{this.oConv.setUtcFormatOffsetAlleged(o);for(var i=0;i<AnyTime.utcLabel[o].length;i++)
{this.oConv.setUtcFormatOffsetSubIndex(i);last=this.btn(cont,this.oConv.format(this.time),this.newOPos,['off-off'],o);last[0].AnyTime_offMin=o;last[0].AnyTime_offSI=i;var w=last.width();if(w>btnW)
btnW=w;if(!useSubIndex)
break;}}
if(last)
last.addClass('AnyTime-off-off-last-btn');this.oBody.find('.AnyTime-off-off-btn').width(btnW);if(last)
{var lW=last.AnyTime_width(true);if(lW>oBW)
oBW=lW+1;}
this.oBody.width(oBW);oBW=this.oBody.AnyTime_width(true);this.oDiv.width(oBW);if(__msie6||__msie7)
title.width(oBW-oTWS);var oH=this.oDiv.AnyTime_height(true);var oHmax=this.div.height()*0.75;if(oH>oHmax)
{oH=oHmax;this.oBody.height(oH-(title.AnyTime_height(true)+oBHS));this.oBody.width(this.oBody.width()+20);this.oDiv.width(this.oDiv.width()+20);if(__msie6||__msie7)
title.width(this.oBody.AnyTime_width(true)-oTWS);}
if(!__msie7)
this.oDiv.height(String(oH)+'px');}
else
{this.cloak.show();this.oDiv.show();}
this.pos(event);this.updODiv(null);var f=this.oDiv.find('.AnyTime-off-off-btn.AnyTime-cur-btn:first');if(!f.length)
f=this.oDiv.find('.AnyTime-off-off-btn:first');this.setFocus(f);},askYear:function(event)
{if(!this.yDiv)
{this.makeCloak();this.yDiv=$('<div class="AnyTime-win AnyTime-yr-selector ui-widget ui-widget-content ui-corner-all" style="position:absolute" />');this.div.append(this.yDiv);var title=$('<h5 class="AnyTime-hdr AnyTime-hdr-yr-selector ui-widget-header ui-corner-top" />');this.yDiv.append(title);var xDiv=$('<div class="AnyTime-x-btn ui-state-default">'+this.lX+'</div>');title.append(xDiv);xDiv.click(function(e){_this.dismissYDiv(e);});title.append(this.lY);var yBody=$('<div class="AnyTime-body AnyTime-body-yr-selector" />');var yW=yBody.AnyTime_width(true);var yH=0;this.yDiv.append(yBody);cont=$('<ul class="AnyTime-yr-mil" />');yBody.append(cont);this.y0XXX=this.btn(cont,0,this.newYPos,['mil','mil0'],this.lY+' '+0+'000');for(i=1;i<10;i++)
this.btn(cont,i,this.newYPos,['mil','mil'+i],this.lY+' '+i+'000');yW+=cont.AnyTime_width(true);if(yH<cont.AnyTime_height(true))
yH=cont.AnyTime_height(true);cont=$('<ul class="AnyTime-yr-cent" />');yBody.append(cont);for(i=0;i<10;i++)
this.btn(cont,i,this.newYPos,['cent','cent'+i],this.lY+' '+i+'00');yW+=cont.AnyTime_width(true);if(yH<cont.AnyTime_height(true))
yH=cont.AnyTime_height(true);cont=$('<ul class="AnyTime-yr-dec" />');yBody.append(cont);for(i=0;i<10;i++)
this.btn(cont,i,this.newYPos,['dec','dec'+i],this.lY+' '+i+'0');yW+=cont.AnyTime_width(true);if(yH<cont.AnyTime_height(true))
yH=cont.AnyTime_height(true);cont=$('<ul class="AnyTime-yr-yr" />');yBody.append(cont);for(i=0;i<10;i++)
this.btn(cont,i,this.newYPos,['yr','yr'+i],this.lY+' '+i);yW+=cont.AnyTime_width(true);if(yH<cont.AnyTime_height(true))
yH=cont.AnyTime_height(true);if(this.askEra)
{cont=$('<ul class="AnyTime-yr-era" />');yBody.append(cont);this.btn(cont,this.conv.eAbbr[0],function(event)
{var t=new Date(this.time.getTime());var year=t.getFullYear();if(year>0)
t.setFullYear(0-year);this.set(t);this.updYDiv($(event.target));},['era','bce'],this.conv.eAbbr[0]);this.btn(cont,this.conv.eAbbr[1],function(event)
{var t=new Date(this.time.getTime());var year=t.getFullYear();if(year<0)
t.setFullYear(0-year);this.set(t);this.updYDiv($(event.target));},['era','ce'],this.conv.eAbbr[1]);yW+=cont.AnyTime_width(true);if(yH<cont.AnyTime_height(true))
yH=cont.AnyTime_height(true);}
if($.browser.msie)
yW+=1;else if($.browser.safari)
yW+=2;yH+=yBody.AnyTime_height(true);yBody.css('width',String(yW)+'px');if(!__msie7)
yBody.css('height',String(yH)+'px');if(__msie6||__msie7)
title.width(yBody.outerWidth(true));yH+=title.AnyTime_height(true);if(title.AnyTime_width(true)>yW)
yW=title.AnyTime_width(true);this.yDiv.css('width',String(yW)+'px');if(!__msie7)
this.yDiv.css('height',String(yH)+'px');}
else
{this.cloak.show();this.yDiv.show();}
this.pos(event);this.updYDiv(null);this.setFocus(this.yDiv.find('.AnyTime-yr-btn.AnyTime-cur-btn:first'));},inpBlur:function(event)
{if(this.oDiv&&this.oDiv.is(":visible"))
{_this.inp.focus();return;}
this.lostFocus=true;setTimeout(function()
{if(_this.lostFocus)
{_this.div.find('.AnyTime-focus-btn').removeClass('AnyTime-focus-btn ui-state-focus');if(_this.pop)
_this.dismiss(event);else
_this.ajax();}},334);},btn:function(parent,text,handler,classes,title)
{var tagName=((parent[0].nodeName.toLowerCase()=='ul')?'li':'td');var div$='<'+tagName+' class="AnyTime-btn';for(var i=0;i<classes.length;i++)
div$+=' AnyTime-'+classes[i]+'-btn';var div=$(div$+' ui-state-default">'+text+'</'+tagName+'>');parent.append(div);div.AnyTime_title=title;div.click(function(e)
{_this.tempFunc=handler;_this.tempFunc(e);});div.dblclick(function(e)
{var elem=$(this);if(elem.is('.AnyTime-off-off-btn'))
_this.dismissODiv(e);else if(elem.is('.AnyTime-mil-btn')||elem.is('.AnyTime-cent-btn')||elem.is('.AnyTime-dec-btn')||elem.is('.AnyTime-yr-btn')||elem.is('.AnyTime-era-btn'))
_this.dismissYDiv(e);else if(_this.pop)
_this.dismiss(e);});return div;},cleanup:function(event)
{this.inp.unbind('blur',this.hBlur);this.inp.unbind('click',this.hClick);this.inp.unbind('focus',this.hFocus);this.inp.unbind('keydown',this.hKeydown);this.inp.unbind('keypress',this.hKeypress);this.div.remove();},dismiss:function(event)
{this.ajax();this.div.hide();if(__iframe)
__iframe.hide();if(this.yDiv)
this.dismissYDiv();if(this.oDiv)
this.dismissODiv();this.lostFocus=true;},dismissODiv:function(event)
{this.oDiv.hide();this.cloak.hide();this.setFocus(this.oCur);},dismissYDiv:function(event)
{this.yDiv.hide();this.cloak.hide();this.setFocus(this.yCur);},setFocus:function(btn)
{if(!btn.hasClass('AnyTime-focus-btn'))
{this.div.find('.AnyTime-focus-btn').removeClass('AnyTime-focus-btn ui-state-focus');this.fBtn=btn;btn.removeClass('ui-state-default ui-state-highlight');btn.addClass('AnyTime-focus-btn ui-state-default ui-state-highlight ui-state-focus');}
if(btn.hasClass('AnyTime-off-off-btn'))
{var oBT=this.oBody.offset().top;var btnT=btn.offset().top;var btnH=btn.AnyTime_height(true);if(btnT-btnH<oBT)
this.oBody.scrollTop(btnT+this.oBody.scrollTop()-(this.oBody.innerHeight()+oBT)+(btnH*2));else if(btnT+btnH>oBT+this.oBody.innerHeight())
this.oBody.scrollTop((btnT+this.oBody.scrollTop())-(oBT+btnH));}},key:function(event)
{var mo;var t=null;var elem=this.div.find('.AnyTime-focus-btn');var key=event.keyCode||event.which;this.denyTab=true;if(key==16)
{}
else if((key==10)||(key==13)||(key==27))
{if(this.oDiv&&this.oDiv.is(':visible'))
this.dismissODiv(event);else if(this.yDiv&&this.yDiv.is(':visible'))
this.dismissYDiv(event);else if(this.pop)
this.dismiss(event);}
else if((key==33)||((key==9)&&event.shiftKey))
{if(this.fBtn.hasClass('AnyTime-off-off-btn'))
{if(key==9)
this.dismissODiv(event);}
else if(this.fBtn.hasClass('AnyTime-mil-btn'))
{if(key==9)
this.dismissYDiv(event);}
else if(this.fBtn.hasClass('AnyTime-cent-btn'))
this.yDiv.find('.AnyTime-mil-btn.AnyTime-cur-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-dec-btn'))
this.yDiv.find('.AnyTime-cent-btn.AnyTime-cur-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-yr-btn'))
this.yDiv.find('.AnyTime-dec-btn.AnyTime-cur-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-era-btn'))
this.yDiv.find('.AnyTime-yr-btn.AnyTime-cur-btn').triggerHandler('click');else if(this.fBtn.parents('.AnyTime-yrs').length)
{if(key==9)
{this.denyTab=false;return;}}
else if(this.fBtn.hasClass('AnyTime-mon-btn'))
{if(this.dY)
this.yCur.triggerHandler('click');else if(key==9)
{this.denyTab=false;return;}}
else if(this.fBtn.hasClass('AnyTime-dom-btn'))
{if((key==9)&&event.shiftKey)
{this.denyTab=false;return;}
else
{t=new Date(this.time.getTime());if(event.shiftKey)
t.setFullYear(t.getFullYear()-1);else
{mo=t.getMonth()-1;if(t.getDate()>__daysIn[mo])
t.setDate(__daysIn[mo])
t.setMonth(mo);}
this.keyDateChange(t);}}
else if(this.fBtn.hasClass('AnyTime-hr-btn'))
{t=this.dDoM||this.dMo;if(t)
t.AnyTime_clickCurrent();else if(this.dY)
this.yCur.triggerHandler('click');else if(key==9)
{this.denyTab=false;return;}}
else if(this.fBtn.hasClass('AnyTime-min-ten-btn'))
{t=this.dH||this.dDoM||this.dMo;if(t)
t.AnyTime_clickCurrent();else if(this.dY)
this.yCur.triggerHandler('click');else if(key==9)
{this.denyTab=false;return;}}
else if(this.fBtn.hasClass('AnyTime-min-one-btn'))
this.dM.AnyTime_clickCurrent();else if(this.fBtn.hasClass('AnyTime-sec-ten-btn'))
{if(this.dM)
t=this.dM.find('.AnyTime-mins-ones');else
t=this.dH||this.dDoM||this.dMo;if(t)
t.AnyTime_clickCurrent();else if(this.dY)
this.yCur.triggerHandler('click');else if(key==9)
{this.denyTab=false;return;}}
else if(this.fBtn.hasClass('AnyTime-sec-one-btn'))
this.dS.AnyTime_clickCurrent();else if(this.fBtn.hasClass('AnyTime-off-btn'))
{if(this.dS)
t=this.dS.find('.AnyTime-secs-ones');else if(this.dM)
t=this.dM.find('.AnyTime-mins-ones');else
t=this.dH||this.dDoM||this.dMo;if(t)
t.AnyTime_clickCurrent();else if(this.dY)
this.yCur.triggerHandler('click');else if(key==9)
{this.denyTab=false;return;}}}
else if((key==34)||(key==9))
{if(this.fBtn.hasClass('AnyTime-mil-btn'))
this.yDiv.find('.AnyTime-cent-btn.AnyTime-cur-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-cent-btn'))
this.yDiv.find('.AnyTime-dec-btn.AnyTime-cur-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-dec-btn'))
this.yDiv.find('.AnyTime-yr-btn.AnyTime-cur-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-yr-btn'))
{t=this.yDiv.find('.AnyTime-era-btn.AnyTime-cur-btn');if(t.length)
t.triggerHandler('click');else if(key==9)
this.dismissYDiv(event);}
else if(this.fBtn.hasClass('AnyTime-era-btn'))
{if(key==9)
this.dismissYDiv(event);}
else if(this.fBtn.hasClass('AnyTime-off-off-btn'))
{if(key==9)
this.dismissODiv(event);}
else if(this.fBtn.parents('.AnyTime-yrs').length)
{t=this.dDoM||this.dMo||this.dH||this.dM||this.dS||this.dO;if(t)
t.AnyTime_clickCurrent();else if(key==9)
{this.denyTab=false;return;}}
else if(this.fBtn.hasClass('AnyTime-mon-btn'))
{t=this.dDoM||this.dH||this.dM||this.dS||this.dO;if(t)
t.AnyTime_clickCurrent();else if(key==9)
{this.denyTab=false;return;}}
else if(this.fBtn.hasClass('AnyTime-dom-btn'))
{if(key==9)
{t=this.dH||this.dM||this.dS||this.dO;if(t)
t.AnyTime_clickCurrent();else
{this.denyTab=false;return;}}
else
{t=new Date(this.time.getTime());if(event.shiftKey)
t.setFullYear(t.getFullYear()+1);else
{mo=t.getMonth()+1;if(t.getDate()>__daysIn[mo])
t.setDate(__daysIn[mo])
t.setMonth(mo);}
this.keyDateChange(t);}}
else if(this.fBtn.hasClass('AnyTime-hr-btn'))
{t=this.dM||this.dS||this.dO;if(t)
t.AnyTime_clickCurrent();else if(key==9)
{this.denyTab=false;return;}}
else if(this.fBtn.hasClass('AnyTime-min-ten-btn'))
this.dM.find('.AnyTime-mins-ones .AnyTime-cur-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-min-one-btn'))
{t=this.dS||this.dO;if(t)
t.AnyTime_clickCurrent();else if(key==9)
{this.denyTab=false;return;}}
else if(this.fBtn.hasClass('AnyTime-sec-ten-btn'))
this.dS.find('.AnyTime-secs-ones .AnyTime-cur-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-sec-one-btn'))
{if(this.dO)
this.dO.AnyTime_clickCurrent();else if(key==9)
{this.denyTab=false;return;}}
else if(this.fBtn.hasClass('AnyTime-off-btn'))
{if(key==9)
{this.denyTab=false;return;}}}
else if(key==35)
{if(this.fBtn.hasClass('AnyTime-mil-btn')||this.fBtn.hasClass('AnyTime-cent-btn')||this.fBtn.hasClass('AnyTime-dec-btn')||this.fBtn.hasClass('AnyTime-yr-btn')||this.fBtn.hasClass('AnyTime-era-btn'))
{t=this.yDiv.find('.AnyTime-ce-btn');if(!t.length)
t=this.yDiv.find('.AnyTime-yr9-btn');t.triggerHandler('click');}
else if(this.fBtn.hasClass('AnyTime-dom-btn'))
{t=new Date(this.time.getTime());t.setDate(1);t.setMonth(t.getMonth()+1);t.setDate(t.getDate()-1);if(event.ctrlKey)
t.setMonth(11);this.keyDateChange(t);}
else if(this.dS)
this.dS.find('.AnyTime-sec9-btn').triggerHandler('click');else if(this.dM)
this.dM.find('.AnyTime-min9-btn').triggerHandler('click');else if(this.dH)
this.dH.find('.AnyTime-hr23-btn').triggerHandler('click');else if(this.dDoM)
this.dDoM.find('.AnyTime-dom-btn-filled:last').triggerHandler('click');else if(this.dMo)
this.dMo.find('.AnyTime-mon12-btn').triggerHandler('click');else if(this.dY)
this.yAhead.triggerHandler('click');}
else if(key==36)
{if(this.fBtn.hasClass('AnyTime-mil-btn')||this.fBtn.hasClass('AnyTime-cent-btn')||this.fBtn.hasClass('AnyTime-dec-btn')||this.fBtn.hasClass('AnyTime-yr-btn')||this.fBtn.hasClass('AnyTime-era-btn'))
{this.yDiv.find('.AnyTime-mil0-btn').triggerHandler('click');}
else if(this.fBtn.hasClass('AnyTime-dom-btn'))
{t=new Date(this.time.getTime());t.setDate(1);if(event.ctrlKey)
t.setMonth(0);this.keyDateChange(t);}
else if(this.dY)
this.yCur.triggerHandler('click');else if(this.dMo)
this.dMo.find('.AnyTime-mon1-btn').triggerHandler('click');else if(this.dDoM)
this.dDoM.find('.AnyTime-dom-btn-filled:first').triggerHandler('click');else if(this.dH)
this.dH.find('.AnyTime-hr0-btn').triggerHandler('click');else if(this.dM)
this.dM.find('.AnyTime-min00-btn').triggerHandler('click');else if(this.dS)
this.dS.find('.AnyTime-sec00-btn').triggerHandler('click');}
else if(key==37)
{if(this.fBtn.hasClass('AnyTime-dom-btn'))
this.keyDateChange(new Date(this.time.getTime()-__oneDay));else
this.keyBack();}
else if(key==38)
{if(this.fBtn.hasClass('AnyTime-dom-btn'))
this.keyDateChange(new Date(this.time.getTime()-(7*__oneDay)));else
this.keyBack();}
else if(key==39)
{if(this.fBtn.hasClass('AnyTime-dom-btn'))
this.keyDateChange(new Date(this.time.getTime()+__oneDay));else
this.keyAhead();}
else if(key==40)
{if(this.fBtn.hasClass('AnyTime-dom-btn'))
this.keyDateChange(new Date(this.time.getTime()+(7*__oneDay)));else
this.keyAhead();}
else if(((key==86)||(key==118))&&event.ctrlKey)
{this.inp.val("").change();var _this=this;setTimeout(function(){_this.showPkr(null);},100);return;}
else
return;event.preventDefault();},keyAhead:function()
{if(this.fBtn.hasClass('AnyTime-mil9-btn'))
this.yDiv.find('.AnyTime-cent0-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-cent9-btn'))
this.yDiv.find('.AnyTime-dec0-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-dec9-btn'))
this.yDiv.find('.AnyTime-yr0-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-yr9-btn'))
this.yDiv.find('.AnyTime-bce-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-sec9-btn'))
{}
else if(this.fBtn.hasClass('AnyTime-sec50-btn'))
this.dS.find('.AnyTime-sec0-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-min9-btn'))
{if(this.dS)
this.dS.find('.AnyTime-sec00-btn').triggerHandler('click');}
else if(this.fBtn.hasClass('AnyTime-min50-btn'))
this.dM.find('.AnyTime-min0-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-hr23-btn'))
{if(this.dM)
this.dM.find('.AnyTime-min00-btn').triggerHandler('click');else if(this.dS)
this.dS.find('.AnyTime-sec00-btn').triggerHandler('click');}
else if(this.fBtn.hasClass('AnyTime-hr11-btn'))
this.dH.find('.AnyTime-hr12-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-mon12-btn'))
{if(this.dDoM)
this.dDoM.AnyTime_clickCurrent();else if(this.dH)
this.dH.find('.AnyTime-hr0-btn').triggerHandler('click');else if(this.dM)
this.dM.find('.AnyTime-min00-btn').triggerHandler('click');else if(this.dS)
this.dS.find('.AnyTime-sec00-btn').triggerHandler('click');}
else if(this.fBtn.hasClass('AnyTime-yrs-ahead-btn'))
{if(this.dMo)
this.dMo.find('.AnyTime-mon1-btn').triggerHandler('click');else if(this.dH)
this.dH.find('.AnyTime-hr0-btn').triggerHandler('click');else if(this.dM)
this.dM.find('.AnyTime-min00-btn').triggerHandler('click');else if(this.dS)
this.dS.find('.AnyTime-sec00-btn').triggerHandler('click');}
else if(this.fBtn.hasClass('AnyTime-yr-cur-btn'))
this.yNext.triggerHandler('click');else
this.fBtn.next().triggerHandler('click');},keyBack:function()
{if(this.fBtn.hasClass('AnyTime-cent0-btn'))
this.yDiv.find('.AnyTime-mil9-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-dec0-btn'))
this.yDiv.find('.AnyTime-cent9-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-yr0-btn'))
this.yDiv.find('.AnyTime-dec9-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-bce-btn'))
this.yDiv.find('.AnyTime-yr9-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-yr-cur-btn'))
this.yPrior.triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-mon1-btn'))
{if(this.dY)
this.yCur.triggerHandler('click');}
else if(this.fBtn.hasClass('AnyTime-hr0-btn'))
{if(this.dDoM)
this.dDoM.AnyTime_clickCurrent();else if(this.dMo)
this.dMo.find('.AnyTime-mon12-btn').triggerHandler('click');else if(this.dY)
this.yNext.triggerHandler('click');}
else if(this.fBtn.hasClass('AnyTime-hr12-btn'))
this.dH.find('.AnyTime-hr11-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-min00-btn'))
{if(this.dH)
this.dH.find('.AnyTime-hr23-btn').triggerHandler('click');else if(this.dDoM)
this.dDoM.AnyTime_clickCurrent();else if(this.dMo)
this.dMo.find('.AnyTime-mon12-btn').triggerHandler('click');else if(this.dY)
this.yNext.triggerHandler('click');}
else if(this.fBtn.hasClass('AnyTime-min0-btn'))
this.dM.find('.AnyTime-min50-btn').triggerHandler('click');else if(this.fBtn.hasClass('AnyTime-sec00-btn'))
{if(this.dM)
this.dM.find('.AnyTime-min9-btn').triggerHandler('click');else if(this.dH)
this.dH.find('.AnyTime-hr23-btn').triggerHandler('click');else if(this.dDoM)
this.dDoM.AnyTime_clickCurrent();else if(this.dMo)
this.dMo.find('.AnyTime-mon12-btn').triggerHandler('click');else if(this.dY)
this.yNext.triggerHandler('click');}
else if(this.fBtn.hasClass('AnyTime-sec0-btn'))
this.dS.find('.AnyTime-sec50-btn').triggerHandler('click');else
this.fBtn.prev().triggerHandler('click');},keyDateChange:function(newDate)
{if(this.fBtn.hasClass('AnyTime-dom-btn'))
{this.set(newDate);this.upd(null);this.setFocus(this.dDoM.find('.AnyTime-cur-btn'));}},makeCloak:function()
{if(!this.cloak)
{this.cloak=$('<div class="AnyTime-cloak" style="position:absolute" />');this.div.append(this.cloak);this.cloak.click(function(e)
{if(_this.oDiv&&_this.oDiv.is(":visible"))
_this.dismissODiv(e);else
_this.dismissYDiv(e);});}
else
this.cloak.show();},newHour:function(event)
{var h;var t;var elem=$(event.target);if(elem.hasClass("AnyTime-out-btn"))
return;if(!this.twelveHr)
h=Number(elem.text());else
{var str=elem.text();t=str.indexOf('a');if(t<0)
{t=Number(str.substr(0,str.indexOf('p')));h=((t==12)?12:(t+12));}
else
{t=Number(str.substr(0,t));h=((t==12)?0:t);}}
t=new Date(this.time.getTime());t.setHours(h);this.set(t);this.upd(elem);},newOffset:function(event)
{if(event.target==this.oSel[0])
this.askOffset(event);else
{this.upd(this.oCur);}},newOPos:function(event)
{var elem=$(event.target);this.offMin=elem[0].AnyTime_offMin;this.offSI=elem[0].AnyTime_offSI;var t=new Date(this.time.getTime());this.set(t);this.updODiv(elem);},newYear:function(event)
{var elem=$(event.target);if(elem.hasClass("AnyTime-out-btn"))
return;var txt=elem.text();if((txt=='<')||(txt=='<'))
this.askYear(event);else if((txt=='>')||(txt=='>'))
this.askYear(event);else
{var t=new Date(this.time.getTime());t.setFullYear(Number(txt));this.set(t);this.upd(this.yCur);}},newYPos:function(event)
{var elem=$(event.target);if(elem.hasClass("AnyTime-out-btn"))
return;var era=1;var year=this.time.getFullYear();if(year<0)
{era=(-1);year=0-year;}
year=AnyTime.pad(year,4);if(elem.hasClass('AnyTime-mil-btn'))
year=elem.html()+year.substring(1,4);else if(elem.hasClass('AnyTime-cent-btn'))
year=year.substring(0,1)+elem.html()+year.substring(2,4);else if(elem.hasClass('AnyTime-dec-btn'))
year=year.substring(0,2)+elem.html()+year.substring(3,4);else
year=year.substring(0,3)+elem.html();if(year=='0000')
year=1;var t=new Date(this.time.getTime());t.setFullYear(era*year);this.set(t);this.updYDiv(elem);},onReady:function()
{this.lostFocus=true;if(!this.pop)
this.upd(null);else
{if(this.div.parent()!=document.body)
this.div.appendTo(document.body);}},pos:function(event)
{if(this.pop)
{var off=this.inp.offset();var bodyWidth=$(document.body).outerWidth(true);var pickerWidth=this.div.outerWidth(true);var left=off.left;if(left+pickerWidth>bodyWidth-20)
left=bodyWidth-(pickerWidth+20);var top=off.top-this.div.outerHeight(true);if(top<0)
top=off.top+this.inp.outerHeight(true);this.div.css({top:String(top)+'px',left:String(left<0?0:left)+'px'});}
var wOff=this.div.offset();if(this.oDiv&&this.oDiv.is(":visible"))
{var oOff=this.oLab.offset();if(this.div.css('position')=='absolute')
{oOff.top-=wOff.top;oOff.left=oOff.left-wOff.left;wOff={top:0,left:0};}
var oW=this.oDiv.AnyTime_width(true);var wW=this.div.AnyTime_width(true);if(oOff.left+oW>wOff.left+wW)
{oOff.left=(wOff.left+wW)-oW;if(oOff.left<2)
oOff.left=2;}
var oH=this.oDiv.AnyTime_height(true);var wH=this.div.AnyTime_height(true);oOff.top+=this.oLab.AnyTime_height(true);if(oOff.top+oH>wOff.top+wH)
oOff.top=oOff.top-oH;if(oOff.top<wOff.top)
oOff.top=wOff.top;this.oDiv.css({top:oOff.top+'px',left:oOff.left+'px'});}
else if(this.yDiv&&this.yDiv.is(":visible"))
{var yOff=this.yLab.offset();if(this.div.css('position')=='absolute')
{yOff.top-=wOff.top;yOff.left=yOff.left-wOff.left;wOff={top:0,left:0};}
yOff.left+=((this.yLab.outerWidth(true)-this.yDiv.outerWidth(true))/2);this.yDiv.css({top:yOff.top+'px',left:yOff.left+'px'});}
if(this.cloak)
this.cloak.css({top:wOff.top+'px',left:wOff.left+'px',height:String(this.div.outerHeight(true)-2)+'px',width:String(this.div.outerWidth(!$.browser.safari)-2)+'px'});},set:function(newTime)
{var t=newTime.getTime();if(this.earliest&&(t<this.earliest))
this.time=new Date(this.earliest);else if(this.latest&&(t>this.latest))
this.time=new Date(this.latest);else
this.time=newTime;},showPkr:function(event)
{try
{this.time=this.conv.parse(this.inp.val());this.offMin=this.conv.getUtcParseOffsetCaptured();this.offSI=this.conv.getUtcParseOffsetSubIndex();}
catch(e)
{this.time=new Date();}
this.set(this.time);this.upd(null);fBtn=null;var cb='.AnyTime-cur-btn:first';if(this.dDoM)
fBtn=this.dDoM.find(cb);else if(this.yCur)
fBtn=this.yCur;else if(this.dMo)
fBtn=this.dMo.find(cb);else if(this.dH)
fBtn=this.dH.find(cb);else if(this.dM)
fBtn=this.dM.find(cb);else if(this.dS)
fBtn=this.dS.find(cb);this.setFocus(fBtn);this.pos(event);if(this.pop&&__iframe)
setTimeout(function()
{var pos=_this.div.offset();__iframe.css({height:String(_this.div.outerHeight(true))+'px',left:String(pos.left)+'px',position:'absolute',top:String(pos.top)+'px',width:String(_this.div.outerWidth(true))+'px'});__iframe.show();},300);},upd:function(fBtn)
{var cmpLo=new Date(this.time.getTime());cmpLo.setMonth(0,1);cmpLo.setHours(0,0,0,0);var cmpHi=new Date(this.time.getTime());cmpHi.setMonth(11,31);cmpHi.setHours(23,59,59,999);var current=this.time.getFullYear();if(this.earliest&&this.yPast)
{cmpHi.setYear(current-2);if(cmpHi.getTime()<this.earliest)
this.yPast.addClass('AnyTime-out-btn ui-state-disabled');else
this.yPast.removeClass('AnyTime-out-btn ui-state-disabled');}
if(this.yPrior)
{this.yPrior.text(AnyTime.pad((current==1)?(-1):(current-1),4));if(this.earliest)
{cmpHi.setYear(current-1);if(cmpHi.getTime()<this.earliest)
this.yPrior.addClass('AnyTime-out-btn ui-state-disabled');else
this.yPrior.removeClass('AnyTime-out-btn ui-state-disabled');}}
if(this.yCur)
this.yCur.text(AnyTime.pad(current,4));if(this.yNext)
{this.yNext.text(AnyTime.pad((current==-1)?1:(current+1),4));if(this.latest)
{cmpLo.setYear(current+1);if(cmpLo.getTime()>this.latest)
this.yNext.addClass('AnyTime-out-btn ui-state-disabled');else
this.yNext.removeClass('AnyTime-out-btn ui-state-disabled');}}
if(this.latest&&this.yAhead)
{cmpLo.setYear(current+2);if(cmpLo.getTime()>this.latest)
this.yAhead.addClass('AnyTime-out-btn ui-state-disabled');else
this.yAhead.removeClass('AnyTime-out-btn ui-state-disabled');}
cmpLo.setFullYear(this.time.getFullYear());cmpHi.setFullYear(this.time.getFullYear());var i=0;current=this.time.getMonth();$('#'+this.id+' .AnyTime-mon-btn').each(function()
{cmpLo.setMonth(i);cmpHi.setDate(1);cmpHi.setMonth(i+1);cmpHi.setDate(0);$(this).AnyTime_current(i==current,((!_this.earliest)||(cmpHi.getTime()>=_this.earliest))&&((!_this.latest)||(cmpLo.getTime()<=_this.latest)));i++;});cmpLo.setFullYear(this.time.getFullYear());cmpHi.setFullYear(this.time.getFullYear());cmpLo.setMonth(this.time.getMonth());cmpHi.setMonth(this.time.getMonth(),1);current=this.time.getDate();var currentMonth=this.time.getMonth();var dow1=cmpLo.getDay();if(this.fDOW>dow1)
dow1+=7;var wom=0,dow=0;$('#'+this.id+' .AnyTime-wk').each(function()
{dow=_this.fDOW;$(this).children().each(function()
{if(dow-_this.fDOW<7)
{var td=$(this);if(((wom==0)&&(dow<dow1))||(cmpLo.getMonth()!=currentMonth))
{td.html(' ');td.removeClass('AnyTime-dom-btn-filled AnyTime-cur-btn ui-state-default ui-state-highlight');td.addClass('AnyTime-dom-btn-empty');if(wom)
{if((cmpLo.getDate()==1)&&(dow!=0))
td.addClass('AnyTime-dom-btn-empty-after-filled');else
td.removeClass('AnyTime-dom-btn-empty-after-filled');if(cmpLo.getDate()<=7)
td.addClass('AnyTime-dom-btn-empty-below-filled');else
td.removeClass('AnyTime-dom-btn-empty-below-filled');cmpLo.setDate(cmpLo.getDate()+1);cmpHi.setDate(cmpHi.getDate()+1);}
else
{td.addClass('AnyTime-dom-btn-empty-above-filled');if(dow==dow1-1)
td.addClass('AnyTime-dom-btn-empty-before-filled');else
td.removeClass('AnyTime-dom-btn-empty-before-filled');}
td.addClass('ui-state-default ui-state-disabled');}
else
{i=cmpLo.getDate();td.text(i);td.removeClass('AnyTime-dom-btn-empty AnyTime-dom-btn-empty-above-filled AnyTime-dom-btn-empty-before-filled '+'AnyTime-dom-btn-empty-after-filled AnyTime-dom-btn-empty-below-filled '+'ui-state-default ui-state-disabled');td.addClass('AnyTime-dom-btn-filled ui-state-default');td.AnyTime_current(i==current,((!_this.earliest)||(cmpHi.getTime()>=_this.earliest))&&((!_this.latest)||(cmpLo.getTime()<=_this.latest)));cmpLo.setDate(i+1);cmpHi.setDate(i+1);}}
dow++;});wom++;});cmpLo.setFullYear(this.time.getFullYear());cmpHi.setFullYear(this.time.getFullYear());cmpLo.setMonth(this.time.getMonth(),this.time.getDate());cmpHi.setMonth(this.time.getMonth(),this.time.getDate());var not12=!this.twelveHr;var hr=this.time.getHours();$('#'+this.id+' .AnyTime-hr-btn').each(function()
{var html=this.innerHTML;var i;if(not12)
i=Number(html);else
{i=Number(html.substring(0,html.length-2));if(html.charAt(html.length-2)=='a')
{if(i==12)
i=0;}
else if(i<12)
i+=12;}
cmpLo.setHours(i);cmpHi.setHours(i);$(this).AnyTime_current(hr==i,((!_this.earliest)||(cmpHi.getTime()>=_this.earliest))&&((!_this.latest)||(cmpLo.getTime()<=_this.latest)));if(i<23)
cmpLo.setHours(cmpLo.getHours()+1);});cmpLo.setHours(this.time.getHours());cmpHi.setHours(this.time.getHours());var units=this.time.getMinutes();var tens=String(Math.floor(units/10));var ones=String(units%10);$('#'+this.id+' .AnyTime-min-ten-btn:not(.AnyTime-min-ten-btn-empty)').each(function()
{$(this).AnyTime_current(this.innerHTML==tens,((!_this.earliest)||(cmpHi.getTime()>=_this.earliest))&&((!_this.latest)||(cmpLo.getTime()<=_this.latest)));if(cmpLo.getMinutes()<50)
{cmpLo.setMinutes(cmpLo.getMinutes()+10);cmpHi.setMinutes(cmpHi.getMinutes()+10);}});cmpLo.setMinutes(Math.floor(this.time.getMinutes()/10)*10);cmpHi.setMinutes(Math.floor(this.time.getMinutes()/10)*10);$('#'+this.id+' .AnyTime-min-one-btn:not(.AnyTime-min-one-btn-empty)').each(function()
{$(this).AnyTime_current(this.innerHTML==ones,((!_this.earliest)||(cmpHi.getTime()>=_this.earliest))&&((!_this.latest)||(cmpLo.getTime()<=_this.latest)));cmpLo.setMinutes(cmpLo.getMinutes()+1);cmpHi.setMinutes(cmpHi.getMinutes()+1);});cmpLo.setMinutes(this.time.getMinutes());cmpHi.setMinutes(this.time.getMinutes());units=this.time.getSeconds();tens=String(Math.floor(units/10));ones=String(units%10);$('#'+this.id+' .AnyTime-sec-ten-btn:not(.AnyTime-sec-ten-btn-empty)').each(function()
{$(this).AnyTime_current(this.innerHTML==tens,((!_this.earliest)||(cmpHi.getTime()>=_this.earliest))&&((!_this.latest)||(cmpLo.getTime()<=_this.latest)));if(cmpLo.getSeconds()<50)
{cmpLo.setSeconds(cmpLo.getSeconds()+10);cmpHi.setSeconds(cmpHi.getSeconds()+10);}});cmpLo.setSeconds(Math.floor(this.time.getSeconds()/10)*10);cmpHi.setSeconds(Math.floor(this.time.getSeconds()/10)*10);$('#'+this.id+' .AnyTime-sec-one-btn:not(.AnyTime-sec-one-btn-empty)').each(function()
{$(this).AnyTime_current(this.innerHTML==ones,((!_this.earliest)||(cmpHi.getTime()>=_this.earliest))&&((!_this.latest)||(cmpLo.getTime()<=_this.latest)));cmpLo.setSeconds(cmpLo.getSeconds()+1);cmpHi.setSeconds(cmpHi.getSeconds()+1);});if(this.oConv)
{this.oConv.setUtcFormatOffsetAlleged(this.offMin);this.oConv.setUtcFormatOffsetSubIndex(this.offSI);var tzs=this.oConv.format(this.time);this.oCur.html(tzs);}
if(fBtn)
this.setFocus(fBtn);this.conv.setUtcFormatOffsetAlleged(this.offMin);this.conv.setUtcFormatOffsetSubIndex(this.offSI);this.inp.val(this.conv.format(this.time)).change();this.div.show();var d,totH=0,totW=0,dYW=0,dMoW=0,dDoMW=0;if(this.dY)
{totW=dYW=this.dY.outerWidth(true);totH=this.yLab.AnyTime_height(true)+this.dY.AnyTime_height(true);}
if(this.dMo)
{dMoW=this.dMo.outerWidth(true);if(dMoW>totW)
totW=dMoW;totH+=this.hMo.AnyTime_height(true)+this.dMo.AnyTime_height(true);}
if(this.dDoM)
{dDoMW=this.dDoM.outerWidth(true);if(dDoMW>totW)
totW=dDoMW;if(__msie6||__msie7)
{if(dMoW>dDoMW)
this.dDoM.css('width',String(dMoW)+'px');else if(dYW>dDoMW)
this.dDoM.css('width',String(dYW)+'px');}
totH+=this.hDoM.AnyTime_height(true)+this.dDoM.AnyTime_height(true);}
if(this.dD)
{this.dD.css({width:String(totW)+'px',height:String(totH)+'px'});totW+=this.dMinW;totH+=this.dMinH;}
var w=0,h=0,timeH=0,timeW=0;if(this.dH)
{w=this.dH.outerWidth(true);timeW+=w+1;h=this.dH.AnyTime_height(true);if(h>timeH)
timeH=h;}
if(this.dM)
{w=this.dM.outerWidth(true);timeW+=w+1;h=this.dM.AnyTime_height(true);if(h>timeH)
timeH=h;}
if(this.dS)
{w=this.dS.outerWidth(true);timeW+=w+1;h=this.dS.AnyTime_height(true);if(h>timeH)
timeH=h;}
if(this.dO)
{w=this.oMinW;if(timeW<w+1)
timeW=w+1;timeH+=this.dO.AnyTime_height(true);}
if(this.dT)
{this.dT.css({width:String(timeW)+'px',height:String(timeH)+'px'});timeW+=this.tMinW+1;timeH+=this.tMinH;totW+=timeW;if(timeH>totH)
totH=timeH;if(this.dO)
{var dOW=this.dT.width()-(this.oMinW+1);this.dO.css({width:String(dOW)+"px"});this.oCur.css({width:String(dOW-(this.oListMinW+4))+"px"});}}
this.dB.css({height:String(totH)+'px',width:String(totW)+'px'});totH+=this.bMinH;totW+=this.bMinW;totH+=this.hTitle.AnyTime_height(true)+this.wMinH;totW+=this.wMinW;if(this.hTitle.outerWidth(true)>totW)
totW=this.hTitle.outerWidth(true);this.div.css({height:String(totH)+'px',width:String(totW)+'px'});if(!this.pop)
this.ajax();},updODiv:function(fBtn)
{var cur,matched=false,def=null;this.oDiv.find('.AnyTime-off-off-btn').each(function()
{if(this.AnyTime_offMin==_this.offMin)
{if(this.AnyTime_offSI==_this.offSI)
$(this).AnyTime_current(matched=true,true);else
{$(this).AnyTime_current(false,true);if(def==null)
def=$(this);}}
else
$(this).AnyTime_current(false,true);});if((!matched)&&(def!=null))
def.AnyTime_current(true,true);this.conv.setUtcFormatOffsetAlleged(this.offMin);this.conv.setUtcFormatOffsetSubIndex(this.offSI);this.inp.val(this.conv.format(this.time)).change();this.upd(fBtn);},updYDiv:function(fBtn)
{var i,legal;var era=1;var yearValue=this.time.getFullYear();if(yearValue<0)
{era=(-1);yearValue=0-yearValue;}
yearValue=AnyTime.pad(yearValue,4);var eY=_this.earliest&&new Date(_this.earliest).getFullYear();var lY=_this.latest&&new Date(_this.latest).getFullYear();i=0;this.yDiv.find('.AnyTime-mil-btn').each(function()
{legal=(((!_this.earliest)||(era*(i+(era<0?0:999))>=eY))&&((!_this.latest)||(era*(i+(era>0?0:999))<=lY)));$(this).AnyTime_current(this.innerHTML==yearValue.substring(0,1),legal);i+=1000;});i=(Math.floor(yearValue/1000)*1000);this.yDiv.find('.AnyTime-cent-btn').each(function()
{legal=(((!_this.earliest)||(era*(i+(era<0?0:99))>=eY))&&((!_this.latest)||(era*(i+(era>0?0:99))<=lY)));$(this).AnyTime_current(this.innerHTML==yearValue.substring(1,2),legal);i+=100;});i=(Math.floor(yearValue/100)*100);this.yDiv.find('.AnyTime-dec-btn').each(function()
{legal=(((!_this.earliest)||(era*(i+(era<0?0:9))>=eY))&&((!_this.latest)||(era*(i+(era>0?0:9))<=lY)));$(this).AnyTime_current(this.innerHTML==yearValue.substring(2,3),legal);i+=10;});i=(Math.floor(yearValue/10)*10);this.yDiv.find('.AnyTime-yr-btn').each(function()
{legal=(((!_this.earliest)||(era*i>=eY))&&((!_this.latest)||(era*i<=lY)));$(this).AnyTime_current(this.innerHTML==yearValue.substring(3),legal);i+=1;});this.yDiv.find('.AnyTime-bce-btn').each(function()
{$(this).AnyTime_current(era<0,(!_this.earliest)||(_this.earliest<0));});this.yDiv.find('.AnyTime-ce-btn').each(function()
{$(this).AnyTime_current(era>0,(!_this.latest)||(_this.latest>0));});this.conv.setUtcFormatOffsetAlleged(this.offMin);this.conv.setUtcFormatOffsetSubIndex(this.offSI);this.inp.val(this.conv.format(this.time)).change();this.upd(fBtn);}};__pickers[id].initialize(id);}})(jQuery);

