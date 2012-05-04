''' ----------------------------------------------------------------------
SSLCAUDIT - a tool for automating security audit of SSL clients
Released under terms of GPLv3, see COPYING.TXT
Copyright (C) 2012 Alexandre Bezroutchko abb@gremwell.com
---------------------------------------------------------------------- '''

import logging, unittest
from src.core.ClientConnectionAuditEvent import ClientConnectionAuditResult
from src.modules.sslcert.ProfileFactory import DEFAULT_CN, SSLProfileSpec_SelfSigned, SSLProfileSpec_IMCA_Signed, SSLProfileSpec_Signed, IM_CA_FALSE_CN, IM_CA_TRUE_CN, IM_CA_NONE_CN
from src.modules.sslcert.SSLServerHandler import    ConnectedReadTimeout, UNEXPECTED_EOF, UNKNOWN_CA
from src.Main import Main
from src.test import TestConfig
from src.test.SSLHammer import NotVerifyingSSLHammer, ChainVerifyingSSLHammer
from src.test.TCPHammer import TCPHammer
from src.test.TestConfig import *

TEST_DEBUG = 0

class ECCAR(object):
    def __init__(self, profile_spec, expected_res):
        self.profile_spec = profile_spec
        self.expected_result = expected_res

    def matches(self, actual_res):
        '''
        Given an actual audit result instance (ClientConnectionAuditResult) checks if it matches our expectations.
        '''
        if not (self.profile_spec == actual_res.profile.get_spec()):
            return False

        if self.expected_result == actual_res.res:
            return True
        else:
            return False

    def __str__(self):
        return "ECCAR(%s, %s)" % (self.profile_spec, self.expected_result)


class TestMainSSL(unittest.TestCase):
    '''
    Unittests for SSL.
    '''
    logger = logging.getLogger('TestMainSSL')

    HAMMER_ATTEMPTS = 10

    def test_plain_tcp_client(self):
    # Plain TCP client causes unexpected UNEXPECTED_EOF instead of UNKNOWN_CA
        self._main_test(
            [
                '--user-cn', TEST_USER_CN,
                '--user-ca-cert', TEST_USER_CA_CERT_FILE,
                '--user-ca-key', TEST_USER_CA_KEY_FILE
            ],
            TCPHammer(),
            [
                ECCAR(SSLProfileSpec_SelfSigned(DEFAULT_CN), UNEXPECTED_EOF),
                ECCAR(SSLProfileSpec_SelfSigned(TEST_USER_CN), UNEXPECTED_EOF),

                ECCAR(SSLProfileSpec_Signed(DEFAULT_CN, TEST_USER_CA_CN), UNEXPECTED_EOF),
                ECCAR(SSLProfileSpec_Signed(TEST_USER_CN, TEST_USER_CA_CN), UNEXPECTED_EOF),

                ECCAR(SSLProfileSpec_IMCA_Signed(DEFAULT_CN, IM_CA_NONE_CN, TEST_USER_CA_CN), UNEXPECTED_EOF),
                ECCAR(SSLProfileSpec_IMCA_Signed(DEFAULT_CN, IM_CA_FALSE_CN, TEST_USER_CA_CN), UNEXPECTED_EOF),
                ECCAR(SSLProfileSpec_IMCA_Signed(DEFAULT_CN, IM_CA_TRUE_CN, TEST_USER_CA_CN), UNEXPECTED_EOF),

                ECCAR(SSLProfileSpec_IMCA_Signed(TEST_USER_CN, IM_CA_NONE_CN, TEST_USER_CA_CN), UNEXPECTED_EOF),
                ECCAR(SSLProfileSpec_IMCA_Signed(TEST_USER_CN, IM_CA_FALSE_CN, TEST_USER_CA_CN), UNEXPECTED_EOF),
                ECCAR(SSLProfileSpec_IMCA_Signed(TEST_USER_CN, IM_CA_TRUE_CN, TEST_USER_CA_CN), UNEXPECTED_EOF)
            ])

    def test_notverifying_client(self):
        self._main_test(
            [
                '--user-cn', TEST_USER_CN,
                '--user-ca-cert', TEST_USER_CA_CERT_FILE,
                '--user-ca-key', TEST_USER_CA_KEY_FILE
            ],
            NotVerifyingSSLHammer(),
            [
                ECCAR(SSLProfileSpec_SelfSigned(DEFAULT_CN), ConnectedReadTimeout(None)),
                ECCAR(SSLProfileSpec_SelfSigned(TEST_USER_CN), ConnectedReadTimeout(None)),

                ECCAR(SSLProfileSpec_Signed(DEFAULT_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None)),
                ECCAR(SSLProfileSpec_Signed(TEST_USER_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None)),

                ECCAR(SSLProfileSpec_IMCA_Signed(DEFAULT_CN, IM_CA_NONE_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None)),
                ECCAR(SSLProfileSpec_IMCA_Signed(DEFAULT_CN, IM_CA_FALSE_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None)),
                ECCAR(SSLProfileSpec_IMCA_Signed(DEFAULT_CN, IM_CA_TRUE_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None)),

                ECCAR(SSLProfileSpec_IMCA_Signed(TEST_USER_CN, IM_CA_NONE_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None)),
                ECCAR(SSLProfileSpec_IMCA_Signed(TEST_USER_CN, IM_CA_FALSE_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None)),
                ECCAR(SSLProfileSpec_IMCA_Signed(TEST_USER_CN, IM_CA_TRUE_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None))
            ])

    def test_client_verifying_cert_chain(self):
        self._main_test(
            [
                '--user-cn', TEST_USER_CN,
                '--user-ca-cert', TEST_USER_CA_CERT_FILE,
                '--user-ca-key', TEST_USER_CA_KEY_FILE
            ],
            ChainVerifyingSSLHammer(TEST_USER_CA_CERT_FILE),
            [
                ECCAR(SSLProfileSpec_SelfSigned(DEFAULT_CN), UNKNOWN_CA),
                ECCAR(SSLProfileSpec_SelfSigned(TEST_USER_CN), UNKNOWN_CA),

                ECCAR(SSLProfileSpec_Signed(DEFAULT_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None)),
                ECCAR(SSLProfileSpec_Signed(TEST_USER_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None)),

                ECCAR(SSLProfileSpec_IMCA_Signed(DEFAULT_CN, IM_CA_NONE_CN, TEST_USER_CA_CN), UNKNOWN_CA),
                ECCAR(SSLProfileSpec_IMCA_Signed(DEFAULT_CN, IM_CA_FALSE_CN, TEST_USER_CA_CN), UNKNOWN_CA),
                ECCAR(SSLProfileSpec_IMCA_Signed(DEFAULT_CN, IM_CA_TRUE_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None)),

                ECCAR(SSLProfileSpec_IMCA_Signed(TEST_USER_CN, IM_CA_NONE_CN, TEST_USER_CA_CN), UNKNOWN_CA),
                ECCAR(SSLProfileSpec_IMCA_Signed(TEST_USER_CN, IM_CA_FALSE_CN, TEST_USER_CA_CN), UNKNOWN_CA),
                ECCAR(SSLProfileSpec_IMCA_Signed(TEST_USER_CN, IM_CA_TRUE_CN, TEST_USER_CA_CN), ConnectedReadTimeout(None))
            ])

    # ------------------------------------------------------------------------------------
    def setUp(self):
        self.main = None

    def tearDown(self):
        if self.main != None: self.main.stop()

    def _main_test(self, args, hammer, expected_results):
        '''
        This is a main worker function. It allocates external resources and launches threads,
        to make sure they are freed this function was to be called exactly once per test method,
        to allow tearDown() method to cleanup properly.
        '''
        self._main_test_init(args, hammer)
        self._main_test_do(expected_results)

    def _main_test_init(self, args, hammer):
        # allocate port
        port = TestConfig.get_next_listener_port()

        # create main, the target of the test
        test_name = "%s %s" % (hammer, args)
        main_args = ['-l', '%s:%d' % (TestConfig.TEST_LISTENER_ADDR, port)]
        main_args.extend(args)
        self.main = Main(main_args)

        # collect classes of observed audit results
        self.actual_results = []
        self.orig_main__handle_result = self.main.handle_result

        def main__handle_result(res):
            self.orig_main__handle_result(res)
            if isinstance(res, ClientConnectionAuditResult):
                self.actual_results.append(res)
            else:
                pass # ignore events print res

        self.main.handle_result = main__handle_result

        # create a client hammering the listener
        self.hammer = hammer
        if self.hammer != None:
            self.hammer.init_tcp((TestConfig.TEST_LISTENER_ADDR, port), self.HAMMER_ATTEMPTS)

    def _main_test_do(self, expected_results):
        # run the server
        self.main.start()

        # start the hammer if any
        if self.hammer != None:    self.hammer.start()

        # wait for main to finish its job
        try:
            self.main.join(timeout=TestConfig.TEST_MAIN_JOIN_TIMEOUT)
            # on timeout throws exception, which we let propagate after we shut the hammer and the main thread

        finally:
            # stop the hammer if any
            if self.hammer != None:    self.hammer.stop()

            # stop the server
            self.main.stop()

        # check if the actual results match expected ones
        if len(expected_results) != len(self.actual_results):
            mismatch = True
            print "! length mismatch len(er)=%d, len(ar)=%d" % (len(expected_results), len(self.actual_results))
            for er in expected_results: print "er=%s" % er
            for ar in self.actual_results: print "ar=%s" % ar
        else:
            mismatch = False
            for i in range(len(expected_results)):
                er = expected_results[i]
                ar = self.actual_results[i]
                if not er.matches(ar):
                    print "! mismatch\n\ter=%s\n\tar=%s" % (er, ar)
                    mismatch = True
        self.assertFalse(mismatch)

if __name__ == '__main__':
    logging.basicConfig()
    unittest.main()

