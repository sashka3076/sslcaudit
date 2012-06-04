# ----------------------------------------------------------------------
# SSLCAUDIT - a tool for automating security audit of SSL clients
# Released under terms of GPLv3, see COPYING.TXT
# Copyright (C) 2012 Alexandre Bezroutchko abb@gremwell.com
# ----------------------------------------------------------------------
from sslcaudit.core.CertFactory import CertFactory

from sslcaudit.modules.base.BaseProfileFactory import BaseProfileFactory, BaseProfile, BaseProfileSpec
from sslcaudit.modules.sslproto.ServerHandler import ServerHandler

SSLPROTO_CN = 'sslproto'
sslproto_server_handler = ServerHandler()

class SSLServerProtoSpec(BaseProfileSpec):
    def __init__(self, proto, cipher):
        self.proto = proto
        self.cipher = cipher

    def __str__(self):
        return "sslproto(%s, %s)" % (self.proto, self.cipher)

class SSLServerProtoProfile(BaseProfile):
    def __init__(self, profile_spec, certnkey):
        self.profile_spec = profile_spec
        self.certnkey = certnkey

    def get_spec(self):
        return self.profile_spec

    def get_handler(self):
        return sslproto_server_handler

    def __str__(self):
        return "%s" % (self.profile_spec)


class ProfileFactory(BaseProfileFactory):
    def __init__(self, file_bag, options):
        BaseProfileFactory.__init__(self, file_bag, options)

        # produce a self-signed server certificate
        cert_factory = CertFactory(self.file_bag)
        certreq_n_keys = cert_factory.mk_certreq_n_keys(SSLPROTO_CN)
        certnkey = cert_factory.sign_cert_req(certreq_n_keys, None)

        for proto in ('sslv23',):
            for cipher in ('HIGH', 'MEDIUM', 'LOW', 'EXPORT'):
                profile = SSLServerProtoProfile(SSLServerProtoSpec(proto, cipher), certnkey)
                self.add_profile(profile)