#!/usr/bin/env python

# this proxy is for testing only, do not use in production!

import SocketServer
import SimpleHTTPServer
import urllib2

PORT = 8000

class Proxy(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api'):
            proxy_path = self.path[4:].strip()
            if proxy_path == '':
                proxy_path = '/'

            req = urllib2.Request('http://localhost:8081%s' % proxy_path)
            req.add_header('X-API-Key', 'password')

            try:
                proxy = urllib2.urlopen(req)
                self.send_response(proxy.getcode())
                self.send_header("Content-type", proxy.headers['content-type'])
                self.end_headers()
                self.copyfile(proxy, self.wfile)
            except urllib2.HTTPError, e:
                self.send_response(e.code)
                self.end_headers()

        else:
            SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

httpd = SocketServer.ForkingTCPServer(('0.0.0.0', PORT), Proxy)
print "serving at port", PORT
httpd.serve_forever()
