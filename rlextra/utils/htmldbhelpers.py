#copyright ReportLab Europe Limited. 2000-2016
# helpers for making html forms for updating db records.

__version__='3.3.0'


### should check html quoting everywhere someday! (eg in hidden fields)
### should generalize to support non unary foreign keys

def timedict():
    from time import localtime, time
    (year, month, day, hour, mm, ss, ms, x, y) = localtime(time())
    return {"year":year, "month":month, "day":day, "hour": hour, "minute":mm}

nowdict = timedict()

def dayselect(name="day", selected=None, values=list(range(1,32)), names=list(range(1,32)),width=None, onchange=None):
    if selected is None:
        selected = nowdict["day"]
    if onchange and width:
        L = ["""<select name="%s" style="width: %s" onchange="%s">""" % (name, width, onchange)]
    elif width:
        L = ["""<select name="%s" style="width: %s">""" % (name, width)]
    else:
        L = ["""<select name="%s">""" % name]
    for i in range(len(values)):
        namei = names[i]
        valuei = values[i]
        li = """   <option value="%s">%s</option>""" % (valuei, namei)
        if selected==valuei:
            li = """      <option selected value="%s">%s</option>""" % (valuei, namei)
        L.append(li)
    L.append("</select>")
    return '\n'.join(L)

nowdayselect = dayselect()

def select(name, names, values, selected=None,width=None, onchange=None):
    """<select...> html element"""
    if len(names)!=len(values):
        raise ValueError("names and values of different len")
    if selected is not None and selected not in values:
        raise ValueError("selected %s not in values: %s..." % (repr(selected), repr(values[0])))
    return dayselect(name=name, names=names, values=values, selected=selected, width=width, onchange=onchange)

def monthselect(name="month", selected=None):
    if selected is None:
        selected = nowdict["month"]
    values = list(range(1,12))
    import calendar
    names = calendar.month_name[1:]
    return dayselect(name, selected, values, names)

nowmonthselect = monthselect()

def yearselect(name="year", selected=None, past=5, forward=5):
    if selected is None:
        selected = nowdict["year"]
    values = list(range(selected-past, selected+forward+1))
    return dayselect(name, selected, values, values)

def hiddenFields(pairs):
    L = []
    for (name, value) in pairs:
        h = """<input type="hidden" name="%s" value="%s">""" % (name, value)
        L.append(h)
    return "\n".join(L)

class DateField:

    def __init__(self, month=None, day=None, year=None, epoch=None):
        import time
        if epoch is not None:
            (year, month, day, hour, mm, ss, ms, x, y) = time.localtime(epoch)
        else:
            if year is None:
                year = nowdict["year"]
            if day is None:
                day = nowdict["day"]
            if month is None:
                month = nowdict["month"]
            epoch = time.mktime( (year,month,day, 0, 0, 0, 0, 0, 0) )
        #print year, month, day, epoch, "<br>"
        self.year, self.month, self.day, self.epoch = year, month, day, epoch
        #print "epoch", epoch, "<br>"
    def htmlData(self):
        from calendar import month_name
        nameofmonth = month_name[self.month]
        return "%s %s %s" % (self.day, nameofmonth, self.year)
    def formField(self, prefix, table, join=1, separator=" "):
        ys = yearselect(prefix+"_yr", self.year)
        ms = monthselect(prefix+"_mn", self.month)
        ds = dayselect(prefix+"_dy", self.day)
        L = [ys, ms, ds]
        if not join: return L
        return separator.join(L)
    def PDFdata(self):
        return self.htmlData() # default
    def hiddenFormField(self, prefix):
        return hiddenFields( [(prefix+"_yr", self.year), (prefix+"_mn", self.month), (prefix+"_dy", self.day)] )
    def initFromDataValue(self, d):
        self.__init__(epoch=d)
    def initFromCGI(self, prefix, cgiform):
        D = {}
        for (suffix, kw) in [("_yr", "year"), ("_mn", "month"), ("_dy", "day")]:
            f = cgiform[prefix+suffix]
            v = f.value
            D[kw] = int(v)
        #print D, "<br>"
        self.__init__(*(), **D)
    def testCGI(self, prefix, cgiform):
        for suffix in ("_yr", "_mn", "_dy"):
            try:
                cgiform[prefix+suffix]
            except:
                #print "test failed", prefix, suffix, "<br>"
                return 0
        return 1
    def dataValue(self):
        return self.epoch
    sqlDataType = "float"
    def sqlLiteral(self):
        return str(self.epoch)

class SmallStringField(DateField):
    sqlDataType = "varchar"
    def __init__(self):
        self.value = ""
    def htmlData(self):
        return self.value
    def formField(self, name, table):
        return """<input type="text" name="%s" value="%s">""" % (name, self.value)
    def initFromCGI(self, prefix, cgiform):
        try:
            f = cgiform[prefix]
        except:
            self.value = "" # no value default
        else:
            v =  f.value
            # hack out anomalies!
            v = v.split("\n")
            v = list(map(str.strip, v))
            v = "\n".join(v)
            self.value = v
    def testCGI(self, prefix, cgiform):
        try:
            cgiform[prefix]
        except:
            return 0
        else:
            return 1
    def initFromDataValue(self, d):
        self.value = d
    def dataValue(self):
        return self.value
    def sqlLiteral(self):
        #print self.value
        v2 = self.value.replace("'","''")
        return "'%s'" % v2
    def hiddenFormField(self, prefix):
        return hiddenFields( [(prefix, self.value)] )

class ForeignKey(SmallStringField):
    "not implemented"

class LargeStringField(SmallStringField):
    def htmlData(self):
        "truncated"
        return """<pre>%s</pre>""" % self.value
    def PDFdata(self):
        return self.value # default
    def formField(self, name, table):
        #print self.value
        return """<textarea name="%s" cols=60 rows=5>%s</textarea>"""%(name, self.value)

class Table:

    def __init__(self, name, PrimaryKeySeq, fieldclasspairs):
        self.name = name
        fieldclassmap = {}
        fieldsequence = []
        for (name, klass) in fieldclasspairs:
            if name in fieldclassmap:
                raise ValueError("field name declared twice %s" % name)
            fieldclassmap[name] = klass
            fieldsequence.append(name)
        for pkf in PrimaryKeySeq:
            if pkf not in fieldclassmap:
                raise ValueError("primary key field not declared %s" % pkf)
        self.fieldclassmap = fieldclassmap
        self.fieldsequence = fieldsequence
        self.primarykeysequence = tuple(PrimaryKeySeq)
        self.actions = []
        #self.makeDeleteAction()
    def CGIfields(self, form):
        result = {}
        for (name, klass) in list(self.fieldclassmap.items()):
            fi = klass()
            test = fi.testCGI(name, form)
            if test:
                fi.initFromCGI(name, form)
                result[name] = fi.dataValue()
        return result
    def makeDeleteAction(self, actionname, method="post", miscdata=""):
        miscdata = miscdata+hiddenFields([("table_action", "delete"), ("table_name", self.name)])
        deleteaction = addedaction_notranslate("delete", self.fieldsequence, actionname, miscdata, method)
        self.add_action(deleteaction)
    def add_action(self, action):
        self.actions.append(action)
    def createStatement(self):
        L = ["create table %s (\n" % self.name]
        a = L.append
        fcm = self.fieldclassmap
        started = 0
        for f in self.fieldsequence:
            if started: a(",\n")
            started = 1
            k = fcm[f]
            ty = k.sqlDataType
            a("    %s %s" % (f, ty))
        a("\n)")
        return ' '.join(L)
    def primaryIndex(self):
        n = self.name
        L = ["create unique index PK_%s on %s (" % (n,n)]
        a = L.append
        started = 0
        for k in self.primarykeysequence:
            if started: a(",")
            started = 1
            a(k)
        a(")")
        return ' '.join(L)
    # XXX should add other index support
    insertPrefixCached = None
    def insertPrefix(self):
        if self.insertPrefixCached: return self.insertPrefixCached
        L = ["insert into %s ( " % self.name]
        a = L.append
        started = 0
        for f in self.fieldsequence:
            if started: a(",")
            started = 1
            a(f)
        a(") values ")
        r = self.insertPrefixCached = ' '.join(L)
        return r
    def insert(self, dictionary):
        ### !!! should optimize
        L = [self.insertPrefix()]
        a = L.append
        fieldclassmap = self.fieldclassmap
        started = 0
        a("\n   (")
        #for (a,b) in dictionary.items(): print a,b,"<br>"
        for f in self.fieldsequence:
            if started: a(",")
            started = 1
            fc = fieldclassmap[f]
            fi = fc()
            v = dictionary[f]
            fi.initFromDataValue(v)
            lit = fi.sqlLiteral()
            a(lit)
        a(")")
        return ' '.join(L)
    def whereMatch(self, dictionary):
        L = ["where\n   "]
        a = L.append
        fieldclassmap = self.fieldclassmap
        started = 0
        for k in list(dictionary.keys()):
            if started: a("\n   and")
            started = 1
            fc = fieldclassmap[k]
            fi = fc()
            v = dictionary[k]
            fi.initFromDataValue(v)
            lit = fi.sqlLiteral()
            a("%s=%s" % (k,lit))
        return ' '.join(L)
    def delWhere(self, dictionary):
        return "delete from %s\n%s" %(self.name, self.whereMatch(dictionary))
    def selWhere(self, dictionary=None):
        order_by = ", ".join(self.primarykeysequence)
        select_list = ", ".join(self.fieldsequence)
        whereclause = ""
        if dictionary: whereclause = self.whereMatch(dictionary)
        return "select %s\nfrom %s\n%s\norder by %s" %(select_list, self.name, whereclause, order_by)
    # no modify support yet
    def insertForm(self, action, miscdata, method="post", dictionary=None):
        # use misc data to insert, eg standard hidden fields
        if not dictionary: dictionary = {}
        L = []
        a = L.append
        a("""<form action="%s" method="%s">""" % (action, method))
        fieldclassmap = self.fieldclassmap
        a(miscdata)
        for f in self.fieldsequence:
            fc = fieldclassmap[f]
            fi = fc()
            v = dictionary.get(f, None)
            if v is not None:
                fi.initFromDataValue(v)
            ff = fi.formField(f, self)
            a("%s: %s<br>" % (f, ff))
        a("""<input type="hidden" name="table_action" value="insert">""")
        a("""<input type="hidden" name="table_name" value=%s>""" % self.name)
        a("""<input type="submit" value="add entry">""")
        a("""</form>""")
        return "\n".join(L)
    def whereTable(self, cursor, dictionary=None):
        L = []
        a = L.append
        wherestatement = self.selWhere(dictionary)
        a("<pre>")
        a(wherestatement)
        cursor.execute(wherestatement)
        a("</pre>")
        a("<hr>")
        a("<table>\n")
        fieldsequence = self.fieldsequence
        fieldclassmap = self.fieldclassmap
        actions = self.actions
        a("<tr>\n")
        for n in fieldsequence:
            a("<th> %s </th>"%n)
        a("</tr>\n")
        for resultrow in cursor.fetchall():
            a("<tr>")
            D = {}
            for (name, value) in map(None, fieldsequence, resultrow):
                fc = fieldclassmap[name]
                fi = fc()
                fi.initFromDataValue(value)
                D[name] = fi
                hd = fi.htmlData()
                a("<td> %s </td>" % hd)
            for act in actions:
                doit = act(D)
                a("<td> %s </td>" % doit)
            a("</tr>\n")
        a("</table>")
        return " ".join(L)
    def pdfrows(self, cursor, dictionary):
        "return list of dictionary or pdf formattable data for selection"
        result = []
        wherestatement = self.selWhere(dictionary)
        print(wherestatement)
        cursor.execute(wherestatement)
        fieldsequence = self.fieldsequence
        fieldclassmap = self.fieldclassmap
        resultrows = cursor.fetchall()
        print(len(resultrows), "rows")
        for resultrow in resultrows:
            D = {}
            for (name, value) in map(None, fieldsequence, resultrow):
                fc = fieldclassmap[name]
                fi = fc()
                fi.initFromDataValue(value)
                D[name] = fi.PDFdata()
            result.append(D)
        return result

def addedaction_notranslate(button, names, action, miscdata="", method="post"):
    D = {}
    for n in names:
        D[n] = n
    return addedaction(button, D, action, miscdata, method)

class addedaction:
    def __init__(self, button, nametranslation, action, miscdata="", method="post"):
        self.nametranslation = nametranslation
        self.button = button
        self.action = action
        self.method = method
        self.miscdata = miscdata
    def __call__(self, dictionary):
        # dictionary should be oldname to field *instances!*
        nametranslation = self.nametranslation
        action = self.action
        button = self.button
        method = self.method
        L = []
        a = L.append
        a("""<form action= "%s" method="%s">""" %(action, method))
        for oldname in list(nametranslation.keys()):
            newname = nametranslation[oldname]
            fieldvalue = dictionary[oldname]
            hidden = fieldvalue.hiddenFormField(newname)
            a(hidden)
        a(self.miscdata)
        a("""<input type="submit" value="%s">""" % button)
        a("""</form>""")
        return "\n".join(L)

nowyearselect = yearselect()

if __name__=="__main__":
   fn = "test.html"
   f = open(fn, "w")
   D = {}
   D["month"] = nowmonthselect
   D["year"] = nowyearselect
   D["day"] = nowdayselect
   f.write("""
   <form action="test.cgi">
   %(month)s %(day)s %(year)s<br>
   <input type="submit">
   </form>""" % D)
   f.close()
   print("wrote", fn)
   print("now creating database")
   fn = "test2.html"
   import sys
   sosave = sys.stdout
   ff = sys.stdout = open(fn, "w")
   print("<pre>")
   client = Table("client", ["handle"],
       [("handle", SmallStringField), ("contact", SmallStringField), ("started", DateField)])
   client.makeDeleteAction("delete")
   print();print(client.createStatement())
   print();print(client.primaryIndex())
   print();print(client.insertPrefix())
   D = {"handle": "woogie"}
   import time
   D2 = {"handle": "woogie", "contact": "poogie", "started": time.time()}
   print();print(client.insert(D2))
   print();print(client.whereMatch(D))
   print();print(client.delWhere(D))
   print();print(client.selWhere(D))
   print("</pre>")
   print(client.insertForm("action", "miscdata", "post", D))
   print("<hr>")
   import gadfly
   g = gadfly.gadfly()
   g.startup("dbtest", ".")
   c = g.cursor()
   c.execute(client.createStatement())
   c.execute(client.primaryIndex())
   c.execute(client.insert(D2))
   print(client.whereTable( c, dictionary=D))
   sys.stdout = sosave
   ff.close()
   print("wrote", fn, "for testing now finishing db init")
   c.execute("delete from client")
