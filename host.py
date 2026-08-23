import http.server, ssl, time, re, os, mimetypes #, cgi

from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, HTTPServer

# Register AppCache manifest MIME type (required for browser caching)
mimetypes.add_type('text/cache-manifest', '.appcache')

class RequestHandler(SimpleHTTPRequestHandler):
    def replace_locale(self):
        self.path = re.sub(r'^\/document\/(\w{2})\/ps5', '/document/en/ps5', self.path)

    def send_head(self):
        ret = super().send_head()
        # AppCache: never cache the manifest itself so browser always re-checks
        fn = os.path.join(self.directory, self.path.lstrip('/'))
        if fn.endswith('.appcache'):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        return ret

    def do_GET(self):
        self.replace_locale()
        return super().do_GET()

    def do_POST(self):
        self.replace_locale()
        tn = self.path.lstrip('/document/en/ps5/')
        print('!POST!: tn:\n'  + tn)
        fn = tn
        if (not tn.startswith("T_")):
            if (fn!="a.bin"):
                print('!POST!: INFO: '  + str(self.rfile.read(int(self.headers['Content-length']))),"utf-8")
                return
            else:
                fn = time.strftime("%Y%m%d-%H%M%S") + ".bin"

        print('!POST!: ' + self.path + ' -->> ' + fn)
        print('test: %d'%int(self.headers['Content-length']))
        data = self.rfile.read(int(self.headers['Content-length']))
        open("%s"%fn, "wb").write(data)
        
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()


server_address = ('0.0.0.0', 443)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile='localhost.pem')
httpd = http.server.HTTPServer(server_address, RequestHandler)
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
print('running server')
httpd.serve_forever()
