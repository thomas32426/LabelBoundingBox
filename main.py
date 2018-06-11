from tkinter import *
from PIL import Image, ImageTk
import tkinter.ttk as ttk
import os
import glob
import random
import json

# colors for the bounding boxes
COLORS = {}
colorList = ['#000000', '#cc0000', '#0000ff', '#6600cc', '#33cc33', '#ff6600', '#ff00ff', '#00ffff']

# noinspection PyUnusedLocal
class LabelTool:
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("LabelTool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = FALSE, height = FALSE)

        # Initialize global state
        self.imageDir = ''
        self.imageList= []
        self.egDir = ''
        self.egList = []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.category = None
        self.imageName = ''
        self.img = None
        self.labelFileName = ''
        self.tkImg = None
        self.tmp = []
        self.currentLabelClass = ''
        self.cla_can_temp = []
        self.classCandidateFileName = 'class.txt'
        self.rescaleFactor = 1
        self.stickModeOn = False

        # Initialize mouse state
        self.STATE = dict()
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

        # Reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.hl = None
        self.vl = None

        
        # ----------------- GUI stuff ---------------------
        # Directory entry and loading
        self.label = Label(self.frame, text = "Image Dir:")
        self.label.grid(row = 0, column = 0, sticky = E)
        self.entry = Entry(self.frame)
        self.entry.grid(row = 0, column = 1, sticky = W+E)
        self.ldBtn = Button(self.frame, text = "Load", command = self.loadDir)
        self.ldBtn.grid(row = 0, column = 2,sticky = W+E)

        # Main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor ='tcross')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind("<Escape>", self.cancelBBox)  # Press escape key to cancel current bbox
        self.parent.bind("<Left>", self.prevImage) # Press left arrow to go backforward
        self.parent.bind("<Right>", self.nextImage) # Press right arrow to go forward

        self.mainPanel.grid(row = 1, column = 1, rowspan = 4, sticky = W+N)

        # Choose class
        self.className = StringVar()
        self.classCandidate = ttk.Combobox(self.frame, state='readonly', textvariable=self.className)
        self.classCandidate.grid(row=1,column=2)
        self.classCandidate.bind("<<ComboboxSelected>>", self.setClass)
        if os.path.exists(self.classCandidateFileName):
            with open(self.classCandidateFileName) as cf:
                for idx, line in enumerate(cf.readlines()):
                    tmp = line.strip('\n')
                    self.cla_can_temp.append(tmp)
                    COLORS[tmp] = colorList[idx]
                    
        self.classCandidate['values'] = self.cla_can_temp
        self.classCandidate.current(0)
        self.currentLabelClass = self.classCandidate.get() #init
        self.btnClass = Button(self.frame, text = 'Stick Mode', command = self.stickMode)
        self.btnClass.grid(row=2,column=2,sticky = W + E)

        # Bind keyboard keys to classes
        self.parent.bind("0", self.keyboardSetClass)
        self.parent.bind("1", self.keyboardSetClass)
        self.parent.bind("2", self.keyboardSetClass)
        self.parent.bind("3", self.keyboardSetClass)
        self.parent.bind("4", self.keyboardSetClass)
        self.parent.bind("5", self.keyboardSetClass)
        self.parent.bind("6", self.keyboardSetClass)
        self.parent.bind("7", self.keyboardSetClass)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text = 'Bounding boxes:')
        self.lb1.grid(row = 3, column = 2,  sticky = W + N)
        self.listbox = Listbox(self.frame, width = 22, height = 12)
        self.listbox.grid(row = 4, column = 2, sticky = N + S)
        self.btnDel = Button(self.frame, text = 'Delete', command = self.delBBox)
        self.btnDel.grid(row = 5, column = 2, sticky = W + E + N)
        self.btnClear = Button(self.frame, text = 'ClearAll', command = self.clearBBox)
        self.btnClear.grid(row = 6, column = 2, sticky = W + E + N)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row = 7, column = 1, columnspan = 2, sticky = W + E)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width = 10, command = self.prevImage)
        self.prevBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width = 10, command = self.nextImage)
        self.nextBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.progLabel = Label(self.ctrPanel, text = "Progress:     /    ")
        self.progLabel.pack(side = LEFT, padx = 5)
        self.tmpLabel = Label(self.ctrPanel, text = "Go to Image No.")
        self.tmpLabel.pack(side = LEFT, padx = 5)
        self.idxEntry = Entry(self.ctrPanel, width = 5)
        self.idxEntry.pack(side = LEFT)
        self.goBtn = Button(self.ctrPanel, text = 'Go', command = self.gotoImage)
        self.goBtn.pack(side = LEFT)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side = RIGHT)

        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(4, weight = 1)

    def loadDir(self, dbg = False):
        if not dbg:
            s = self.entry.get()
            self.parent.focus()
            self.category = str(s)
        else:
            s = r'./data/trainingSetA'

        # get image list
        self.imageDir = os.path.join(self.imageDir, '%s' %self.category)
        self.imageList = glob.glob(os.path.join(self.imageDir, '*.JPG'))
        if len(self.imageList) == 0:
            print('No .JPG images found in the specified dir!')
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

        # set up output dir
        # self.outDir = os.path.join(self.outDir, '%s' %self.category)
        # if not os.path.exists(self.outDir):
        #     os.mkdir(self.outDir)
        self.outDir = self.imageDir
        print('%d images loaded from %s' %(self.total, s))
        self.loadImage()    

    def loadImage(self):
        # load image
        imagePath = self.imageList[self.cur - 1]
        self.img = Image.open(imagePath)
        
        # resize image by rescale factor
        self.img = self.img.resize((self.img.size[0] // self.rescaleFactor, self.img.size[1] // self.rescaleFactor))
        
        self.tkImg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width = max(self.tkImg.width(), 400), height = max(self.tkImg.height(), 400))
        self.mainPanel.create_image(0, 0, image = self.tkImg, anchor=NW)
        self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))

        # load labels
        self.clearBBox()
        self.imageName = os.path.split(imagePath)[-1].split('.')[0]
        labelname = self.imageName + '.json'
        self.labelFileName = os.path.join(self.outDir, labelname)

        if os.path.exists(self.labelFileName):
            with open(self.labelFileName, 'r') as json_file:
                d = json.load(json_file)
                for key, val in d.items():
                    if key != 'box':
                        print(key, val)

            if 'box' in d.keys():
                for (i, line) in enumerate(d['box']):
                    self.bboxList.append(tuple(line))
                    tmpId = self.mainPanel.create_rectangle(int(line[1])//self.rescaleFactor, int(line[2])//self.rescaleFactor, int(line[3])//self.rescaleFactor, int(line[4])//self.rescaleFactor, width = 2,
                                                            outline = COLORS[line[0]])
                    self.bboxIdList.append(tmpId)
                    self.listbox.insert(END, '%s : (%d, %d) -> (%d, %d)' %(line[0],int(line[1]), int(line[2]),
                                                                            int(line[3]), int(line[4])))
                    self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[line[0]])

    def saveImage(self):
        try:
            with open(self.labelFileName, 'r') as json_file:
                d = json.load(json_file)
            
            boxes = []
            for bbox in self.bboxList:
                boxes.append(list(bbox))

            with open(self.labelFileName, 'w') as json_file:
                if 'box' in d.keys():
                    if len(boxes) == 0:
                        d.pop('box', None)
                    else:
                        d['box'] = boxes  
                else:
                    d['box'] = boxes

                json.dump(d, json_file, indent=4, sort_keys=True)
            
            print('Image No. %d saved' %self.cur)
        except FileNotFoundError:
            print("Make sure %s exists first. Nothing was saved." %self.labelFileName)


    def mouseClick(self, event):
        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
        else:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
            self.bboxList.append((self.currentLabelClass, x1*self.rescaleFactor, y1*self.rescaleFactor, x2*self.rescaleFactor, y2*self.rescaleFactor))
            self.bboxIdList.append(self.bboxId)
            self.bboxId = None
            self.listbox.insert(END, '%s : (%d, %d) -> (%d, %d)' %(self.currentLabelClass,x1*self.rescaleFactor, y1*self.rescaleFactor, x2*self.rescaleFactor, y2*self.rescaleFactor))
            self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[self.currentLabelClass])
        self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        self.disp.config(text = 'x: %d, y: %d' %(event.x, event.y))
        if self.tkImg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkImg.width(), event.y, width = 2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkImg.height(), width = 2)
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'], event.x, event.y,
                                                          width = 2, outline = COLORS[self.currentLabelClass])

    def cancelBBox(self, event):
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE['click'] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        if len(sel) != 1:
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.bboxList.pop(idx)
        self.listbox.delete(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        self.listbox.delete(0, len(self.bboxList))
        self.bboxIdList = []
        self.bboxList = []

    def prevImage(self, event = None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event = None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

    def setClass(self, *args):
        self.currentLabelClass = self.classCandidate.get()
    
    def keyboardSetClass(self, event):
        if event.char == '0':
            self.classCandidate.current(0)
        elif event.char == '1':
            self.classCandidate.current(1)
        elif event.char == '2':
            self.classCandidate.current(2)
        elif event.char == '3':
            self.classCandidate.current(3)   
        elif event.char == '4':
            self.classCandidate.current(4)
        elif event.char == '5':
            self.classCandidate.current(5)
        elif event.char == '6':
            self.classCandidate.current(6)
        elif event.char == '7':
            self.classCandidate.current(7)
        
        self.currentLabelClass = self.classCandidate.get()

    def stickMode(self):
        self.stickModeOn = not self.stickModeOn
        if self.stickModeOn == True:
            print("Stick mode activated!")
        else:
            print("Stick mode deactivated!")

if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width=True, height=True)
    root.mainloop()