''' ----------------------------------------------------------------------
SSLCAUDIT - a tool for automating security audit of SSL clients
Released under terms of GPLv3, see COPYING.TXT
Copyright (C) 2012 Alexandre Bezroutchko abb@gremwell.com
---------------------------------------------------------------------- '''

from Queue import Empty
import logging, sys
from optparse import OptionParser
from threading import Thread
from src.ClientAuditor.ClientAuditorServer import ClientAuditorServer
from src.ClientAuditor.ClientConnectionAuditEvent import ClientConnectionAuditResult
from src.ClientAuditor.ClientHandler import ClientAuditResult
from src.ClientAuditor.Dummy.DummyClientAuditorSet import DummyClientAuditorSet
from src.ClientAuditor.SSL.SSLClientAuditorSet import SSLClientAuditorSet, DEFAULT_CN

logger = logging.getLogger('Main')

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = '8443'
DEFAULT_TEST_NAME = 'untitled'

PROG_NAME = 'sslcaudit'
PROG_VERSION = '1.0rc1'

OUTPUT_FIELD_SEPARATOR = ' '

class Main(Thread):

    def __init__(self, argv):
        Thread.__init__(self, target=self.run)

        parser = OptionParser(usage=('%s [OPTIONS]' % PROG_NAME), version=("%s %s" % (PROG_NAME, PROG_VERSION)))
        parser.add_option("-l", dest="listen_on", default='0.0.0.0:8443', help="Listening [HOST:]PORT")
        parser.add_option("-m", dest="module", help="Audit module (by default - all)")
        parser.add_option("-d", dest="debug_level", default=0, help="Debug level")
        parser.add_option("-c", dest="nclients", default=1, help="Number of clients to handle before quitting")
        parser.add_option("-N", dest="test_name", help="User-specified name of the test")

        parser.add_option("--user-cn", dest="user_cn",
            help="Use specified CN")
        parser.add_option("--server", dest="server",
            help="HOST:PORT to fetch the certificate from")
        parser.add_option("--user-cert", dest="user_cert_file",
            help="A file with user-supplied certificate")
        parser.add_option("--user-key", dest="user_key_file",
            help="A file with user-supplied key")
        parser.add_option("--user-ca-cert", dest="user_ca_cert_file",
            help="A file with a cert for CA, useful for testing sslcaudit itself")
        parser.add_option("--user-ca-key", dest="user_ca_key_file",
            help="A file with a key for CA, useful for testing sslcaudit itself")

        parser.add_option("--no-default-cn", action="store_true", default=False, dest="no_default_cn",
            help=("Do not use default CN (%s)" % (DEFAULT_CN)))
        parser.add_option("--no-self-signed", action="store_true", default=False, dest="no_self_signed",
            help="Don't try self-signed certificates")
        parser.add_option("--no-user-cert-signed", action="store_true", default=False, dest="no_user_cert_signed",
            help="Do not sign server certificates with user-supplied one")

        args = []
        (options, args) = parser.parse_args(argv)

        self.options = options

        if self.options.debug_level > 0:
            logging.getLogger().setLevel(logging.DEBUG)

        self.auditor_sets = []
        if self.options.module == None or self.options.module == SSLClientAuditorSet.MODULE_ID:
            self.auditor_sets.append(SSLClientAuditorSet(self.options))

        #if self.options.module == None or self.options.module == DummyClientAuditorSet.MODULE_ID:
        #    self.auditor_sets.append(DummyClientAuditorSet(self.options))

        if len(self.auditor_sets) == 0:
            raise RuntimeError("auditor set is empty")

        listen_on_parts = self.options.listen_on.split(':')
        if len(listen_on_parts) == 1:
            # convert "PORT" string to (DEFAULT_HOST, POST) tuple
            listen_on = (DEFAULT_HOST, int(listen_on_parts[0]))
        elif len(listen_on_parts) == 2:
            # convert "HOST:PORT" string to (HOST, PORT) tuple
            listen_on = (listen_on_parts[0], int(listen_on_parts[1]))
        else:
            # XXX
            raise Exception("invalid value for -l parameter '%s'" % self.options.listen_on.split(':'))

        if self.options.test_name == None:
            self.options.test_name = DEFAULT_TEST_NAME

        # unparsed command line goes into test name
        if len(args) > 0:
            raise Exception("unexpected arguments: %s" % args)

        self.server = ClientAuditorServer(listen_on, self.auditor_sets)
        self.queue_read_timeout = 0.1

    def start(self):
        self.do_stop = False
        self.server.start()
        Thread.start(self)

    def stop(self):
        # signal the thread to stop
        self.do_stop = True

    def handle_result(self, res):
        if isinstance(res, ClientConnectionAuditResult):
            # print test name, client address and port, auditor name, and result
            # all in one line, in fixed width columns
            fields = []
            if self.options.test_name != None:
                fields.append('%-25s' % str(self.options.test_name))
            client_address = '%s:%d' % (res.conn.client_address)
            fields.append('%-22s' % client_address)
            fields.append('%-70s' % str(res.auditor.name))
            fields.append(str(res.res))
            print OUTPUT_FIELD_SEPARATOR.join(fields)

    def run(self):
        '''
        Main loop function. Will run until the desired number of clients is handled.
        '''

        nresults = 0
        # loop until get all desired results, quit if stopped
        while nresults < self.options.nclients and not self.do_stop:
            try:
                # wait for a message blocking for short intervals, check stop flag frequently
                res = self.server.res_queue.get(True, self.queue_read_timeout)
                logger.debug("got result %s", res)
                self.handle_result(res)

                if isinstance(res, ClientAuditResult):
                    nresults = nresults + 1
            except Empty:
                pass


