#copyright ReportLab Europe Limited 2000-2016
#all rights reserved

def addDbOptions(parser,
                 defaultUser='root',
                 defaultPasswd='',
                 defaultHost='',
                 defaultPort=3306,
                 ):
    parser.add_option(
        "-u", "--user",
        action="store", type="string", dest="user",
        help="database username", metavar="USER",
        default=defaultUser)
    parser.add_option(
        "-p", "--password",
        action="store", type="string", dest="passwd",
        help="database password", metavar="PASSWORD",
        default=defaultPasswd)
    parser.add_option(
        "--host",
        action="store", type="string", dest="host",
        help="database hostname or IP address", metavar="HOST",
        default=defaultHost)
    parser.add_option(
        "-P", "--port",
        action="store", type="int", dest="port",
        help="database port", metavar="PORT",
        default=defaultPort)
