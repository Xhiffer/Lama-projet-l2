#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history www.reportlab.co.uk/rl-cgi/viewcvs.cgi/rlextra/graphics/guiedit/guidialogs.py
__version__='3.3.0'
'''A specialized combo box based on Pmw's ComboBox class'''
import base64
from reportlab.graphics import renderPM
import Pmw
import collections
try:
	import tkinter
except ImportError:
	import Tkinter as tkinter

class PMDisplay(Pmw.ScrolledFrame):
	def __init__(self, parent,**kw):
		Pmw.ScrolledFrame.__init__(*(self,parent), **kw)
		self.initialiseoptions(PMDisplay)

	def newDrawing(self, zoom, d, text):
		w, h = int(zoom*d.width+0.5), int(zoom*d.height+0.5)
		if zoom!=1.0:
			from reportlab.graphics.shapes import Drawing
			d = Drawing(w,h,d,transform=(zoom,0,0,zoom,0,0))
		dim = d.width,d.height
		ds = renderPM.drawToString(d,fmt='gif')
		ndim = d.width,d.height
		if ndim!=dim:
			print('size changed dim=%r ndim=%r' % (dim,ndim))
			w, h = int(d.width+0.5), int(d.height+0.5)
			ds = renderPM.drawToString(d,fmt='gif')
		self._image = tkinter.PhotoImage(
				data=base64.encodestring(ds),
				width=w,
				height=h,
				format='gif')
		if hasattr(self,'_label'): self._label.grid_forget()
		frame = self.interior()
		self._label = tkinter.Label(frame, width=w, height=h, image=self._image)
		self._label.grid(row=0, column=0, sticky = 'news')
		self['label_text'] = text
		frame.grid_rowconfigure(0, weight = 1)
		frame.grid_columnconfigure(0, weight = 1)
		self.reposition()

def _flipCmd(m,cmd,label,flip,fg):
	i = m.index(label+'*')
	v = (flip.index(m.entrycget(i,'label')[len(label)+1:])+1) % len(flip)
	m.entryconfigure(i,label='%s %s' % (label,flip[v]),foreground=fg[v])
	if cmd: cmd(v)

def _addFlipButton(menu, label='', value=0, flip=['off','on'], fg=['darkred','darkgreen'], command=None):
	menu.add_command(label='%s %s' % (label,flip[value]),foreground=fg[value],
			command=lambda s=_flipCmd,m=menu,label=label,fg=fg,flip=flip,c=command: s(m,c,label,flip,fg))

class RL_MenuBar(Pmw.MainMenuBar):
	def __init__(self,parent,**kw):
		Pmw.MainMenuBar.__init__(*(self,parent), **kw)
		self.initialiseoptions(RL_MenuBar)

	def addFlipButton(self, menuName, statusHelp='', traverseSpec=None, label='', value=0,
		flip=['off','on'], fg=['darkred','darkgreen'],command=None,**kw):
		L = kw['label'] = '%s %s' % (label,flip[value])
		kw['foreground'] = fg[value]
		self.addmenuitem(menuName,'command',statusHelp,traverseSpec,**kw)
		#m = self.component(menuName + '-menu')
		m = self.component(menuName)
		m.entryconfigure(L,command=lambda s=_flipCmd,m=m,label=label,fg=fg,flip=flip,c=command: s(m,c,label,flip,fg))

	def insertmenuitem(self, menuName, index, itemType, statusHelp = '',
			traverseSpec = None, **kw):
		if itemType not in ('command', 'separator', 'checkbutton', 'radiobutton', 'cascade'):
			raise ValueError('unknown menuitem type "%s"' % itemType)
		menu = self.component(menuName)
		if itemType != 'separator':
			self._addHotkeyToOptions(menuName, kw, traverseSpec)
		menu.insert(index,itemType,kw)
		self._menuInfo[menuName][1].insert(index,statusHelp)

class RL_ScrolledText(Pmw.ScrolledText):
	def __init__(self,*args,**kw):
		for a in ('colors','maxlines','autoclear','initText'):
			if a in list(kw.keys()):
				v = kw[a]
				del kw[a]
			else:
				v = None
			setattr(self,a,v)

		Pmw.ScrolledText.__init__(*(self,)+args, **kw)
		w = self._text = self.component('text')
		w.config(state='disabled')
		w.bind('<Button-1>', self._textB1)
		if self.colors:
			self._tag_config(self.colors)
			self._tagNames = tuple(self.colors.keys())
		else:
			self._tagNames = ()
		self.initialiseoptions(RL_ScrolledText)
		if self.initText:
			for k,m in self.initText:
				self.write(msg=m,kind=k)
			del self.initText[:]

	def _textB1(self,event):
		'''special binding for our disabled texts
		Allows dragging to select and copy, but not editing
		'''
		w, x, y = event.widget, event.x, event.y
		call = w.tk.call
		pfx = tkinter.TkVersion>=8.4 and '::tk::' or '::tk'
		call('set',pfx+'Priv(selectMode)','char')
		call('set',pfx+'Priv(mouseMoved)',0)
		call('set',pfx+'Priv(pressX)',x)
		call('set',pfx+'Priv(pressX)',x)
		w.mark_set('insert',call(pfx+'TextClosestGap',str(w),x,y))
		w.mark_set('anchor','insert')
		w.focus()
		w.tag_remove('sel','0.0','end')
		return 'break'


	def write(self,msg, kind=None, flush=0, norm=lambda m: m+(m and(m[-1]!='\n'and'\n'or'')or'\n')):
		w = self._text
		w.config(state='normal')
		if self.autoclear: w.delete('0.0','end')
		w.insert('end',norm(msg),kind)
		if self.maxlines: w.delete('1.0','end-%dl' % self.maxlines)
		w.see('end-2c')
		w.config(state='disabled')
		if flush: w.update()

	def destroy(self):
		if self.initText is not None:
			L = self.initText
			i=0
			for t in self.get('0.0', 'end').split('\n'):
				i = i+1
				for n in self.tag_names('%d.0' % i):
					if n in self._tagNames:
						L.append((n,t))
						break
		Pmw.ScrolledText.destroy(self)

	def clear(self,kind=None):
		w = self._text
		w.config(state='normal')
		if kind is not None:
			rg = w.tag_ranges(kind)
			for i in range(0,len(rg),2):
				w.delete(rg[i],rg[i+1])
		else:
			w.delete('0.0','end')
		w.config(state='disabled')

	def _tag_config(self,V):
		w = self._text
		for k, v in list(V.items()):
			rg = w.tag_ranges(k)
			w.tag_configure(k,v)
			if len(rg): w.tag_add(k,rg[0],rg[1:])
			w.tag_configure(k,v)

class NameDialog(Pmw.Dialog):
	'''
	Dialog window displaying a list and entry field and requesting
	the user to make a selection or enter a value
	'''
	def __init__(self, parent=None, **kw):
		# Define the megawidget options.
		INITOPT = Pmw.INITOPT
		optiondefs = (
			('borderx',    10,	  INITOPT),
			('bordery',    10,	  INITOPT),
			('namelabel',	None,	None),
			)
		self.defineoptions(kw, optiondefs)

		# Initialise the base class (after defining the options).
		Pmw.Dialog.__init__(self, parent)

		# Create the components.
		interior = self.interior()

		aliases = (
			('listbox', 'combobox_listbox'),
			('scrolledlist', 'combobox_scrolledlist'),
			('entry', 'combobox_entry'),
			('label', 'combobox_label'),
			)
		if self['namelabel']:
			self._nameField = self.createcomponent('name',
				(),None,Pmw.EntryField, (interior,),
				labelpos='w',
				label_text = self['namelabel'],
				)
			self._nameField.pack(side='top',expand='true',fill='x',
				padx = self['borderx'], pady = self['bordery'])

		self._combobox = self.createcomponent('combobox',
				aliases, None,
				Pmw.ComboBox, (interior,),
				scrolledlist_dblclickcommand = self.invoke,
				dropdown = 0,
				)

		self._combobox.pack(side='top', expand='true', fill='both',
				padx = self['borderx'], pady = self['bordery'])

		if 'activatecommand' not in kw:
			# Whenever this dialog is activated, set the focus to the
			# ComboBox's listbox widget.
			listbox = self.component('listbox')
			self.configure(activatecommand = listbox.focus_set)

		# Check keywords and initialise options.
		self.initialiseoptions(NameDialog)

	# Need to explicitly forward this to override the stupid
	# (grid_)size method inherited from Tkinter.Toplevel.Grid.
	def size(self):
		return self._combobox.size()

	# Need to explicitly forward this to override the stupid
	# (grid_)bbox method inherited from Tkinter.Toplevel.Grid.
	def bbox(self, index):
		return self._combobox.bbox(index)

Pmw.forwardmethods(NameDialog, Pmw.ComboBox, '_combobox')

class EditTextDialog(Pmw.TextDialog):
	def __init__(self,initialText='',parent=None,**kwds):
		Pmw.TextDialog.__init__(self,parent=parent,**kwds)
		self.insert('end', initialText)
		self.configure(text_state = 'normal')
Pmw.forwardmethods(EditTextDialog, Pmw.ScrolledText, '_text')

class EditListDialog(Pmw.Dialog):
	'''
	Simple dialog to edit a list
	'''
	def __init__(self, parent = None, **kw):
		_getArrowBitmaps(parent)
		# Define the megawidget options.
		INITOPT = Pmw.INITOPT
		optiondefs = (
			('borderx',	10,    INITOPT),
			('bordery',	10,    INITOPT),
			('balloon',	None,	INITOPT),
			)
		self.defineoptions(kw, optiondefs)

		balloon = self['balloon']

		# Initialise the base class (after defining the options).
		Pmw.Dialog.__init__(self, parent)

		# Create the components.
		interior = self.interior()

		aliases = (
			('listbox', 'combobox_listbox'),
			('scrolledlist', 'combobox_scrolledlist'),
			('entry', 'combobox_entry'),
			('label', 'combobox_label'),
			)

		r = 0	#grid row
		self._combobox = self.createcomponent('combobox',
				aliases, None,
				Pmw.ComboBox, (interior,),
				scrolledlist_selectioncommand = None,
				dropdown = 0,
			)
		self._combobox.grid(row=r,column=0,columnspan=4,sticky='news',padx=self['borderx'],pady=self['bordery'])
		interior.rowconfigure(r, weight=1)
		interior.columnconfigure(1, weight=1)
		interior.columnconfigure(2, weight=1)
		self.__listbox = self.component('listbox')
		self._entry = self.component('entry')

		r = 2	#grid row
		b = self._db = tkinter.Button(interior, image='DNArrow',height=1,command = self._dnCmd)
		b.grid(column=0,row=r,sticky='nsew')
		if balloon: balloon.bind(b,'Move selected item down')

		b = self._ab = tkinter.Button(interior, text='add',height=1,command = self._addCmd)
		b.grid(column=1,row=r,sticky='nsew')
		if balloon: balloon.bind(b,'add entered value to list')

		b = self._kb = tkinter.Button(interior, text='del',height=1,command = self._delCmd)
		b.grid(column=2,row=r,sticky='nsew')
		if balloon: balloon.bind(b,'delete selected item')

		b = self._ub = tkinter.Button(interior, image='UPArrow',height=1,command = self._upCmd)
		b.grid(column=3,row=r,sticky='nsew')
		if balloon: balloon.bind(b,'Move selected item up')

		if 'activatecommand' not in kw:
			# Whenever this dialog is activated, set the focus to the
			# ComboBox's listbox widget.
			self.configure(activatecommand = self.__listbox.focus_set)

		#some additional bindings
		self.__listbox.bind('<Down>', self._dnCmd)
		self.__listbox.bind('<Up>', self._upCmd)

		# Check keywords and initialise options.
		self.initialiseoptions(EditListDialog)

	# Need to explicitly forward this to override the stupid
	# (grid_)size method inherited from Tkinter.Toplevel.Grid.
	def size(self):
		return self._combobox.size()

	# Need to explicitly forward this to override the stupid
	# (grid_)bbox method inherited from Tkinter.Toplevel.Grid.
	def bbox(self, index):
		return self._combobox.bbox(index)

	def __edit0(self,event):
		sels = self.getcurselection()
		if len(sels) == 0:
			return None, None
		else:
			item = sels[0]
			return (int(self.curselection()[0]), item)

	def getList(self):
		return self.__listbox.get(0,'end')

	def _addCmd(self,event=None):
		item = self.get().strip()
		if not item: return
		L = self.getList()
		if item in L: return
		i, _ = self.__edit0(event)
		if i is None: i = 0
		self.__listbox.insert(i,item)
		self.__listbox.select_set(i,i)

	def _delCmd(self,event=None):
		i, _ = self.__edit0(event)
		if i is not None:
			self.__listbox.delete(i)
			self.__listbox.select_clear(0,'end')

	def _upCmd(self,event=None):
		i, item = self.__edit0(event)
		if i:
			self.__listbox.delete(i)
			j = i-1
			self.__listbox.insert(j,item)
			self.__listbox.select_set(j,j)

	def _dnCmd(self,event=None):
		i, item = self.__edit0(event)
		if i is not None:
			self.__listbox.delete(i)
			j = i+1
			self.__listbox.insert(j,item)
			self.__listbox.select_set(j,j)

Pmw.forwardmethods(EditListDialog, Pmw.ComboBox, '_combobox')

class FolderField(Pmw.EntryField):
	'''
	EntryField for a folder name and a browse button
	'''
	def __init__(self, parent=None, **kw):
		# Define the megawidget options.
		optiondefs = ()
		self.defineoptions(kw, optiondefs)

		# Initialise the base class (after defining the options).
		Pmw.EntryField.__init__(self, parent)

		# Create the components.
		interior = self.interior()

		b = self.createcomponent('browse', (), 'Button', tkinter.Button,
						(interior,), text='...', command=self._browse)
		b.grid(row=2,column=3,sticky='ew',padx=5)
		interior.grid_columnconfigure(3, weight=0)

		# Check keywords and initialise options.
		self.initialiseoptions()

	def _browse(self):
		path = tkinter.filedialog.askdirectory(initialdir=self.getvalue() or None)
		if path:
			self.setentry(path)

class GoStartDialog(Pmw.Dialog):
	'''
	Simple dialog to get values for the GO command
	'''
	DRIVERS = ['pyodbc','mysql','odbc','mx.ODBC']
	def __init__(self, parent=None, **kw):
		isCSV = kw.pop('isCSV')
		for k,v in (
				('title','DataAwareDrawing Parameters'),
				('buttons',('OK','Cancel')),
				('defaultbutton','OK'),
				):
			kw.setdefault(k,v)
		# Define the megawidget options.
		INITOPT = Pmw.INITOPT
		optiondefs = (
			('balloon',	None,	INITOPT),
			('icwd',	'',	INITOPT),
			('isql',	'',	INITOPT),
			('ishow',	0, INITOPT),
			('iformats','', INITOPT),
			('imaxcharts',	'', INITOPT),
			('idb',    '',	INITOPT),
			('ipattern','',	INITOPT),
			('ioutdir',	'',INITOPT),
			)
		if not isCSV:
			optiondefs += (
			('ihost',	'', INITOPT),
			('iuser',	'', INITOPT),
			('ipasswd', '', INITOPT),
			('idriver', 0, INITOPT),
			)
		self.defineoptions(kw, optiondefs)

		# Initialise the base class (after defining the options).
		Pmw.Dialog.__init__(self, parent)

		# Create the components.
		interior = self.interior()
		for r,name in enumerate(('cwd','sql')):
			klass = name=='sql' and Pmw.EntryField or FolderField
			value=self['i'+name] or ''
			w = self.createcomponent(name,(),None,klass,interior,
				labelpos='w',
				label_text = name.upper(),
				value=value,
				)
			w.grid(row=r,column=0,columnspan=5,sticky='ew',padx=5,pady=5)
			interior.grid_rowconfigure(r, weight=0)
			setattr(self,'_'+name,w)
		r += 1
		('host','driver','user','passwd','db')
		for c,name in enumerate(isCSV and ('db',) or ('host','driver','user','passwd','db')):
			KW = dict(labelpos='n',label_text=name.capitalize())
			if name=='driver':
				klass = Pmw.OptionMenu
				KW['items']=self.DRIVERS
				KW['initialitem']=self['i'+name]
			else:
				klass = Pmw.EntryField
				KW['entry_width'] = name=='host' and 32 or 12
				KW['value']=self['i'+name] or ''
			if name=='passwd':
				KW['entry_show']='*'
			w = self.createcomponent(name,(),None,klass,interior,**KW)
			w.grid(row=r,column=c,sticky='ew',pady=5,padx=2)
			interior.grid_columnconfigure(c, weight=1)
			setattr(self,'_'+name,w)
		interior.grid_rowconfigure(r, weight=0)

		r += 1
		klass = Pmw.EntryField
		for c,name in enumerate(('formats','outdir','pattern','maxcharts')):
			w = self.createcomponent(name,(),None,klass,interior,
			labelpos='n',
			label_text=name.capitalize(),
			entry_width=name=='maxcharts' and 3 or 12,
			value=self['i'+name]) or ''
			w.grid(row=r,column=c,sticky=name!='maxcharts' and 'ew' or '',pady=5,padx=2)
			interior.grid_columnconfigure(c, weight=1)
			setattr(self,'_'+name,w)

		self._showVar = tkinter.IntVar()
		self._showVar.set(self['ishow'])
		F = tkinter.Frame(interior)
		tkinter.Label(F,text='Show Preview').pack(side='top')
		w = self.createcomponent('show',(),None,tkinter.Checkbutton,F,
				text = '',
				onvalue='1',
				offvalue='0',
				variable=self._showVar,
				)
		w.pack(side='top')
		setattr(self,'_ishow',w)
		F.grid(row=r,column=4,pady=5,padx=2)
		interior.grid_rowconfigure(r, weight=0)
		# Check keywords and initialise options.
		self.initialiseoptions()

dnColor='blue'
upColor='red'

class AttrListBox(Pmw.MegaWidget):
	def __init__(self, parent = None, **kw):
		_getArrowBitmaps(parent)

		# Define the megawidget options.
		INITOPT = Pmw.INITOPT
		optiondefs = (
			('labelmargin',			0,		  INITOPT),
			('labelpos',			None,	INITOPT),
			('listheight',			200,	INITOPT),
			('selectioncommand',	None,	None),
			('dblclickcommand',		   None,	None),
			('upcommand',			None,	None),
			('dncommand',			None,	None),
			('unique',				  1,		INITOPT),
		)
		self.defineoptions(kw, optiondefs)

		# Initialise the base class (after defining the options).
		Pmw.MegaWidget.__init__(self, parent)

		# Create the components.
		interior = self.interior()

		# Create the scrolled listbox
		self._list = self.createcomponent('scrolledlist',
				(('listbox', 'scrolledlist_listbox'),), None,
				Pmw.ScrolledListBox, (interior,),
				selectioncommand = self._selectCmd,
				dblclickcommand = self._dblCmd)
		self._list.grid(column=2, row=2, sticky='nsew')
		self.__listbox = self._list.component('listbox')

		ef = self.createcomponent('entryframe',
				(), None,
				tkinter.Frame, (interior,),
				)

		self._db = tkinter.Button(ef, image='DNArrow',command = self._dnCmd)
		self._db.grid(column=0,row=0,sticky='nsew')
		self._entryfield = self.createcomponent('entryfield',
				(('entry', 'entryfield_entry'),), None,
				Pmw.EntryField, (ef,))
		self._entryfield.grid(column=1, row=0, sticky='nsew')
		self._ub = tkinter.Button(ef, image='UPArrow',command = self._upCmd)
		self._ub.grid(column=2,row=0,sticky='nsew')

		ef.grid_columnconfigure(1, weight = 1)
		self._entryWidget = self._entryfield.component('entry')
		self.__listbox.configure(font=('Courier',10))
		ef.grid(column=2, row=3, sticky='nsew')

		interior.grid_columnconfigure(2, weight = 1)

		# The scrolled listbox should expand vertically.
		interior.grid_rowconfigure(2, weight = 1)

		# Create the label.
		self.createlabel(interior, childRows=2)

		self._entryWidget.bind('<Down>', self._next)
		self._entryWidget.bind('<Up>', self._previous)
		self._entryWidget.bind('<Control-n>', self._next)
		self._entryWidget.bind('<Control-p>', self._previous)
		self.__listbox.bind('<Down>', self._next)
		self.__listbox.bind('<Up>', self._previous)
		self.__listbox.bind('<Control-n>', self._next)
		self.__listbox.bind('<Control-p>', self._previous)

		# Check keywords and initialise options.
		self.initialiseoptions(AttrListBox)

	def destroy(self):
		Pmw.MegaWidget.destroy(self)

	#======================================================================
	# Public methods
	def get(self, first = None, last=None):
		if first is None:
			return self._entryWidget.get()
		else:
			return self._list.get(first, last)

	def invoke(self):
		return self._selectCmd()

	def _logAttrInfo(self):
		from rlextra.graphics.guiedit.guiedit import editor, _findLHS, _stripSub, exceptionLog
		attrHelp = getattr(editor,'attrHelp',None)
		if not attrHelp: return
		try:
			from reportlab.graphics.widgetbase import TypedPropertyCollection
			name = editor.getFullObjectName()
			aname = self._lastsetentry[1]
			unsub = aname[0]!='['
			lhs = _findLHS(name+(unsub and '.' or '')+aname)
			if lhs!=None: lhs = lhs[5:]
			if not unsub:
				sname, aname = _stripSub(aname)
				sname = '[%s].%s' % (sname,aname)
			else:
				sname = aname = _findLHS(aname)
			obj = editor.getSampleAttr(editor.attrRootName)
			if isinstance(obj,TypedPropertyCollection):
				obj = getattr(obj,'_value',obj)
			am = getattr(obj,'_attrMap',None)
			inMap = am and aname in am or 0
			value = editor.getSampleAttr(lhs)
			if inMap:
				from reportlab.lib.validators import isBoolean, OneOf
				ame = am[aname]
				desc = getattr(ame,'desc')
				I = []
				if desc:
					for l in desc.split('\n'):
						I.append(('    ')+l)
				validate = ame.validate
				if validate is isBoolean:
					if I: I.append('    boolean value=%s' % value)
				elif isinstance(validate,OneOf):
					if I: I.append('    one of %r\n    current value=%s' % (validate._enum,value))
				else:
					if I: I.append('    current value=%s' % repr(value))
				if I:
					I = '\n'.join([aname]+I)
					attrHelp.write(I,flush=1,kind='temporary')
					return
			attrHelp.write('\n%s\n    %s' % (aname,value in getattr(obj,'contents',[]) and 'child widget' or 'no attribute information'),kind='temporary',flush=1)
		except:
			exceptionLog('Error trying to show attibute info')

	def selectitem(self, index, setentry=1):
		if type(index) == bytes:
			text = index
			items = self._list.get(0, 'end')
			if text in items:
				index = list(items).index(text)
			else:
				raise IndexError('index "%s" not found' % text)
		elif setentry:
			text = self._list.get(0, 'end')[index]

		self._list.select_clear(0, 'end')
		self._list.select_set(index, index)
		self._list.activate(index)
		self.see(index)
		if setentry:
			self._lastsetentry = (index, text)
			self._entryfield.setentry(text)
			self._logAttrInfo()

	# Need to explicitly forward this to override the stupid
	# (grid_)size method inherited from Tkinter.Frame.Grid.
	def size(self):
		return self._list.size()

	# Need to explicitly forward this to override the stupid
	# (grid_)bbox method inherited from Tkinter.Frame.Grid.
	def bbox(self, index):
		return self._list.bbox(index)

	def clear(self):
		self._entryfield.clear()
		self._list.clear()

	# Private methods
	def _next(self, event):
		size = self.size()
		if size <= 1:
			return

		cursels = self.curselection()

		if len(cursels) == 0:
			index = 0
		else:
			index = int(cursels[0])
			if index == size - 1:
				index = 0
			else:
				index += 1

		self.selectitem(index)
		if event.widget is self._list._listbox: return 'break'

	def _previous(self, event):
		size = self.size()
		if size <= 1:
			return

		cursels = self.curselection()

		if len(cursels) == 0:
			index = size - 1
		else:
			index = int(cursels[0])
			if index == 0:
				index = size - 1
			else:
				index -= 1

		self.selectitem(index)
		if event.widget is self._list._listbox: return 'break'

	def __doCmd(self,event,cmdName):
		sels = self.getcurselection()
		if len(sels) == 0:
			item = None
		else:
			item = sels[0]
			self._lastsetentry = (int(self.curselection()[0]), item)
			self._entryfield.setentry(item)
			self._logAttrInfo()
		cmd = self[cmdName]
		if isinstance(cmd, collections.Callable):
			return cmd(item)

	def _selectCmd(self, event=None):
		return self.__doCmd(event,'selectioncommand')

	def _dblCmd(self, event=None):
		return self.__doCmd(event,'dblclickcommand')

	def _upCmd(self,event=None):
		return self.__doCmd(event,'upcommand')

	def _dnCmd(self,event=None):
		return self.__doCmd(event,'dncommand')

Pmw.forwardmethods(AttrListBox, Pmw.ScrolledListBox, '_list')
Pmw.forwardmethods(AttrListBox, Pmw.EntryField, '_entryfield')

def _getArrowBitmaps(master):
	if not master: master = tkinter._default_root
	master.tk.call('image','create', 'bitmap', 'DNArrow', '-foreground', dnColor,
'-data',
'''#define dnarrow_width 8
#define dnarrow_height 8
#define dnarrow_x_hot 0
#define dnarrow_y_hot 0
static char dnarrow_bits[] = {
0x0, 0x3c, 0x3c, 0xff, 0x7e, 0x3c, 0x18, 0x0,
};''')
	master.tk.call('image','create', 'bitmap', 'UPArrow', '-foreground', upColor,
'-data',
'''#define uparrow_width 8
#define uparrow_height 8
#define uparrow_x_hot 0
#define uparrow_y_hot 0
static char uparrow_bits[] = {
0x0, 0x18, 0x3c, 0x7e, 0xff, 0x3c, 0x3c, 0x0,
};''')
