#!/usr/bin/python3

import http.server
import urllib
import subprocess
import shutil
import sys
import os
import time
import socketserver

PORT = 8080
OUTPUTDIRNAME = '/output'

class GuestFishWrapper():
    def execute(self, storageUrl, outputDirName):
        # Invoke guestfish with the disk
        # list of commands are in cmds.gf and output files are put 
        # into a directory called output
        print(storageUrl)

        timeStr = str(time.time())
        requestDir = outputDirName + os.sep + timeStr
        varDir = requestDir + '/var'
        os.makedirs(varDir)
        
        args = ['/libguestfs/run', 'guestfish', '-a', storageUrl, '--ro', 'launch', ':', 'mount', '/dev/sda1', '/', ':', 'copy-out', '/var/log', varDir]
        print(args)

        subprocess.call(args)
        return shutil.make_archive(requestDir, 'zip', requestDir)

class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


        

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
            print('Guest zipped up ' + outputFileName)

            #Now go write this file in the response body
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            statinfo = os.stat(outputFileName)
            self.send_header('Content-Length', statinfo.st_size)
            self.send_header('Content-Disposition', os.path.basename(outputFileName))
            self.end_headers()
            print('HTTP Headers done.')

            with open(outputFileName, 'rb') as outputFileObj:
                buf = None
                print('Opened file for read')
                while (True):
                    print('Reading...')
                    buf = outputFileObj.read(4096)
                    if (not buf):
                        break
                    self.wfile.write(buf)
            print('Finished request processing')
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
        server = ThreadingServer(server_address, GuestFishHttpHandler)
        print("Serving at port", PORT)

        try:
            while (True):
                sys.stdout.flush()
                server.handle_request()
        except KeyboardInterrupt:
            print("Done")




