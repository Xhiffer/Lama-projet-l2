#copyright ReportLab Europe Limited. 2000-2016
"Utilities for sending mail"

def _sendMail(smtpServer,sender,receiver,msg, user=None, password=None):
    import smtplib
    server = smtplib.SMTP(smtpServer)
    try:
        if user:
            server.login(user, password)
        server.sendmail(sender, receiver, msg)
    finally:
        server.quit()

import re
few_re = re.compile( '^=\\?.*\\?=$' )

def _encmin(u):
    """minimally encode unicode"""
    for enc in ('utf-8','iso-8859-1'):
        try:
            return u.encode(enc), enc
        except UnicodeEncodeError:
            pass
    return u.encode('utf-8'), 'utf-8'

def _xencmin(u, force=False):
    '''
    Used for minimally encoding a unicode into whatever is shortest.
    '''
    high_count = len([ x for x in u if ord(x) > 127])
    if not force:
        if high_count == 0:
            return u,'7bit'
    base64_count = (len(u)*4)/3
    if base64_count % 4:
        base64_count += 4 - ( base64_count % 4 )
    qp_count = len(u) + high_count * 2
    if base64_count < qp_count:
        return u.encode('base64'),'Base64'
    enc = '*'
    if '*' in u:
        if '^' not in u:
            enc = '^'
        elif '~' not in u:
            enc = '~'
        else:
            enc = None
    if enc:
        u = u.replace(' ',enc)
        u = u.encode('quoted-printable')
        u = u.replace(enc,' ')
        return u, 'Quoted-Printable'
    return u.encode('quoted-printable').replace('=20',' '),'Quoted-Printable'

def _encoded_word(word, enc='utf8', force=False):
    if not isinstance(word,str):
        word = word.decode(enc)
    wchr, charset = _encmin(word)
    force = force or few_re.match(wchr)
    wenc, enc = _xencmin(wchr, force=force)
    if enc == '7bit':
        return wenc,False
    else:
        menc = 'X'
        if enc == 'Base64':
            menc = 'B'
            wenc = ''.join(wenc.split('\n'))
        elif enc == 'Quoted-Printable':
            menc = 'Q'
            wenc = ''.join(wenc.split( '=\n' ))
            wenc = wenc.replace(' ','_')
            wenc = wenc.replace('?','=%X'%ord( '?' ) )
        return '=?%s?%s?%s?=' % (charset.upper(),menc,wenc), True

def encoded_word(word,enc='utf8',force=False):
    '''attempt a good encoded-word encoding of word http://en.wikipedia.org/wiki/MIME#Encoded-Word'''
    return _encoded_word(word,enc,force)[0]

def sendMail(smtpServer, sender, receiver, subject, text, fromaddr=None, user=None, password=None):
    "Sends a simple mail"
    if fromaddr is None: fromaddr=sender
    _sendMail(smtpServer,sender,receiver,
            "To: %s\nFrom: %s\nSubject: %s\n\n%s" % (receiver,fromaddr,subject, text), user=user, password=password)

class MailAttachment:
    def __init__(self,name,stream=None, mimeType=('application','octet-stream')):
        self.stream = stream
        self.name = name
        self.mimeType = mimeType
    def read(self):
        if self.stream:
            return self.stream.read()
        else:
            return open(self.name,'rb').read()

def sendEmail(smtpServer, toAddress, fromAddress, subject, msgBody, subjectEncoding=None, sender=None, user=None, password=None, attachments=[], isHtmlText=False):
    import os
    from email.MIMEText import MIMEText
    text = MIMEText(msgBody, (isHtmlText and 'html' or 'plain'), 'utf-8') # Assume text is UTF8
    if not attachments:
        msg = text
    else:
        from email.MIMEMultipart import MIMEMultipart
        from email.MIMEBase import MIMEBase
        from email import Encoders
        msg = MIMEMultipart()
        msg.attach(text)
        for f in attachments:
            name = os.path.basename(f.name)
            part = MIMEBase(*f.mimeType)
            part.set_payload(f.read())
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="%s"' % name )
            msg.attach(part)
    if subjectEncoding is not None:
        from email.Header import Header
        subject = Header(subject,subjectEncoding)
    msg['Subject'] = subject
    msg['From'] = fromAddress
    msg['To'] = toAddress
    if sender: msg['Sender'] = sender
    _sendMail(smtpServer,fromAddress,(toAddress,), msg.as_string(), user=user, password=password)

def sendHtmlMail(smtpServer, sender, receiver, subject, html, user=None, password=None):
    "Sends an html email (html argument is an HTML string)"
    import MimeWriter
    import mimetools
    import io

    # Produce an approximate textual rendering of the HTML string,
    # unless you have been given a better version as an argument
    import htmllib, formatter
    textout = io.StringIO()
    formtext = formatter.AbstractFormatter(formatter.DumbWriter(textout))
    parser = htmllib.HTMLParser(formtext)
    parser.feed(html)
    parser.close()
    text = textout.getvalue()
    del textout, formtext, parser

    out = io.StringIO() # output buffer for our message
    htmlin = io.StringIO(html)
    txtin = io.StringIO(text)

    writer = MimeWriter.MimeWriter(out)

    # Set up some basic headers. Place subject here
    # because smtplib.sendmail expects it to be in the
    # message body, as relevant RFCs prescribe.
    writer.addheader("Subject", subject)
    writer.addheader("MIME-Version", "1.0")

    # Start the multipart section of the message.
    # Multipart/alternative seems to work better
    # on some MUAs than multipart/mixed.
    writer.startmultipartbody("alternative")
    writer.flushheaders()

    # the plain-text section: just copied through, assuming iso-8859-1
    subpart = writer.nextpart()
    pout = subpart.startbody("text/plain", [("charset", 'iso-8859-1')])
    pout.write(txtin.read())
    txtin.close()

    # the HTML subpart of the message: quoted-printable, just in case
    subpart = writer.nextpart()
    subpart.addheader("Content-Transfer-Encoding", "quoted-printable")
    pout = subpart.startbody("text/html", [("charset", 'us-ascii')])
    mimetools.encode(htmlin, pout, 'quoted-printable')
    htmlin.close()

    # You're done; close your writer and return the message body
    writer.lastpart()
    msg = out.getvalue()
    out.close()
    smtpServer._sendMail(smtpServer,sender, receiver, msg, user=user, password=password)

# any other utilities
def validateEmail(addr):
    "regex that checks for email validity( '@' sign etc..)"
    import re
    email = re.compile("^[a-z0-9\._-]+@+[a-z0-9\._-]+\.+[a-z]{2,3}$",re.I)
    return email.match(addr)

def escapeHTML(s):
    """
    Escape all characters with a special meaning in HTML
    to appropriate character tags
    """
    _ESCAPE_HTML_CHARS=list('&<>":={}()')
    _ESCAPE_HTML_CHARS_TRANS = [(c,'&#%d;' % ord(c)) for c in _ESCAPE_HTML_CHARS]    
    for c,e in _ESCAPE_HTML_CHARS_TRANS:
        s = s.replace(c,e)
    return s
