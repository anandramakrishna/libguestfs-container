#!/usr/bin/python3

import http.server
import urllib
import subprocess
import shutil
import sys
import os
import time
import socketserver
import logging

PORT = 8080
OUTPUTDIRNAME = '/output'

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(asctime)s: %(message)s')

class GuestFishWrapper():
    def execute(self, storageUrl, outputDirName):
        # Invoke guestfish with the disk
        # list of commands are in cmds.gf and output files are put 
        # into a directory called output
        logging.info(storageUrl)

        timeStr = str(time.time())
        requestDir = outputDirName + os.sep + timeStr
        varDir = requestDir + '/var'
        os.makedirs(varDir)
        
        args = [
            '/libguestfs/run', 'guestfish', '-a', storageUrl, '--ro', 
            'echo', 'Launching guestfish...', ':',
            'launch', ':', 
            'echo', 'Mounting sda1', ':',
            'mount', '/dev/sda1', '/', ':', 
            'echo', 'Copying waagent logs', ':',
            'glob', 'copy-out', '/var/log/waagent*', varDir, ':',
            'echo', 'Copying syslog', ':',
            'glob', 'copy-out', '/var/log/syslog*', varDir, ':',
            'echo', 'Copying rsyslog', ':',
            'glob', 'copy-out', '/var/log/rsyslog*', varDir, ':',
            'echo', 'Copying kern logs', ':',
            'glob', 'copy-out', '/var/log/kern*', varDir, ':',
            'echo', 'Copying dmesg logs', ':',
            'glob', 'copy-out', '/var/log/dmesg*', varDir, ':',
            'echo', 'Copying dpkg logs', ':',
            'glob', 'copy-out', '/var/log/dpkg*', varDir, ':',
            'echo', 'Copying cloud-init logs', ':',
            'glob', 'copy-out', '/var/log/cloud-init*', varDir, ':',
            'echo', 'Copying boot logs', ':',
            'glob', 'copy-out', '/var/log/boot*', varDir, ':',
            'echo', 'Copying auth logs', ':',
            'glob', 'copy-out', '/var/log/auth*', varDir, ':',
            'echo', 'All copying done!']
        logging.info(args)

        logging.info('Calling guestfish')
        subprocess.call(args)
        logging.info('Guestfish done!')

        logging.info('Making archive')
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
            logging.info('Guest zipped up ' + outputFileName)

            #Now go write this file in the response body
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            statinfo = os.stat(outputFileName)
            self.send_header('Content-Length', statinfo.st_size)
            self.send_header('Content-Disposition', os.path.basename(outputFileName))
            self.end_headers()
            logging.info('HTTP Headers done.')

            with open(outputFileName, 'rb') as outputFileObj:
                buf = None
                logging.info('Opened file for read')
                while (True):
                    logging.info('Reading...')
                    buf = outputFileObj.read(4096)
                    if (not buf):
                        break
                    self.wfile.write(buf)
            logging.info('Finished request processing')
        except (IndexError, FileNotFoundError) as ex:
            logging.exception('Caught IndexError or FileNotFound error')
            self.send_response(404, 'Not Found')
            self.end_headers()
        except:
            logging.exception('Caught exception' + str(ex))
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




