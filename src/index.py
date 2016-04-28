#!/usr/bin/python3

import http.server
import urllib
import subprocess
import shutil
import sys
import os

PORT = 8080

class GuestFishWrapper():
    def execute(self, storageUrl):
        # Invoke guestfish with the disk
        # list of commands are in cmds.gf and output files are put 
        # into a directory called output
        print(storageUrl)
        subprocess.call(['/libguestfs/run', 'guestfish', '-a', storageUrl, '--ro', '-f', os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'cmds.gf')])
        shutil.make_archive('output', 'zip', 'output')
        

class GuestFishHttpHandler(http.server.BaseHTTPRequestHandler):
    # Handles url's of the form:
    #   http://localhost/storage_acct_name/container_name/blobname?saskey
    def do_GET(self):
        urlObj = urllib.parse.urlparse(self.path)
        urlSplit = urlObj.path.split('/')
        storageAcctName = urlSplit[1]
        container_blob_name = urlSplit[2] + '/' + urlSplit[3]
        storageUrl = urllib.parse.urlunparse(('https', storageAcctName + '.blob.core.windows.net', container_blob_name, '', urlObj.query, None))        
        
        gfWrapper = GuestFishWrapper()
        gfWrapper.execute(storageUrl)

        #Now go write this file in the response body
        self.send_response(200)
        self.send_header('Content-Type', 'application/zip')
        statinfo = os.stat('output.zip')
        self.send_header('Content-Length', statinfo.st_size)
        self.end_headers()

        with open('output.zip', 'rb') as outputFileObj:
            buf = None
            while (True):
                buf = outputFileObj.read(4096)
                if (buf == None):
                    break
                self.wfile.write(buf)
        seld.wfile.close()
        
        

if __name__ == '__main__':
    if (len(sys.argv) > 1):
        gf = GuestFishWrapper()
        gf.execute(sys.argv[1])
    else:
        server_address = ('', PORT)
        server = http.server.HTTPServer(server_address, GuestFishHttpHandler)
        print("Serving at port", PORT)
        server.serve_forever()



