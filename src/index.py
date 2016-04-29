#!/usr/bin/python3

import http.server
import urllib
import subprocess
import shutil
import sys
import os
import time

PORT = 8080
OUTPUTDIRNAME = 'output'

class GuestFishWrapper():
    def execute(self, storageUrl, outputFileName):
        # Invoke guestfish with the disk
        # list of commands are in cmds.gf and output files are put 
        # into a directory called output
        print(storageUrl)

        timeStr = str(time.time())
        requestDir = 'output/' + timeStr
        varDir = requestDir + '/var'
        os.makedirs(varDir)
        
        args = ['/libguestfs/run', 'guestfish', '-a', storageUrl, '--ro', 'launch', ':', 'mount', '/dev/sda1', '/', ':', 'copy-out', '/var/log', varDir]
        print(args)

        subprocess.call(args)
        shutil.make_archive(outputFileName, 'zip', requestDir)
        return outputFileName + '.zip'

        

class GuestFishHttpHandler(http.server.BaseHTTPRequestHandler):
    # Handles url's of the form:
    #   http://localhost/storage_acct_name/container_name/blobname?saskey
    def do_GET(self):
        try:
            urlObj = urllib.parse.urlparse(self.path)
            urlSplit = urlObj.path.split('/')
            storageAcctName = urlSplit[1]
            container_blob_name = urlSplit[2] + '/' + urlSplit[3]
            storageUrl = urllib.parse.urlunparse(('https', storageAcctName + '.blob.core.windows.net', container_blob_name, '', urlObj.query, None))        
        
            self.send_response_only(100)

            gfWrapper = GuestFishWrapper()
            outputFileName = gfWrapper.execute(storageUrl, OUTPUTDIRNAME)

            #Now go write this file in the response body
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            statinfo = os.stat(outputFileName)
            self.send_header('Content-Length', statinfo.st_size)
            self.end_headers()

            with open(outputFileName, 'rb') as outputFileObj:
                buf = None
                while (True):
                    buf = outputFileObj.read(4096)
                    if (buf == None):
                        break
                    self.wfile.write(buf)
        except (IndexError, FileNotFoundError) as ex:
            self.send_response(404, 'Not Found')
            self.end_headers()
        except:
            self.send_response(500)
            self.end_headers()
        finally:
            self.wfile.flush()        
        

if __name__ == '__main__':
    if (len(sys.argv) > 1):
        gf = GuestFishWrapper()
        outputFileName = gf.execute(sys.argv[1], OUTPUTDIRNAME)
        print("Created " + outputFileName);
    else:
        server_address = ('', PORT)
        server = http.server.HTTPServer(server_address, GuestFishHttpHandler)
        print("Serving at port", PORT)
        server.serve_forever()



