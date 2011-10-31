#!/usr/bin/env python
# printing_in_wx.py
#

from collections import deque
from contabyte import Contabyte
from pcapper import Pcapper
from threading import Thread
import math
import matplotlib
import numpy
import socket
import time
import wx

SECONDS = 60
POINTS_PER_SECONDS = 1
SAMPLE_INTERVAL = 0.8

matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas
from matplotlib.figure import Figure

class Updater(Thread):
  
  def __init__(self, window, ip, nap):
    Thread.__init__(self)
    self._window = window
    self._ip = ip
    self._nap = nap
    
    maxlen = int(math.ceil(SECONDS * POINTS_PER_SECONDS))
    self._samples_down = deque(maxlen=maxlen)
    self._samples_up = deque(maxlen=maxlen)
    for i in range (0, maxlen):
      self._samples_down.append(0)
      self._samples_up.append(0)
      
    self._p = Pcapper(self._ip)
    self._p.start()
    
  def _get_sample(self):
    
    self._p.sniff(Contabyte(self._ip, self._nap))
    time.sleep(SAMPLE_INTERVAL)
    self._p.stop_sniff()
    
    stats = self._p.get_stats()
    down = stats.byte_down_all_net * 8.0 / (SAMPLE_INTERVAL * 1000.0)
    up = -stats.byte_up_all_net * 8.0 / (SAMPLE_INTERVAL * 1000.0)
    return (down, up)

  def _update_samples(self):
    (down, up) = self._get_sample()

    self._samples_down.popleft()
    self._samples_down.append(down)
    
    self._samples_up.popleft()
    self._samples_up.append(up)

  def run(self):
    while(self._window):
      try:
        self._update_samples()
        wx.CallAfter(self._window.Plot_Data, list(self._samples_down), list(self._samples_up))
        time.sleep(1.0 / POINTS_PER_SECONDS - SAMPLE_INTERVAL)
      except:
        break

    self._p.stop()
    self._p.join()
    
  def stop(self):
    self._window = None
      
class Netgraph(wx.Frame):

  def __init__(self):
    wx.Frame.__init__ (self, None, id=wx.ID_ANY, title='Netgraph', size=wx.Size(750, 300), style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.RESIZE_BOX))
    self.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))

    self.figure = Figure()
    self.axes = self.figure.add_subplot(111)
    self.axes.set_xticklabels([])
    self.axes.set_ylabel("Kbps")
    self._min = 0
    self._max = 0

    t = numpy.arange(-SECONDS, 0, 1.0 / POINTS_PER_SECONDS)
    self.d, = self.axes.plot(t, numpy.zeros(60 * 1.0 / POINTS_PER_SECONDS))
    self.u, = self.axes.plot(t, numpy.zeros(60 * 1.0 / POINTS_PER_SECONDS))

    self.canvas = FigCanvas(self, -1, self.figure)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)

    self.SetSizer(sizer)
    self.Fit()
      
  def onExit(self, event=None):
    self.Destroy()

  def _check_limits(self, u, d):
    min = numpy.min(u)
    max = numpy.max(d)
    
    if (min < self._min or max > self._max):
      self._min = min
      self._max = max
      self.axes.set_ylim(self._min - 50, self._max + 50)

  def Plot_Data(self, d, u):
    self._check_limits(u, d)
    
    self.d.set_ydata(d)
    self.u.set_ydata(u)
    self.canvas.draw()
        
if __name__ == '__main__':
    app = wx.PySimpleApp()
    fig = Netgraph()
    fig.Show()
    
    s = socket.socket(socket.AF_INET)
    s.connect(('www.fub.it', 80))
    ip = s.getsockname()[0]
    s.close()
    nap = '193.104.137.133'
      
    u = Updater(fig, ip, nap)
    u.start()

    app.MainLoop()
    
    u.stop()
    u.join()
