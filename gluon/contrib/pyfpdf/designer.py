#!/usr/bin/python
# -*- coding: latin-1 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"Visual Template designer for PyFPDF (using wxPython OGL library)"

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2011 Mariano Reingart"
__license__ = "GPL 3.0"
__version__ = "1.01a"

# Based on:
#  * pySjetch.py wxPython sample application
#  * OGL.py and other wxPython demo modules


import os, sys
import wx
import wx.lib.ogl as ogl
from wx.lib.wordwrap import wordwrap

DEBUG = True


class CustomDialog(wx.Dialog):
    "A dinamyc dialog to ask user about arbitrary fields"

    def __init__(
            self, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition,
            style=wx.DEFAULT_DIALOG_STYLE, fields=None, data=None,
            ):

        wx.Dialog.__init__ (self, parent, ID, title, pos, size, style)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.textctrls = {}
        for field in fields:
            box = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(self, -1, field)
            label.SetHelpText("This is the help text for the label")
            box.Add(label, 1, wx.ALIGN_CENTRE|wx.ALL, 5)
            text = wx.TextCtrl(self, -1, "", size=(80,-1))
            text.SetHelpText("Here's some help text for field #1")
            if field in data:
                text.SetValue(repr(data[field]))
            box.Add(text, 1, wx.ALIGN_CENTRE|wx.ALL, 1)
            sizer.Add(box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 1)
            self.textctrls[field] = text

        line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)

        btnsizer = wx.StdDialogButtonSizer()

        btn = wx.Button(self, wx.ID_OK)
        btn.SetHelpText("The OK button completes the dialog")
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btn.SetHelpText("The Cancel button cancels the dialog. (Cool, huh?)")
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

    @classmethod
    def do_input(Class, parent, title, fields, data):
        dlg = Class(parent, -1, title, size=(350, 200),
                         style=wx.DEFAULT_DIALOG_STYLE, # & ~wx.CLOSE_BOX,
                        fields=fields, data=data
                         )
        dlg.CenterOnScreen()
        while 1:
            val = dlg.ShowModal()
            if val == wx.ID_OK:
                values = {}
                for field in fields:
                    try:
                        values[field] = eval(dlg.textctrls[field].GetValue())
                    except Exception, e:
                        msg = wx.MessageDialog(parent, unicode(e),
                               "Error in field %s" % field,
                               wx.OK | wx.ICON_INFORMATION
                               )
                        msg.ShowModal()
                        msg.Destroy()
                        break
                else:
                    return dict([(field, values[field]) for field in fields])
            else:
                return None


class MyEvtHandler(ogl.ShapeEvtHandler):
    "Custom Event Handler for Shapes"
    def __init__(self, callback):
        ogl.ShapeEvtHandler.__init__(self)
        self.callback = callback

    def OnLeftClick(self, x, y, keys=0, attachment=0):
        shape = self.GetShape()
        canvas = shape.GetCanvas()
        dc = wx.ClientDC(canvas)
        canvas.PrepareDC(dc)

        if shape.Selected() and keys & ogl.KEY_SHIFT:
            shape.Select(False, dc)
            #canvas.Redraw(dc)
            canvas.Refresh(False)
        else:
            redraw = False
            shapeList = canvas.GetDiagram().GetShapeList()
            toUnselect = []

            for s in shapeList:
                if s.Selected() and not keys & ogl.KEY_SHIFT:
                    # If we unselect it now then some of the objects in
                    # shapeList will become invalid (the control points are
                    # shapes too!) and bad things will happen...
                    toUnselect.append(s)

            shape.Select(True, dc)

            if toUnselect:
                for s in toUnselect:
                    s.Select(False, dc)
                ##canvas.Redraw(dc)
                canvas.Refresh(False)

        self.callback()

    def OnEndDragLeft(self, x, y, keys=0, attachment=0):
        shape = self.GetShape()
        ogl.ShapeEvtHandler.OnEndDragLeft(self, x, y, keys, attachment)

        if not shape.Selected():
            self.OnLeftClick(x, y, keys, attachment)

        self.callback()

    def OnSizingEndDragLeft(self, pt, x, y, keys, attch):
        ogl.ShapeEvtHandler.OnSizingEndDragLeft(self, pt, x, y, keys, attch)
        self.callback()

    def OnMovePost(self, dc, x, y, oldX, oldY, display):
        shape = self.GetShape()
        ogl.ShapeEvtHandler.OnMovePost(self, dc, x, y, oldX, oldY, display)
        self.callback()
        if "wxMac" in wx.PlatformInfo:
            shape.GetCanvas().Refresh(False)

    def OnLeftDoubleClick(self, x, y, keys = 0, attachment = 0):
        self.callback("LeftDoubleClick")

    def OnRightClick(self, *dontcare):
        self.callback("RightClick")


class Element(object):
    "Visual class that represent a placeholder in the template"

    fields = ['name', 'type',
                  'x1', 'y1', 'x2', 'y2',
                  'font', 'size',
                  'bold', 'italic', 'underline',
                  'foreground', 'background',
                  'align', 'text', 'priority',]

    def __init__(self, canvas=None, frame=None, zoom=5.0, static=False, **kwargs):
        self.kwargs = kwargs
        self.zoom = zoom
        self.frame = frame
        self.canvas = canvas
        self.static = static

        name = kwargs['name']
        kwargs['type']
        type = kwargs['type']

        x, y, w, h = self.set_coordinates(kwargs['x1'], kwargs['y1'], kwargs['x2'], kwargs['y2'])

        text = kwargs['text']

        shape = self.shape = ogl.RectangleShape(w, h)

        if not static:
            shape.SetDraggable(True, True)

        shape.SetX(x)
        shape.SetY(y)
        #if pen:    shape.SetPen(pen)
        #if brush:  shape.SetBrush(brush)
        shape.SetBrush(wx.TRANSPARENT_BRUSH)

        if type not in ('L', 'B', 'BC'):
            if not static:
                pen = wx.LIGHT_GREY_PEN
            else:
                pen = wx.RED_PEN
            shape.SetPen(pen)

        self.text = kwargs['text']

        evthandler = MyEvtHandler(self.evt_callback)
        evthandler.SetShape(shape)
        evthandler.SetPreviousHandler(shape.GetEventHandler())
        shape.SetEventHandler(evthandler)
        shape.SetCentreResize(False)
        shape.SetMaintainAspectRatio(False)

        canvas.AddShape( shape )

    @classmethod
    def new(Class, parent):
        data = dict(name='some_name', type='T',
                    x1=5.0, y1=5.0, x2=100.0, y2=10.0,
                    font="Arial", size=12,
                 bold=False, italic=False, underline=False,
                    foreground= 0x000000, background=0xFFFFFF,
                    align="L", text="", priority=0)
        data = CustomDialog.do_input(parent, 'New element', Class.fields, data)
        if data:
            return Class(canvas=parent.canvas, frame=parent, **data)

    def edit(self):
        "Edit current element (show a dialog box with all fields)"
        data = self.kwargs.copy()
        x1, y1, x2, y2 = self.get_coordinates()
        data.update(dict(name=self.name,
                         text=self.text,
                         x1=x1, y1=y1, x2=x2, y2=y2,
                       ))
        data = CustomDialog.do_input(self.frame, 'Edit element', self.fields, data)
        if data:
            self.kwargs.update(data)
            self.name = data['name']
            self.text = data['text']
            x,y, w, h = self.set_coordinates(data['x1'], data['y1'], data['x2'], data['y2'])
            self.shape.SetX(x)
            self.shape.SetY(y)
            self.shape.SetWidth(w)
            self.shape.SetHeight(h)
            self.canvas.Refresh(False)
            self.canvas.GetDiagram().ShowAll(1)

    def edit_text(self):
        "Allow text edition (i.e. for doubleclick)"
        dlg = wx.TextEntryDialog(
            self.frame, 'Text for %s' % self.name,
            'Edit Text', '')
        if self.text:
            dlg.SetValue(self.text)
        if dlg.ShowModal() == wx.ID_OK:
            self.text = dlg.GetValue().encode("latin1")
        dlg.Destroy()

    def copy(self):
        "Return an identical duplicate"
        kwargs = self.as_dict()
        element = Element(canvas=self.canvas, frame=self.frame, zoom=self.zoom, static=self.static, **kwargs)
        return element

    def remove(self):
        "Erases visual shape from OGL canvas (element must be deleted manually)"
        self.canvas.RemoveShape(self.shape)

    def move(self, dx, dy):
        "Change pdf coordinates (converting to wx internal values)"
        x1, y1, x2, y2 = self.get_coordinates()
        x1 += dx
        x2 += dx
        y1 += dy
        y2 += dy
        x, y, w, h = self.set_coordinates(x1, y1, x2, y2)
        self.shape.SetX(x)
        self.shape.SetY(y)

    def evt_callback(self, evt_type=None):
        "Event dispatcher"
        if evt_type=="LeftDoubleClick":
            self.edit_text()
        if evt_type=='RightClick':
            self.edit()

        # update the status bar
        x1, y1, x2, y2 = self.get_coordinates()
        self.frame.SetStatusText("%s (%0.2f, %0.2f) - (%0.2f, %0.2f)" %
                                        (self.name, x1, y1, x2, y2))

    def get_coordinates(self):
        "Convert from wx to pdf coordinates"
        x, y = self.shape.GetX(), self.shape.GetY()
        w, h = self.shape.GetBoundingBoxMax()
        w -= 1
        h -= 1
        x1 = x/self.zoom - w/self.zoom/2.0
        x2 = x/self.zoom + w/self.zoom/2.0
        y1 = y/self.zoom - h/self.zoom/2.0
        y2 = y/self.zoom + h/self.zoom/2.0
        return x1, y1, x2, y2

    def set_coordinates(self, x1, y1, x2, y2):
        "Convert from pdf to wx coordinates"
        x1 = x1 * self.zoom
        x2 = x2 * self.zoom
        y1 = y1 * self.zoom
        y2 = y2 * self.zoom

        # shapes seems to be centred, pdf coord not
        w = max(x1, x2) - min(x1, x2) + 1
        h = max(y1, y2) - min(y1, y2) + 1
        x = (min(x1, x2) + w/2.0)
        y = (min(y1, y2) + h/2.0)
        return x, y, w, h

    def text(self, txt=None):
        if txt is not None:
            if not isinstance(txt,str):
                txt = str(txt)
            self.kwargs['text'] = txt
            self.shape.ClearText()
            for line in txt.split('\n'):
                self.shape.AddText(unicode(line, "latin1"))
            self.canvas.Refresh(False)
        return self.kwargs['text']
    text = property(text, text)

    def set_x(self, x):
        self.shape.SetX(x)
        self.canvas.Refresh(False)
        self.evt_callback()
    def set_y(self, y):
        self.shape.SetY(y)
        self.canvas.Refresh(False)
        self.evt_callback()
    def get_x(self):
        return self.shape.GetX()
    def get_y(self):
        return self.shape.GetY()

    x = property(get_x, set_x)
    y = property(get_y, set_y)

    def selected(self, sel=None):
        if sel is not None:
            print "Setting Select(%s)" % sel
            self.shape.Select(sel)
        return self.shape.Selected()
    selected = property(selected, selected)

    def name(self, name=None):
        if name is not None:
            self.kwargs['name'] = name
        return self.kwargs['name']
    name = property(name, name)

    def __contains__(self, k):
        "Implement in keyword for searchs"
        return k in self.name.lower() or self.text and k in self.text.lower()

    def as_dict(self):
        "Return a dictionary representation, used by pyfpdf"
        d = self.kwargs
        x1, y1, x2, y2 = self.get_coordinates()
        d.update({
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                'text': self.text})
        return d


class AppFrame(wx.Frame):
    "OGL Designer main window"
    title = "PyFPDF Template Designer (wx OGL)"

    def __init__(self):
        wx.Frame.__init__( self,
                          None, -1, self.title,
                          size=(640,480),
                          style=wx.DEFAULT_FRAME_STYLE )
        sys.excepthook  = self.except_hook
        self.filename = ""
        # Create a toolbar:
        tsize = (16,16)
        self.toolbar = self.CreateToolBar(wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT)

        artBmp = wx.ArtProvider.GetBitmap
        self.toolbar.AddSimpleTool(
            wx.ID_NEW, artBmp(wx.ART_NEW, wx.ART_TOOLBAR, tsize), "New")
        self.toolbar.AddSimpleTool(
            wx.ID_OPEN, artBmp(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, tsize), "Open")
        self.toolbar.AddSimpleTool(
            wx.ID_SAVE, artBmp(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, tsize), "Save")
        self.toolbar.AddSimpleTool(
            wx.ID_SAVEAS, artBmp(wx.ART_FILE_SAVE_AS, wx.ART_TOOLBAR, tsize),
            "Save As...")
        #-------
        self.toolbar.AddSeparator()
        self.toolbar.AddSimpleTool(
            wx.ID_UNDO, artBmp(wx.ART_UNDO, wx.ART_TOOLBAR, tsize), "Undo")
        self.toolbar.AddSimpleTool(
            wx.ID_REDO, artBmp(wx.ART_REDO, wx.ART_TOOLBAR, tsize), "Redo")
        self.toolbar.AddSeparator()
        #-------
        self.toolbar.AddSimpleTool(
            wx.ID_CUT, artBmp(wx.ART_CUT, wx.ART_TOOLBAR, tsize), "Remove")
        self.toolbar.AddSimpleTool(
            wx.ID_COPY, artBmp(wx.ART_COPY, wx.ART_TOOLBAR, tsize), "Duplicate")
        self.toolbar.AddSimpleTool(
            wx.ID_PASTE, artBmp(wx.ART_PASTE, wx.ART_TOOLBAR, tsize), "Insert")
        self.toolbar.AddSeparator()
        self.toolbar.AddSimpleTool(
            wx.ID_FIND, artBmp(wx.ART_FIND, wx.ART_TOOLBAR, tsize), "Find")
        self.toolbar.AddSeparator()
        self.toolbar.AddSimpleTool(
            wx.ID_PRINT, artBmp(wx.ART_PRINT, wx.ART_TOOLBAR, tsize), "Print")
        self.toolbar.AddSimpleTool(
            wx.ID_ABOUT, artBmp(wx.ART_HELP, wx.ART_TOOLBAR, tsize), "About")

        self.toolbar.Realize()

        self.toolbar.EnableTool(wx.ID_SAVEAS,       False)
        self.toolbar.EnableTool(wx.ID_UNDO,         False)
        self.toolbar.EnableTool(wx.ID_REDO,         False)

        menu_handlers = [
            (wx.ID_NEW, self.do_new),
            (wx.ID_OPEN, self.do_open),
            (wx.ID_SAVE, self.do_save),
            (wx.ID_PRINT, self.do_print),
            (wx.ID_FIND, self.do_find),
            (wx.ID_CUT, self.do_cut),
            (wx.ID_COPY, self.do_copy),
            (wx.ID_PASTE, self.do_paste),
            (wx.ID_ABOUT, self.do_about),
        ]
        for menu_id, handler in menu_handlers:
            self.Bind(wx.EVT_MENU, handler, id = menu_id)

        sizer = wx.BoxSizer(wx.VERTICAL)
        # put stuff into sizer

        self.CreateStatusBar()

        canvas = self.canvas = ogl.ShapeCanvas( self )
        maxWidth  = 1500
        maxHeight = 2000
        canvas.SetScrollbars(20, 20, maxWidth/20, maxHeight/20)
        sizer.Add( canvas, 1, wx.GROW )

        canvas.SetBackgroundColour("WHITE") #

        diagram = self.diagram = ogl.Diagram()
        canvas.SetDiagram( diagram )
        diagram.SetCanvas( canvas )
        diagram.SetSnapToGrid( False )

        # apply sizer
        self.SetSizer(sizer)
        self.SetAutoLayout(1)
        self.Show(1)

        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_event)
        self.elements = []

    def on_key_event(self, event):
        """ Respond to a keypress event.

            We make the arrow keys move the selected object(s) by one pixel in
            the given direction.
        """
        step = 1
        if event.ControlDown():
            step = 20

        if event.GetKeyCode() == wx.WXK_UP:
            self.move_elements(0, -step)
        elif event.GetKeyCode() == wx.WXK_DOWN:
            self.move_elements(0, step)
        elif event.GetKeyCode() == wx.WXK_LEFT:
            self.move_elements(-step, 0)
        elif event.GetKeyCode() == wx.WXK_RIGHT:
            self.move_elements(step, 0)
        elif event.GetKeyCode() == wx.WXK_DELETE:
            self.do_cut()
        else:
            event.Skip()

    def do_new(self, evt=None):
        for element in self.elements:
            element.remove()
        self.elements = []
        # draw paper size guides
        for k, (w, h) in [('legal', (216, 356)), ('A4', (210, 297)), ('letter', (216, 279))]:
            self.create_elements(
                k, 'R', 0, 0, w, h,
                size=70, foreground=0x808080, priority=-100,
                canvas=self.canvas, frame=self, static=True)
        self.diagram.ShowAll( 1 )

    def do_open(self, evt):
        dlg = wx.FileDialog(
            self, message="Choose a file",
            defaultDir=os.getcwd(),
            defaultFile="invoice.csv",
            wildcard="CSV Files (*.csv)|*.csv",
            style=wx.OPEN
            )

        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            self.filename = dlg.GetPaths()[0]

        dlg.Destroy()
        self.SetTitle(self.filename + " - " + self.title)

        self.do_new()
        tmp = []
        f = open(self.filename)
        try:
            filedata = f.readlines()
        finally:
            f.close()
        for lno, linea in enumerate(filedata):
            if DEBUG: print "processing line", lno, linea
            args = []
            for i,v in enumerate(linea.split(";")):
                if not v.startswith("'"):
                    v = v.replace(",",".")
                else:
                    v = v#.decode('latin1')
                if v.strip()=='':
                    v = None
                else:
                    v = eval(v.strip())
                args.append(v)
            tmp.append(args)

        # sort by z-order (priority)
        for args in sorted(tmp, key=lambda t: t[-1]):
            if DEBUG: print args
            self.create_elements(*args)
        self.diagram.ShowAll( 1 )                       #

        return True

    def do_save(self, evt, filename=None):
        try:
            from time import gmtime, strftime
            ts = strftime("%Y%m%d%H%M%S", gmtime())
            os.rename(self.filename, self.filename + ts + ".bak")
        except Exception, e:
            if DEBUG: print e
            pass

        def csv_repr(v, decimal_sep="."):
            if isinstance(v, float):
                return ("%0.2f" % v).replace(".", decimal_sep)
            else:
                return repr(v)

        f = open(self.filename, "w")
        try:
            for element in sorted(self.elements, key=lambda e:e.name):
                if element.static:
                    continue
                d = element.as_dict()
                l = [d['name'], d['type'],
                     d['x1'], d['y1'], d['x2'], d['y2'],
                     d['font'], d['size'],
                     d['bold'], d['italic'], d['underline'],
                     d['foreground'], d['background'],
                     d['align'], d['text'], d['priority'],
                    ]
                f.write(";".join([csv_repr(v) for v in l]))
                f.write("\n")
        finally:
            f.close()

    def do_print(self, evt):
        # genero el renderizador con propiedades del PDF
        from template import Template
        t = Template(elements=[e.as_dict() for e in self.elements if not e.static])
        t.add_page()
        if not t['logo'] or not os.path.exists(t['logo']):
            # put a default logo so it doesn't trow an exception
            logo = os.path.join(os.path.dirname(__file__), 'tutorial','logo.png')
            t.set('logo', logo)
        try:
            t.render(self.filename +".pdf")
        except:
            if DEBUG and False:
                import pdb;
                pdb.pm()
            else:
                raise
        if sys.platform=="linux2":
            os.system("evince ""%s""" % self.filename +".pdf")
        else:
            os.startfile(self.filename +".pdf")

    def do_find(self, evt):
        # busco nombre o texto
        dlg = wx.TextEntryDialog(
            self, 'Enter text to search for',
            'Find Text', '')
        if dlg.ShowModal() == wx.ID_OK:
            txt = dlg.GetValue().encode("latin1").lower()
            for element in self.elements:
                if txt in element:
                    element.selected = True
                    print "Found:", element.name
            self.canvas.Refresh(False)
        dlg.Destroy()

    def do_cut(self, evt=None):
        "Delete selected elements"
        new_elements = []
        for element in self.elements:
            if element.selected:
                print "Erasing:", element.name
                element.selected = False
                self.canvas.Refresh(False)
                element.remove()
            else:
                new_elements.append(element)
        self.elements = new_elements
        self.canvas.Refresh(False)
        self.diagram.ShowAll( 1 )

    def do_copy(self, evt):
        "Duplicate selected elements"
        fields = ['qty', 'dx', 'dy']
        data = {'qty': 1, 'dx': 0.0, 'dy': 5.0}
        data = CustomDialog.do_input(self, 'Copy elements', fields, data)
        if data:
            new_elements = []
            for i in range(1, data['qty']+1):
                for element in self.elements:
                    if element.selected:
                        print "Copying:", element.name
                        new_element = element.copy()
                        name = new_element.name
                        if len(name)>2 and name[-2:].isdigit():
                            new_element.name = name[:-2] + "%02d" % (int(name[-2:])+i)
                        else:
                            new_element.name = new_element.name + "_copy"
                        new_element.selected = False
                        new_element.move(data['dx']*i, data['dy']*i)
                        new_elements.append(new_element)
            self.elements.extend(new_elements)
            self.canvas.Refresh(False)
            self.diagram.ShowAll( 1 )

    def do_paste(self, evt):
        "Insert new elements"
        element = Element.new(self)
        if element:
            self.canvas.Refresh(False)
            self.elements.append(element)
            self.diagram.ShowAll( 1 )

    def create_elements(self, name, type, x1, y1, x2, y2,
                   font="Arial", size=12,
                   bold=False, italic=False, underline=False,
                   foreground= 0x000000, background=0xFFFFFF,
                   align="L", text="", priority=0, canvas=None, frame=None, static=False,
                   **kwargs):
        element = Element(name=name, type=type, x1=x1, y1=y1, x2=x2, y2=y2,
                   font=font, size=size,
                   bold=bold, italic=italic, underline=underline,
                   foreground= foreground, background=background,
                   align=align, text=text, priority=priority,
                   canvas=canvas or self.canvas, frame=frame or self,
                   static=static)
        self.elements.append(element)

    def move_elements(self, x, y):
        for element in self.elements:
            if element.selected:
                print "moving", element.name, x, y
                element.x = element.x + x
                element.y = element.y + y

    def do_about(self, evt):
        info = wx.AboutDialogInfo()
        info.Name = self.title
        info.Version = __version__
        info.Copyright = __copyright__
        info.Description = (
            "Visual Template designer for PyFPDF (using wxPython OGL library)\n"
            "Input files are CSV format describing the layout, separated by ;\n"
            "Use toolbar buttons to open, save, print (preview) your template, "
            "and there are buttons to find, add, remove or duplicate elements.\n"
            "Over an element, a double left click opens edit text dialog, "
            "and a right click opens edit properties dialog. \n"
            "Multiple element can be selected with shift left click. \n"
            "Use arrow keys or drag-and-drop to move elements.\n"
            "For further information see project webpage:"
            )
        info.WebSite = ("http://code.google.com/p/pyfpdf/wiki/Templates",
                        "pyfpdf Google Code Project")
        info.Developers = [ __author__, ]

        info.License = wordwrap(__license__, 500, wx.ClientDC(self))

        # Then we call wx.AboutBox giving it that info object
        wx.AboutBox(info)

    def except_hook(self, type, value, trace):
        import traceback
        exc = traceback.format_exception(type, value, trace)
        for e in exc: wx.LogError(e)
        wx.LogError('Unhandled Error: %s: %s'%(str(type), str(value)))


app = wx.PySimpleApp()
ogl.OGLInitialize()
frame = AppFrame()
app.MainLoop()
app.Destroy()



