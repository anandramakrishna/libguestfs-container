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
import io

IP_ADDRESS='127.0.0.1'
PORT = 8081
OUTPUTDIRNAME = '/output'

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(asctime)s: %(thread)d : %(message)s')

class GuestFishWrapper:
    environment = None
    httpRequestHandler = None

    def __init__(self, handler):
      self.httpRequestHandler = handler

    def buildGFArgs(self, args):
        retArgs = ['/libguestfs/run', 'guestfish', '--remote']
        retArgs.extend(args)
        logging.info(retArgs)
        return retArgs

    def callGF(self, echoStr, commands, continueOnError=False):
        try:
            logging.info(echoStr)
            self.httpRequestHandler.send_response_only(100)
            self.httpRequestHandler.end_headers()

            proc = subprocess.Popen(
                self.buildGFArgs(commands),
                env = self.environment,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True)
            return proc.communicate()
        except subprocess.CalledProcessError as e:
            logging.warning('Failed ' + echoStr)
            if continueOnError == False:
                raise(e)
            logging.info('Continuing...')
        
    def validateGF(self, echoStr, commands, continueOnError=False):
        output, error = self.callGF(echoStr, commands, continueOnError)
        logging.info('Output = %s', output)
        logging.info('Error = %s', error)

        if (error.find('libguestfs: error') == -1 or
                output.find('libguestfs:error') == -1):
            return True, output
        return False, output

    def execute(self, storageUrl, outputDirName):
        logging.info(storageUrl)

        timeStr = str(time.time())
        requestDir = outputDirName + os.sep + timeStr
        varlogDir = requestDir + os.sep + 'var' + os.sep + 'log'
        etcDir = requestDir + os.sep + 'etc'
        operationOutFilename = requestDir + os.sep + 'results.txt'
        os.makedirs(varlogDir)
        os.makedirs(etcDir)

        with open(operationOutFilename, "w", newline="\r\n") as operationOutFile:       

            # Run guestfish in remote mode and then send it a command
            # at a time since the programming environment inside guestfish
            # is very limited (no variables, etc.)

            args = [
                '/libguestfs/run', 'guestfish', '--listen', 
                '-a', storageUrl, '--ro' ]
            logging.info(args)

            # Guestfish server mode returns a string of the form
            #   GUESTFISH_PID=pid; export GUESTFISH_PID
            # We need to parse this and extract out the GUESTFISH_PID 
            # environment variable and inserting it into the subsequent env
            logging.info('Calling guestfish')
            self.environment = os.environ.copy()
            output = subprocess.check_output(
                args, env=self.environment, universal_newlines=True)
            logging.info(output)

            try:
                guestfishpid = int(output.split(';')[0].split('=')[1])
            except Exception as e:
                raise Exception('Cannot find GUESTFISH_PID')
            
            self.environment['GUESTFISH_PID'] = str(guestfishpid)
            logging.info('GUESTFISH_PID = %d', guestfishpid)

            # Enumerate file systems
            # Then try mounting them and looking for logs
            # Exit out once any logs are found

            self.callGF('Launching', ['launch'])
            operationOutFile.write("Filesystem Status:\r\n")
            output, error = self.callGF('Listing filesystems', ['list-filesystems'])
            operationOutFile.write(output)
            operationOutFile.write("\r\n")

            # output of list-filesystems is of the form:
            #   /dev/sda1: ext4
            #   /dev/sdb1: ext4 
            #   ...

            for line in output.splitlines():
                idx = line.find(':')
                if idx == -1:
                    continue
                device = line[:idx]
                logging.info('Found device at path: %s', device)

                try:
                    self.callGF('Unmounting root volume', 
                        ['--', '-umount', '/'], True)
                except subprocess.CalledProcessError:
                    pass

                failed = False
                try:
                    completed, output = self.validateGF('Trying to mounting %s' %(device), 
                            ['--', '-mount', device, '/']) 
                    if completed != True:
                        failed = True
                    else:
                        operationOutFile.write("Mounted ")
                        operationOutFile.write(device)
                        operationOutFile.write("\r\n")
                except subprocess.CalledProcessError as e:
                    failed = True

                if failed == True:
                    operationOutFile.write("Failed to mount ")
                    operationOutFile.write(device)
                    operationOutFile.write("\r\n")
                    # Couldn't mount this device, so just continue to next device
                    logging.info('Could not mount device %s', device)
                    continue

                operationOutFile.write("Listing /var/log:\r\n")
                # Look for existence of /var/log
                failed = False
                try:
                    completed, output = self.validateGF(
                            'Looking for existence of /var/log', 
                            ['--', '-ll', '/var/log'])
                    if completed != True:
                        failed = True
                    else:
                        operationOutFile.write(output)
                        operationOutFile.write("\r\n")
                except subprocess.CalledProcessError as e:
                    failed = True

                if failed == True:
                    logging.info('/var/log does not exist on %s', device)
                    operationOutFile.write("n/a\r\n")
                    continue

                self.callGF('Copying waagent logs', 
                    ['--','-glob','copy-out', '/var/log/waagent*', varlogDir], True)
                self.callGF('Copying syslog files',
                    ['--','-glob', 'copy-out', '/var/log/syslog*', varlogDir], True)
                self.callGF('Copying rsyslog files',
                    ['--','-glob', 'copy-out','/var/log/rsyslog*', varlogDir], True)
                self.callGF('Copying messages',
                    ['--','-glob','copy-out','/var/log/messages*', varlogDir], True)
                self.callGF('Copying kern logs',
                    ['--', '-glob', 'copy-out', '/var/log/kern*', varlogDir], True)
                self.callGF('Copying dmesg logs',
                    ['--', '-glob', 'copy-out', '/var/log/dmesg*', varlogDir], True)
                self.callGF('Copying dpkg logs',
                    ['--', '-glob', 'copy-out', '/var/log/dpkg*', varlogDir], True)
                self.callGF('Copying yum logs',
                    ['--', '-glob', 'copy-out', '/var/log/yum*', varlogDir], True)
                self.callGF('Copying cloud-init logs',
                    ['--','-glob','copy-out','/var/log/cloud-init*',varlogDir], True)
                self.callGF('Copying boot logs',
                    ['--','-glob', 'copy-out', '/var/log/boot*', varlogDir], True)
                self.callGF('Copying auth logs',
                    ['--', '-glob', 'copy-out', '/var/log/auth*', varlogDir], True)
                self.callGF('Copying secure logs',
                    ['--','-glob', 'copy-out', '/var/log/secure*', varlogDir], True)
                self.callGF('Copying fstab',
                    ['--','-glob', 'copy-out', '/etc/fstab', etcDir], True)
                self.callGF('Copying sshd_conf',
                    ['--','-glob', 'copy-out', '/etc/ssh/sshd_config', etcDir],True)
                
            self.callGF('Exiting guestfish', ['--', '-exit'])

            proc = subprocess.Popen(["ls","-R",requestDir], stdout=subprocess.PIPE)
            output = proc.stdout.read().decode('UTF-8')
            operationOutFile.write("Packaged files:\r\n")
            operationOutFile.write(output)

        logging.info('Making archive')
        archiveName = shutil.make_archive(requestDir, 'zip', requestDir)
        shutil.rmtree(requestDir);
        return archiveName;

class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass
        

class GuestFishHttpHandler(http.server.BaseHTTPRequestHandler):
    # Handles url's of the form:
    #   http://localhost/storage_acct_name/container_name/blobname?saskey
    def do_GET(self):
        try:
            urlObj = urllib.parse.urlparse(self.path)
            urlSplit = urlObj.path.split('/')
            if not len(urlSplit) >= 5:
                return

            operationId = urlSplit[1]
            mode = urlSplit[2]
            storageAcctName = urlSplit[3]
            container_blob_name = urlSplit[4] + '/' + urlSplit[5]
            storageUrl = urllib.parse.urlunparse(('https', storageAcctName + '.blob.core.windows.net', container_blob_name, '', urlObj.query, None))        
        
            logging.info('Processing operation id# ' + operationId)
            logging.info('URL: ' + self.path)
            self.send_response_only(100)
            self.end_headers()
 
            gfWrapper = GuestFishWrapper(self)
            outputFileName = gfWrapper.execute(storageUrl, OUTPUTDIRNAME)
            logging.info('Guest zipped up ' + outputFileName)

            #Now go write this file in the response body
            self.wfile.write(bytes('HTTP/1.1 200 OK\r\n', 'utf-8'))
            self.wfile.write(bytes('Content-Type: application/zip\r\n','utf-8'))

            statinfo = os.stat(outputFileName)
            self.wfile.write(bytes('Content-Length: {0}\r\n'.format(
                str(statinfo.st_size)), 'utf-8'))
            self.wfile.write(bytes(
                'Content-Disposition: Attachment; filename={0}\r\n'.format(
                os.path.basename(outputFileName)), 'utf-8'))
            self.wfile.write(bytes('\r\n', 'utf-8'))
            self.wfile.flush()
            logging.info('HTTP Headers done.')

            with open(outputFileName, 'rb') as outputFileObj:
                buf = None
                logging.info('Opened file for read')
                while (True):
                    logging.info('Reading...')
                    buf = outputFileObj.read(64 * 1024)
                    if (not buf):
                        break
                    self.wfile.write(buf)
            logging.info('Finished request processing')
        except (IndexError, FileNotFoundError) as ex:
            logging.exception('Caught IndexError or FileNotFound error')
            self.send_response(404, 'Not Found')
            self.end_headers()
        except Exception as ex:
            logging.exception('Caught exception' + str(ex))
            self.send_response(500)
            self.end_headers()
        finally:
            self.wfile.flush()
            os.remove(outputFileName)            

        

if __name__ == '__main__':
    if (len(sys.argv) > 1):
        gf = GuestFishWrapper()
        outputFileName = gf.execute(sys.argv[1], OUTPUTDIRNAME)
        print("Created " + outputFileName);
    else:
        server_address = (IP_ADDRESS, PORT)
        GuestFishHttpHandler.protocol_version = "HTTP/1.1"
        server = ThreadingServer(server_address, GuestFishHttpHandler)
        print("Serving at port", PORT)

        try:
            while (True):
                sys.stdout.flush()
                server.handle_request()
        except KeyboardInterrupt:
            print("Done")




