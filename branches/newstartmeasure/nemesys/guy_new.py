#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
from progress import Progress

class MyFrame(wx.Frame):
  def __init__(self, *args, **kwds):
    # begin wxGlade: MyFrame.__init__
    kwds["style"] = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.RESIZE_BOX)
    wx.Frame.__init__(self, *args, **kwds)

    # Menu Bar
    self.frame_1_menubar = wx.MenuBar()
    wxglade_tmp_menu = wx.Menu()
    self.frame_1_menubar.Append(wxglade_tmp_menu, "About")
    self.SetMenuBar(self.frame_1_menubar)
    # Menu Bar end
    self.panel_1 = wx.Panel(self, -1)
    self.bitmap_1 = wx.StaticBitmap(self.panel_1, -1, wx.Bitmap("../icons/logo_misurainternet.png", wx.BITMAP_TYPE_ANY))
    self.label_1 = wx.StaticText(self.panel_1, -1, "Ne.me.sys", style=wx.ALIGN_CENTRE)
    self.label_2 = wx.StaticText(self.panel_1, -1, "Inizio test di misura: <inserire data>\nLa misurazione va completata entro tre giorni dal suo inizio", style=wx.ALIGN_CENTRE)
    self.label_3 = wx.StaticText(self.panel_1, -1, "Stato di avanzamento: X test su 24", style=wx.ALIGN_CENTRE)
    self.bitmap_2 = wx.StaticBitmap(self.panel_1, -1, wx.Bitmap("../icons/logo_nemesys.png", wx.BITMAP_TYPE_ANY))
    self.text_ctrl_1 = wx.TextCtrl(self.panel_1, -1, "", style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL | wx.TE_RICH | wx.TE_RICH2 | wx.NO_BORDER)
    self.sizer_5_staticbox = wx.StaticBox(self.panel_1, -1, "Dettaglio di stato della misura")

    self.__set_properties()
    self.__do_layout()
    
    self.InitBuffer()
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    # end wxGlade

  def OnPaint(self, evt):
    dc = wx.BufferedPaintDC(self, self.buffer)

  def InitBuffer(self):
    w, h = self.GetClientSize()
    self.buffer = wx.EmptyBitmap(w, h)
    dc = wx.BufferedDC(wx.ClientDC(self), self.buffer)
    self.PaintInit(dc, None)

  def __set_properties(self):
    # begin wxGlade: MyFrame.__set_properties
    self.SetTitle("Ne.me.sys")
    self.SetSize((600, 300))
    self.label_1.SetFont(wx.Font(26, wx.DEFAULT, wx.NORMAL, wx.BOLD, 0, ""))
    self.text_ctrl_1.SetMinSize((580, -1))
    #self.text_ctrl_1.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
    #self.panel_1.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
    # end wxGlade

  def __do_layout(self):
    # begin wxGlade: MyFrame.__do_layout
    sizer_1 = wx.BoxSizer(wx.VERTICAL)
    sizer_2 = wx.BoxSizer(wx.VERTICAL)
    self.sizer_5_staticbox.Lower()
    sizer_5 = wx.StaticBoxSizer(self.sizer_5_staticbox, wx.HORIZONTAL)
    sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
    sizer_4 = wx.BoxSizer(wx.VERTICAL)

    sizer_3.Add(self.bitmap_1, 0, wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 10)
    sizer_4.Add(self.label_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
    sizer_4.Add(self.label_2, 0, wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
    sizer_4.Add(self.label_3, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
    sizer_3.Add(sizer_4, 0, wx.TOP | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 10)
    sizer_3.Add(self.bitmap_2, 0, wx.LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 10)
    sizer_2.Add(sizer_3, 1, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)

    self._grid = wx.GridSizer(2, 24, 2, 6)
    for i in range (0, 24):
      self.label_hour = wx.StaticText(self.panel_1, -1, "%2d" % i)
      self._grid.Add(self.label_hour, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)

    for i in range (24, 48):    
      self.bitmap_hour = wx.StaticBitmap(self.panel_1, -1, wx.Bitmap("../icons/red.png", wx.BITMAP_TYPE_ANY))
      self._grid.Add(self.bitmap_hour, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)

    sizer_2.Add(self._grid, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 8)
    sizer_5.Add(self.text_ctrl_1, 1, wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
    sizer_2.Add(sizer_5, 2, wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 10)
    self.panel_1.SetSizer(sizer_2)
    sizer_1.Add(self.panel_1, 1, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
    self.SetSizer(sizer_1)
    self.Layout()
    # end wxGlade

  def PaintInit(self, dc, event):
    '''
    Inizializza le casselle ora tutte rosse
        
    '''
    xmldoc = Progress(True)

    n = 0
    for hour in range(0, 24):
        color = "red"
        if xmldoc.isdone(hour):
            color = "green"
            n = n + 1
        self.PaintHour(hour, color)
    #for i in range (24, 48):    
    #  self.bitmap_hour = wx.StaticBitmap(self.panel_1, -1, wx.Bitmap("../icons/red.png", wx.BITMAP_TYPE_ANY))
    #  self._grid.Add(self.bitmap_hour, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)

    #logger.debug('Aggiorno lo stato di avanzamento')
    if (n != 0):
      self.label_3.SetLabel('Stato di avanzamento: %d test su 24' % n)
    else:
      self.label_3.SetLabel('Stato di avanzamento: nessun test effettuato su 24')

  def PaintHour(self, hour, color):
    '''
    Aggiorna la casella allora specificata con il colore specificatio
    '''
    self._grid._ReplaceItem()

# end of class MyFrame
if __name__ == "__main__":
  app = wx.PySimpleApp(0)
  wx.InitAllImageHandlers()
  frame_1 = MyFrame(None, -1, "")
  app.SetTopWindow(frame_1)
  frame_1.Show()
  app.MainLoop()
