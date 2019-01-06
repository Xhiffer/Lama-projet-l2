"""Simple XML-RPC Server.

This module can be used to create simple XML-RPC servers
by creating a server and either installing functions, a
class instance, or by extending the SimpleXMLRPCServer
class.

The methods system.listMethods, system.methodHelp and
system.methodSignature are automatically made available
to remote clients. Installed instances can extend
the behavior of these methods by implementing the
following methods:

def _listMethods(self):
    '''_listMethods() => ['method1', method2']

    This method will be called in response to
    system.listMethods to generate HTML help
    for the server. You can use it to return
    the list of methods that are available as
    part of this instance.

    If this method and the _dispatch method are
    not implemented by this instance, then the
    system.listMethods routine will automatically
    enumerate all callable attributes on the
    instance that do not begin with "_"'''

def _methodHelp(self, method_name):
    '''_methodHelp('method1') => 'method1 is method which...'

    This method will be called in response to
    system.methodHelp to generate HTML help
    for the server. You can use it to return
    a document string for a particular method.

    If this method and the _dispatch method are
    not implemented by this instance, then the
    system.methodHelp routine will provide
    the document string as help for any instance
    attributes that do not begin with "_"'''

def _get_method_argstring(self, method_name):
    '''_get_method_argstring('add') => '(int x, int y)'

    This method will be called to generate HTML help
    for the server. You can use it to return
    a string descripting argument list for a particular
    method.

    If this method and the _dispatch method are
    not implemented by this instance, then the
    argument strings will be automatically
    generated for any callable instance attributes
    that do not begin with "_"'''
    
It can also be used to handle XML-RPC requests in a CGI
environment using CGIXMLRPCRequestHandler.

A list of possible usage patterns follows:

1. Install functions:

server = SimpleXMLRPCServer(("localhost", 8000))
server.register_function(pow)
server.register_function(lambda x,y: x+y, 'add')
server.serve_forever()

2. Install an instance:

class MyFuncs:
    def __init__(self):
        # make all of the string functions available through
        # string.func_name
        import string
        self.string = string
    def _listMethods(self):
        # implement this method so that the introspection methods
        # know to advertise the strings methods
        return list_public_methods(self) + \
                ['string.' + method for method in list_public_methods(self.string)]
    def pow(self, x, y): return pow(x, y)
    def add(self, x, y) : return x + y
server = SimpleXMLRPCServer(("localhost", 8000))
server.register_instance(MyFuncs())
server.serve_forever()

3. Install an instance with custom dispatch method:

class Math:
    def _listMethods(self):
        return ['add', 'pow']
    def _methodHelp(self, method):
        if method == 'add':
            return "add(2,3) => 5"
        elif method == 'pow':
            return "pow(x, y[, z]) => number"
        else:
            # By convention, return empty
            # string if no help is available
            return ""
    def _dispatch(self, method, params):
        if method == 'pow':
            return pow(*params)
        elif method == 'add':
            return params[0] + params[1]
        else:
            raise 'bad method'
server = SimpleXMLRPCServer(("localhost", 8000))
server.register_instance(Math())
server.serve_forever()

4. Subclass SimpleXMLRPCServer:

class MathServer(SimpleXMLRPCServer):
    def _dispatch(self, method, params):
        try:
            # We are forcing the 'export_' prefix on methods that are
            # callable through XML-RPC to prevent potential security
            # problems
            func = getattr(self, 'export_' + method)
        except AttributeError:
            raise Exception('method "%s" is not supported' % method)
        else:
            return func(*params)

    def export_add(self, x, y):
        return x + y

server = MathServer(("localhost", 8000))
server.serve_forever()

5. CGI script:

server = CGIXMLRPCRequestHandler()
server.register_function(pow)
server.handle_request()
"""

# Written by Brian Quinlan (brian@sweetapp.com).
# Based on code written by Fredrik Lundh.

try:
    import xmlrpc.client as xmlrpc_client
    import http.server as http_server
    import socketserver
except ImportError:
    import xmlrpclib as xmlrpc_client
    import BaseHTTPServer as http_server
    import SocketServer as socketserver
Fault = xmlrpc_client.Fault
import sys, traceback
import pydoc
import inspect
import os
import re
import collections

def _resolve_dotted_attribute(obj, attr):
    """Resolves a dotted attribute name to an object.  Raises
    an AttributeError if any attribute in the chain starts with a '_'.
    """
    for i in attr.split('.'):
        if i.startswith('_'):
            raise AttributeError(
                'attempt to access private attribute "%s"' % i
                )
        else:
            obj = getattr(obj,i)
    return obj

def list_public_methods(obj):
    """Returns a list of attribute strings, found in the specified
    object, which represent callable attributes"""

    return [member for member in dir(obj)
                if not member.startswith('_') and
                    isinstance(getattr(obj, member), collections.Callable)]

def remove_duplicates(lst):
    """remove_duplicates([2,2,2,1,3,3]) => [3,1,2]

    Returns a copy of a list without duplicates. Every list
    item must be hashable and the order of the items in the
    resulting list is not defined."""
    
    u = {}
    for x in lst:
        u[x] = 1

    return list(u.keys())

class SimpleXMLRPCServerDoc(pydoc.HTMLDoc):
    """Class used to generate document for a SimpleXMLRPCServer"""
    
    def markup(self, text, escape=None, funcs={}, classes={}, methods={}):
        """Mark up some plain text, given a context of symbols to look for.
        Each context dictionary maps object names to anchor names."""
        escape = escape or self.escape
        results = []
        here = 0

        # Note that this regular expressions does not allow for the hyperlinking
        # of arbitrary strings being used as method names. Only methods with
        # names consisting of word characters and .s are hyperlinked.
        pattern = re.compile(r'\b((http|ftp)://\S+[\w/]|'
                                r'RFC[- ]?(\d+)|'
                                r'PEP[- ]?(\d+)|'
                                r'(self\.)?((?:\w|\.)+))\b')
        while 1:
            match = pattern.search(text, here)
            if not match: break
            start, end = match.span()
            results.append(escape(text[here:start]))

            all, scheme, rfc, pep, selfdot, name = match.groups()
            if scheme:
                results.append('<a href="%s">%s</a>' % (all, escape(all)))
            elif rfc:
                url = 'http://www.rfc-editor.org/rfc/rfc%d.txt' % int(rfc)
                results.append('<a href="%s">%s</a>' % (url, escape(all)))
            elif pep:
                url = 'http://www.python.org/peps/pep-%04d.html' % int(pep)
                results.append('<a href="%s">%s</a>' % (url, escape(all)))
            elif text[end:end+1] == '(':
                results.append(self.namelink(name, methods, funcs, classes))
            elif selfdot:
                results.append('self.<strong>%s</strong>' % name)
            else:
                results.append(self.namelink(name, classes))
            here = end
        results.append(escape(text[here:]))
        return ''.join(results)
    
    def docroutine(self, object, name=None, mod=None,
                   funcs={}, classes={}, methods={}, cl=None):
        """Produce HTML documentation for a function or method object."""

        anchor = (cl and cl.__name__ or '') + '-' + name
        note = ''

        title = '<a name="%s"><strong>%s</strong></a>' % (anchor, name)
            
        if inspect.ismethod(object):
            args, varargs, varkw, defaults = inspect.getargspec(object.__func__)
            # exclude the argument bound to the instance, it will be
            # confusing to the non-Python user
            argspec = inspect.formatargspec(
                args[1:], varargs, varkw, defaults, formatvalue=self.formatvalue)  
        elif inspect.isfunction(object):
            args, varargs, varkw, defaults = inspect.getargspec(object)
            argspec = inspect.formatargspec(
                args, varargs, varkw, defaults, formatvalue=self.formatvalue)
        else:
            argspec = '(...)'

        if isinstance(object, tuple):
            argspec = object[0] or argspec
            docstring = object[1] or ""
        else:
            docstring = pydoc.getdoc(object)
                
        decl = title + argspec + (note and self.grey(
               '<font face="helvetica, arial">%s</font>' % note))

        doc = self.markup(
            docstring, self.preformat, funcs, classes, methods)
        doc = doc and '<dd><tt>%s</tt></dd>' % doc
        return '<dl><dt>%s</dt>%s</dl>\n' % (decl, doc)

    def docserver(self, server_name, package_documentation, methods):
        """Produce HTML documentation for an XML-RPC server."""

        fdict = {}
        for key, value in list(methods.items()):
            fdict[key] = '#-' + key
            fdict[value] = fdict[key]
            
        head = '<big><big><strong>%s</strong></big></big>' % server_name            
        result = self.heading(head, '#ffffff', '#7799ee')
       
        doc = self.markup(package_documentation, self.preformat, fdict)
        doc = doc and '<tt>%s</tt>' % doc
        result = result + '<p>%s</p>\n' % doc

        contents = []
        method_items = list(methods.items())
        method_items.sort()
        for key, value in method_items:
            contents.append(self.docroutine(value, key, funcs=fdict))
        result = result + self.bigsection(
            'Methods', '#ffffff', '#eeaa77', pydoc.join(contents))

        return result

class SimpleXMLRPCDispatcher:
    """Mix-in class that dispatches XML-RPC requests.

    This class is used to register XML-RPC method handlers
    and then to dispatch them. There should never be any
    reason to instantiate this class directly.
    """
    
    def __init__(self):
        self.funcs = {}
        self.instance = None

        # setup variables used for HTML documentation
        self.server_name = 'XML-RPC Server Documentation'
        self.server_documentation = \
        """This server exports the following methods through the XML-RPC
protocol."""
        self.server_title = 'XML-RPC Server Documentation'
        self.debug = 1

    def set_server_title(self, server_title):
        """Set the HTML title of the generated server documentation"""

        self.server_title = server_title

    def set_server_name(self, server_name):
        """Set the name of the generated HTML server documentation"""

        self.server_name = server_name

    def set_server_documentation(self, server_documentation):
        """Set the documentation string for the entire server.

        Use to generate HTML documentation."""

        self.server_documentation = server_documentation
        
    def register_instance(self, instance):
        """Registers an instance to respond to XML-RPC requests.

        Only one instance can be installed at a time.

        If the registered instance has a _dispatch method then that
        method will be called with the name of the XML-RPC method and
        it's parameters as a tuple
        e.g. instance._dispatch('add',(2,3))

        If the registered instance does not have a _dispatch method
        then the instance will be searched to find a matching method
        and, if found, will be called. Methods beginning with an '_'
        are considered private and will not be called by
        SimpleXMLRPCServer.

        If a registered function matches a XML-RPC request, then it
        will be called instead of the registered instance.
        """

        self.instance = instance

    def register_introspection_functions(self):
        """Registers the XML-RPC introspection methods in the system
        namespace.

        see http://xmlrpc.usefulinc.com/doc/reserved.html"""
        
        self.funcs.update({'system.listMethods' : self.system_listMethods,
                      'system.methodSignature' : self.system_methodSignature,
                      'system.methodHelp' : self.system_methodHelp})

    def register_multicall_functions(self):
        """Registers the XML-RPC multicall method in the system
        namespace.

        see http://www.xmlrpc.com/discuss/msgReader$1208"""
        
        self.funcs.update({'system.multicall' : self.system_multicall})
        
    def register_function(self, function, name = None):
        """Registers a function to respond to XML-RPC requests.

        The optional name argument can be used to set a Unicode name
        for the function.
        """

        if name is None:
            name = function.__name__
        self.funcs[name] = function

    def generate_html_documentation(self):
        """generate_html_documentation() => html documentation for the server

        Generates HTML documentation for the server using introspection for
        installed functions and instances that do not implement the
        _dispatch method. Alternatively, instances can choose to implement
        the _get_method_argstring(method_name) method to provide the
        argument string used in the documentation and the
        _methodHelp(method_name) method to provide the help text used
        in the documentation."""
        
        methods = {}

        for method_name in self.system_listMethods():
            if method_name in self.funcs:
                method = self.funcs[method_name]
            elif self.instance is not None:
                method_info = [None, None] # argspec, documentation
                if hasattr(self.instance, '_get_method_argstring'):
                    method_info[0] = self.instance._get_method_argstring(method_name)
                if hasattr(self.instance, '_methodHelp'):
                    method_info[1] = self.instance._methodHelp(method_name)

                method_info = tuple(method_info)
                if method_info != (None, None):
                    method = method_info
                elif not hasattr(self.instance, '_dispatch'):
                    try:
                        method = _resolve_dotted_attribute(
                                    self.instance,
                                    method_name
                                    )
                    except AttributeError:
                        method = method_info
                else:
                    method = method_info
            else:
                assert 0, "Could not find method in self.functions and no instance installed"

            methods[method_name] = method

        documenter = SimpleXMLRPCServerDoc()
        documentation = documenter.docserver(
                                self.server_name,
                                self.server_documentation,
                                methods
                                )
                                        
        return documenter.page(self.server_title, documentation)
            
    def _marshaled_dispatch(self, data, dispatch_method = None):
        """Dispatches an XML-RPC method from marshalled (XML) data.
        
        XML-RPC methods are dispatched from the marshalled (XML) data
        using the _dispatch method and the result is returned as
        marshalled data. For backwards compatibility, a dispatch
        function can be provided as an argument (see comment in 
        SimpleXMLRPCRequestHandler.do_POST) but overriding the
        existing method through subclassing is the prefered means
        of changing method dispatch behavior.
        """
        
        params, method = xmlrpc_client.loads(data)

        # generate response
        try:
            if dispatch_method is not None:
                response = dispatch_method(method, params)
            else:                
                response = self._dispatch(method, params)
            # wrap response in a singleton tuple
            response = (response,)
            response = xmlrpc_client.dumps(response, methodresponse=1)
        except Fault as fault:
            response = xmlrpc_client.dumps(fault)
        except:
            # report exception back to server
            ftb = self.debug and '\n'+str(traceback.format_tb(sys.exc_info()[2])) or ''
            response = xmlrpc_client.dumps(
                xmlrpc_client.Fault(1, "%s:%s%s" % (sys.exc_info()[0], sys.exc_info()[1],ftb))
                )

        return response

    def system_listMethods(self):
        """system.listMethods() => ['add', 'subtract', 'multiple']

        Returns a list of the methods supported by the server."""
        
        methods = list(self.funcs.keys())
        if self.instance is not None:
            if hasattr(self.instance, '_listMethods'):
                methods = remove_duplicates(methods + self.instance._listMethods())
            # if the instance has a _dispatch method then we
            # don't have enough information to provide a list
            # of methods
            elif not hasattr(self.instance, '_dispatch'):
                methods = remove_duplicates(methods + list_public_methods(self.instance))
        methods.sort()
        return methods
    
    def system_methodSignature(self, method_name):
        """system.methodSignature('add') => [double, int, int]"

        Returns a list describing the signiture of the method. In the
        above example, the add method takes two integers as arguments
        and returns a double result.

        This server does NOT support system.methodSignature."""
        
        # http://xmlrpc.usefulinc.com/doc/sysmethodsig.html
        return 'signatures not supported'

    def system_methodHelp(self, method_name):
        """system.methodHelp('add') => "Adds two integers together"

        Returns a string containing documentation for the specified method."""
        
        method = None
        if method_name in self.funcs:
            method = self.funcs[method_name]
        elif self.instance is not None:
            if hasattr(self.instance, '_methodHelp'):
                return self.instance._methodHelp(method_name)
            # if the instance has a _dispatch method then we
            # don't have enough information to provide help
            elif not hasattr(self.instance, '_dispatch'):
                try:
                    method = _resolve_dotted_attribute(
                                self.instance,
                                method_name
                                )
                except AttributeError:
                    pass

        # Note that we aren't checking that the method actually
        # be a callable object of some kind
        if method is None:
            return ""
        else:
            return pydoc.getdoc(method)

    def system_multicall(self, call_list):
        """system.multicall([{'methodName': 'add', 'params': [2, 2]}, ...]) => [[4], ...]

        Allows the caller to package multiple XML-RPC calls into a single
        request.

        See http://www.xmlrpc.com/discuss/msgReader$1208        
        """
        
        results = []
        for call in call_list:
            method_name = call['methodName']
            params = call['params']

            try:
                # XXX The problem is we have to check that the marshal won't
                # work to insert an appropriate error here instead of failing
                # the entire multicall
                results.append([self._dispatch(method_name, params)])
            except Fault as fault:
                results.append(
                    {'faultCode' : fault.faultCode,
                     'faultString' : fault.faultString}
                    )
            except:
                results.append(
                    {'faultCode' : 1,
                     'faultString' : "%s:%s\n%s" % (sys.exc_info()[0], sys.exc_info()[1], traceback.format_tb(sys.exc_info()[2]))}
                    )
        return results
    
    def _dispatch(self, method, params):
        """Dispatches the XML-RPC method.

        XML-RPC calls are forwarded to a registered function that
        matches the called XML-RPC method name. If no such function
        exists then the call is forwarded to the registered instance,
        if available.

        If the registered instance has a _dispatch method then that
        method will be called with the name of the XML-RPC method and
        it's parameters as a tuple
        e.g. instance._dispatch('add',(2,3))

        If the registered instance does not have a _dispatch method
        then the instance will be searched to find a matching method
        and, if found, will be called.

        Methods beginning with an '_' are considered private and will
        not be called.
        """

        func = None
        try:
            # check to see if a matching function has been registered
            func = self.funcs[method]
        except KeyError:
            if self.instance is not None:
                # check for a _dispatch method
                if hasattr(self.instance, '_dispatch'):
                    return self.instance._dispatch(method, params)
                else:
                    # call instance method directly
                    try:
                        func = _resolve_dotted_attribute(
                            self.instance,
                            method
                            )
                    except AttributeError:
                        pass

        if func is not None:
            return func(*params)
        else:
            raise Exception('method "%s" is not supported' % method)
        
        
class SimpleXMLRPCRequestHandler(http_server.BaseHTTPRequestHandler):
    """Simple XML-RPC request handler class.

    Handles all HTTP POST requests and attempts to decode them as
    XML-RPC requests.

    XML-RPC requests are dispatched to the server's _dispatch method,
    which may be overriden by subclasses.
    """

    def do_POST(self):
        """Handles the HTTP POST request.

        Attempts to interpret all HTTP POST requests as XML-RPC calls,
        which are forwarded to the server's _dispatch method for handling.
        """
        
        try:
            # get arguments
            data = self.rfile.read(int(self.headers["content-length"]))
            # In previous versions of SimpleXMLRPCServer, _dispatch
            # could be overridden in this class, instead of in
            # SimpleXMLRPCDispatcher. To maintain backwards compatibility,
            # check to see if a subclass implements _dispatch and dispatch
            # using that method if present.
            response = self.server._marshaled_dispatch(data, getattr(self, '_dispatch', None))
        except: # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            self.send_response(500)
            self.end_headers()
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

            # shut down the connection
            self.wfile.flush()
            self.connection.shutdown(1)
            
    def log_request(self, code='-', size='-'):
        """Selectively log an accepted request."""

        if self.server.logRequests:
            http_server.BaseHTTPRequestHandler.log_request(self, code, size)

class SimpleXMLRPCAndDocsRequestHandler(SimpleXMLRPCRequestHandler):
    def do_GET(self):
        """Handles the HTTP GET request.

        Interpret all HTTP GET requests as requests for server
        documentation.
        """
        
        response = self.server.generate_html_documentation()
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

        # shut down the connection
        self.wfile.flush()
        self.connection.shutdown(1)
        
class SimpleXMLRPCServer(socketserver.TCPServer, 
                         SimpleXMLRPCDispatcher):
    """Simple XML-RPC server.

    Simple XML-RPC server that allows functions and a single instance
    to be installed to handle requests. The default implementation
    attempts to dispatch XML-RPC calls to the functions or instance
    installed in the server. Override the _dispatch method inhereted
    from SimpleXMLRPCDispatcher to change this behavior.
    """

    def __init__(self, addr, requestHandler=SimpleXMLRPCRequestHandler,
                 logRequests=1):
        self.logRequests = logRequests
        
        SimpleXMLRPCDispatcher.__init__(self)
        socketserver.TCPServer.__init__(self, addr, requestHandler)
        

class CGIXMLRPCRequestHandler(SimpleXMLRPCDispatcher):
    """Simple handler for XML-RPC data passed through CGI."""
    
    def __init__(self):
        SimpleXMLRPCDispatcher.__init__(self)

    def handle_xmlrpc(self, request_text):
        """Handle a single XML-RPC request"""
        
        response = self._marshaled_dispatch(request_text)
    
        print('Content-Type: text/xml')
        print('Content-Length: %d' % len(response))
        print()
        print(response)

    def handle_get(self):
        """Handle a single HTTP GET request.

        Default implementation indicates an error because
        XML-RPC uses the POST method.
        """

        code = 400
        message, explain = http_server.BaseHTTPRequestHandler.responses[code]
        
        response = http_server.DEFAULT_ERROR_MESSAGE % \
            {
             'code' : code, 
             'message' : message, 
             'explain' : explain
            }
        print('Status: %d %s' % (code, message))
        print('Content-Type: text/html')
        print('Content-Length: %d' % len(response))
        print()
        print(response)
                    
    def handle_request(self, request_text = None):
        """Handle a single XML-RPC request passed through a CGI post method.
        
        If no XML data is given then it is read from stdin. The resulting
        XML-RPC response is printed to stdout along with the correct HTTP
        headers.
        """
        
        if request_text is None and \
            os.environ.get('REQUEST_METHOD', None) == 'GET':
            self.handle_get()
        else:
            # POST data is normally available through stdin
            if request_text is None:
                request_text = sys.stdin.read()        

            self.handle_xmlrpc(request_text)
            
class CGIXMLRPCAndDocsRequestHandler(CGIXMLRPCRequestHandler):
    def handle_get(self):
        """Handles the HTTP GET request.

        Interpret all HTTP GET requests as requests for server
        documentation.
        """

        response = self.generate_html_documentation()

        print('Content-Type: text/html')
        print('Content-Length: %d' % len(response))
        print()
        print(response)
        
if __name__ == '__main__':
    server = SimpleXMLRPCServer(("localhost", 8000))
    server.register_function(pow)
    server.register_function(lambda x,y: x+y, 'add')
    server.serve_forever()
