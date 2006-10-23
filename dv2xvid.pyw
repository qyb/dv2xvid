#!/usr/bin/env python

"""
This demo attempts to override the C++ MainLoop and implement it
in Python.
"""

import time
import wx
import wx.lib.infoframe
import dircache
import os
import sys
import thread

import dv_info
import vdub
#---------------------------------------------------------------------------

wildcard = "AVI source (*.avi)|*.avi|"     \
           "All files (*.*)|*.*"

class SrcListWindow(wx.ListCtrl):
    def __init__(self, parent):
        self.sortlist = []
        self.seconds = 0
        wx.ListCtrl.__init__(self, parent, -1, size=(385, 220),
                             style=wx.LC_REPORT|wx.LC_VIRTUAL|wx.LC_HRULES|wx.LC_VRULES)
        self.InsertColumn(0, "File Path")
        self.InsertColumn(1, "File Info")
        self.SetColumnWidth(0, 190)
        self.SetColumnWidth(1, 190)

        self.parent = parent

    def cmpfunc(self, x, y):
        return cmp(x[1], y[1])

    def OnGetItemText(self, item, col):
        return self.sortlist[item][col]

    def SetSortList(self, l):
        self.sortlist = []
        for key in l.keys():
            self.sortlist.append([key, l[key][0], l[key][1]])
        self.sortlist.sort(self.cmpfunc)
        self.DeleteAllItems()
        # before SetItemCount, we must DeleteAllItems,
        # otherwise the current content will not be refreshed
        self.SetItemCount(len(l))

    def ItemSelected(self):
        self.seconds = 0
        ret = []
        item = self.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        while item != -1:
            ret.append(self.sortlist[item][0])
            self.seconds += self.sortlist[item][2].seconds
            item = self.GetNextItem(item, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        return ret

        
class JobListWindow(wx.ListCtrl):
    def __init__(self, parent):
        self.joblist = []
        wx.ListCtrl.__init__(self, parent, -1, size=(375, 100),
                             style=wx.LC_REPORT|wx.LC_VIRTUAL|wx.LC_HRULES|wx.LC_VRULES|wx.LC_NO_HEADER)
        self.InsertColumn(0, "jobs")
        self.SetColumnWidth(0, 370)

    def OnGetItemText(self, item, col):
        j = self.joblist[item]
        flist = j[1]
        fstr = ''
        for f in flist:
            fstr += '**' + f
        return j[0] + ' - ' + fstr

    def AddJob(self, args):
        wx.LogMessage("Add job...")
        self.joblist.append(args)
        self.show()

    def show(self):
        self.DeleteAllItems()
        self.SetItemCount(len(self.joblist))

    def ItemSelectedDel(self):
        ret = []
        items = []
        item = self.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        while item != -1:
            ret.append(self.joblist[item][1])
            items.append(item)
            item = self.GetNextItem(item, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        items.reverse()
        for i in items:
            self.joblist = self.joblist[0:i] + self.joblist[i+1:]
        self.show()
        return ret

    def vdub(self, lockobject, output):
        lockobject.acquire()
        try:
            for job in self.joblist:
                #print job[1]
                vdub.main(sys.argv[0], str(job[0]), job[1], job[2], output)
        except:
            pass
        lockobject.release()
        output("job end!")

class MyFrame(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title,
                          size=(400, 560),
                          style=wx.MINIMIZE_BOX | wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX | wx.CLIP_CHILDREN)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

        self.SrcList = {}

        panel = wx.Panel(self)

        filelist_info = wx.BoxSizer(wx.HORIZONTAL)
        filelist_info.Add(wx.StaticText(panel, -1, "Source AVI LIST"))
        
        filelist_button = wx.BoxSizer(wx.HORIZONTAL)
        fb1 = wx.Button(panel, 10, "Add Directory",
                                 (20,150), style=wx.NO_BORDER)
        fb2 = wx.Button(panel, 20, "Add File",
                                 (20,150), style=wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.OnClickDir, fb1)
        self.Bind(wx.EVT_BUTTON, self.OnClickFile, fb2)
        filelist_button.Add(fb1)
        filelist_button.Add((7,20))
        filelist_button.Add(fb2)
        
        filelist_menu = wx.BoxSizer(wx.HORIZONTAL)
        filelist_menu.Add(filelist_info, 0, wx.ALIGN_BOTTOM)
        filelist_menu.Add((140,20), 0)
        
        filelist_menu.Add(filelist_button, 0, wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM)
        self.srcListCtrl = SrcListWindow(panel)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.ChangeTimeInfo, self.srcListCtrl)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.ChangeTimeInfo, self.srcListCtrl)
        
        filelist_selectedLength = wx.BoxSizer(wx.HORIZONTAL)
        filelist_selectedLength.Add(wx.StaticText(panel, -1, "Source Length: "))
        self.selectedLength = wx.StaticText(panel, -1, "0 second")
        filelist_selectedLength.Add(self.selectedLength)
        
        #filelist.Add(self.srcListCtrl)

        target = wx.BoxSizer(wx.HORIZONTAL)
        dstb = wx.Button(panel, 40, "select target", style=wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.OnClickDst, dstb)
        self.dstCtrl = wx.TextCtrl(panel, -1, "c:\\xvid.avi", size=(200, 20))
        target.Add(wx.StaticText(panel, -1, "Target AVI   "), 0, wx.ALIGN_CENTER)
        target.Add(self.dstCtrl, 0, wx.ALIGN_CENTER)
        target.Add((41,20))
        target.Add(dstb, 0, wx.ALIGN_BOTTOM)

        jb1 = wx.Button(panel, 50, "add job", style=wx.NO_BORDER)
        jb2 = wx.Button(panel, 60, "delete job", style=wx.NO_BORDER)
        jb3 = wx.Button(panel, 70, "start jobs", style=wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.OnClickAdd, jb1)
        self.Bind(wx.EVT_BUTTON, self.OnClickDel, jb2)
        self.Bind(wx.EVT_BUTTON, self.OnClickStart, jb3)
        joblist_menu = wx.BoxSizer(wx.HORIZONTAL)
        joblist_menu.Add(wx.StaticText(panel, -1, "Job List"),
                         0, wx.ALIGN_BOTTOM)
        joblist_menu.Add((120,20), 0)
        joblist_menu.Add(jb1)
        joblist_menu.Add(jb2)
        joblist_menu.Add(jb3)

        self.jobListCtrl = JobListWindow(panel)

        self.output = wx.TextCtrl(panel, -1, "", size=(382, 85), style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        self.output.SetBackgroundColour(wx.Colour(212, 208, 200))
        wx.Log_SetActiveTarget(wx.LogTextCtrl(self.output))
        
        border = wx.BoxSizer(wx.VERTICAL)
        #border.Add(fileButton, 0, wx.ALL, 5)
        border.Add(filelist_menu, 0, wx.ALL, 5)
        border.Add(self.srcListCtrl, 0, wx.EXPAND | wx.EAST | wx.WEST, 5)
        border.Add(filelist_selectedLength, 0, wx.ALL, 5)
        border.Add(target, 0, wx.ALL, 5)
        #border.Add(bsizer)
        border.Add(joblist_menu, 0, wx.ALL, 5)
        border.Add(self.jobListCtrl, 0, wx.EXPAND | wx.EAST | wx.WEST, 5)
        border.Add(self.output, 0, wx.ALL, 5)
        panel.SetSizer(border)
        
        wx.LogMessage("Start...")
        self.threadlock = thread.allocate_lock()
        
    def OnClickDst(self, event):
        dlg = wx.FileDialog(self, "Choose a target filename:",
                            defaultDir=os.getcwd(),
                            defaultFile="")
        if dlg.ShowModal() == wx.ID_OK:
            self.dstCtrl.SetValue(dlg.GetPath())
        dlg.Destroy()

    def OnClickDir(self, event):
        dlg = wx.DirDialog(self, "Choose a directory:")
        if dlg.ShowModal() == wx.ID_OK:
            p = dlg.GetPath()
            p = os.path.normpath(p)
            allfile = dircache.listdir(p)
            for filename in allfile:
                filepath = os.path.join(p, filename)
                if os.path.isfile(filepath):
                    ret = dv_info.dvinfo(filepath)
                    if ret:
                        self.SrcList[filepath] = ret
        dlg.Destroy()
        self.srcListCtrl.SetSortList(self.SrcList)
        
    def OnClickFile(self, event):
        dlg = wx.FileDialog(self, "Choose a file:", defaultDir=os.getcwd(),
                            defaultFile="", wildcard=wildcard,
                            style=wx.OPEN | wx.MULTIPLE | wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            for filepath in dlg.GetPaths():
                #wx.LogMessage(filepath)
                if os.path.isfile(filepath):
                    ret = dv_info.dvinfo(filepath)
                    if ret:
                        self.SrcList[filepath] = ret
        dlg.Destroy()
        self.srcListCtrl.SetSortList(self.SrcList)

    def OnClickAdd(self, event):
        if self.dstCtrl.GetValue() == 0:
            return
        files = self.srcListCtrl.ItemSelected()
        #print files
        if 0 == len(files):
            return
        ar16_9 = None
        for f in files:
            #print self.SrcList[f]
            if ar16_9 == None:
                ar16_9 = self.SrcList[f][2]
            else:
                if ar16_9 != self.SrcList[f][2]:
                    wx.LogMessage("Can't mix 16:9 and 4:3 source")
                    return
        for f in files:
            tmp = {}
            for k in self.SrcList.keys():
                if k != f:
                    tmp[k] = self.SrcList[k]
            self.SrcList = tmp
        self.srcListCtrl.SetSortList(self.SrcList)
        self.jobListCtrl.AddJob([self.dstCtrl.GetValue(), files, ar16_9])
        self.ChangeTimeInfo()

    def OnClickDel(self, event):
        jobs = self.jobListCtrl.ItemSelectedDel()
        for files in jobs:
            for f in files:
                ret = dv_info.dvinfo(f)
                if ret:
                    self.SrcList[f] = ret
        self.srcListCtrl.SetSortList(self.SrcList)
        self.ChangeTimeInfo()

    def OnClickStart(self, event):
        if self.threadlock.locked():
            wx.LogMessage("another thread have run...")
        else:
            id = thread.start_new_thread(self.jobListCtrl.vdub, (self.threadlock,self.write_log))
            wx.LogMessage("job thread id: %d" % id)

    def write_log(self, text):
        if text[-1] == '\n':
            text = text[:-1]
        wx.LogMessage(text)
    
    def ChangeTimeInfo(self, event=None):
        self.srcListCtrl.ItemSelected()
        if self.srcListCtrl.seconds == 0:
            self.selectedLength.SetLabel("%d second" % self.srcListCtrl.seconds)
        else:
            self.selectedLength.SetLabel("%d seconds" % self.srcListCtrl.seconds)
        return
    
    def OnCloseWindow(self, event):
        app.keepGoing = False
        self.Destroy()


#---------------------------------------------------------------------------

class MyApp(wx.App):
    def MainLoop(self):

        if "wxMac" in wx.PlatformInfo:
            # TODO:  Does wxMac implement wxEventLoop yet???
            wx.App.MainLoop()

        else:
            # Create an event loop and make it active.  If you are
            # only going to temporarily have a nested event loop then
            # you should get a reference to the old one and set it as
            # the active event loop when you are done with this one...
            evtloop = wx.EventLoop()
            old = wx.EventLoop.GetActive()
            wx.EventLoop.SetActive(evtloop)

            # This outer loop determines when to exit the application,
            # for this example we let the main frame reset this flag
            # when it closes.
            while self.keepGoing:
                # At this point in the outer loop you could do
                # whatever you implemented your own MainLoop for.  It
                # should be quick and non-blocking, otherwise your GUI
                # will freeze.  

                # call_your_code_here()


                # This inner loop will process any GUI events
                # until there are no more waiting.
                while evtloop.Pending():
                    evtloop.Dispatch()

                # Send idle events to idle handlers.  You may want to
                # throttle this back a bit somehow so there is not too
                # much CPU time spent in the idle handlers.  For this
                # example, I'll just snooze a little...
                time.sleep(0.10)
#                self.ProcessIdle()

            wx.EventLoop.SetActive(old)



    def OnInit(self):
        frame = MyFrame(None, -1, "DV -> XviD")
        frame.Show(True)
        self.SetTopWindow(frame)

        self.keepGoing = True
        return True


app = MyApp(False)
app.MainLoop()
