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
import threading
import csv
from threading import Thread
from datetime import datetime

IP_ADDRESS = '127.0.0.1'
PORT = 8081
OUTPUTDIRNAME = '/output'

totalCount = 0
successCount = 0

logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s: %(asctime)s: %(thread)d : %(message)s')

# Print iterations progress


def printProgress(iteration, total, prefix='',
                  suffix='', decimals=1, barLength=100):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        barLength   - Optional  : character length of bar (Int)
    """
    formatStr = "{0:." + str(decimals) + "f}"
    percents = formatStr.format(100 * (iteration / float(total)))
    filledLength = int(round(barLength * iteration / float(total)))
    bar = 'X' * filledLength + '-' * (barLength - filledLength)
    sys.stdout.write('\r%s |%s| %s%s %s' %
                     (prefix, bar, percents, '%', suffix)),
    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()


class KeepAliveThread(Thread):

    httpRequestHandler = None
    exit_flag = None
    doWork = True
    forThread = None

    def __init__(self, handler, threadId):
        Thread.__init__(self)
        self.httpRequestHandler = handler
        self.doWork = True
        self.exit_flag = threading.Event()
        self.forThread = threadId
        logging.info('Starting KeepAliveWorkerThread for thread ' +
                     str(self.forThread) + '.')

    def run(self):
        while not self.exit_flag.wait(timeout=120):
            if self.doWork:
                logging.info(
                    'Sending CONTINUE response to keep thread ' + str(self.forThread) + ' alive.')
                self.httpRequestHandler.send_response_only(100)
                self.httpRequestHandler.end_headers()
            else:
                logging.info(
                    'Exiting KeepAliveWorkerThread for thread' + str(self.forThread))
                return
        logging.info('Exiting KeepAliveWorkerThread for thread ' +
                     str(self.forThread))

    def complete(self):
        self.doWork = False
        self.exit_flag.set()


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

            proc = subprocess.Popen(
                self.buildGFArgs(commands),
                env=self.environment,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True)
            return proc.communicate()
        except subprocess.CalledProcessError as e:
            logging.warning('Failed ' + echoStr)
            if not continueOnError:
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

    def execute(self, storageUrl, outputDirName, operationId):
        logging.info(storageUrl)

        timeStr = str(time.time())
        requestDir = outputDirName + os.sep + operationId
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
                '-a', storageUrl, '--ro']
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
            fsOutput, error = self.callGF(
                'Listing filesystems', ['list-filesystems'])
            operationOutFile.write(fsOutput)
            operationOutFile.write("\r\n")
            logging.info(fsOutput)

            operationOutFile.write("Inspection Status:\r\n")
            output, error = self.callGF('Inspecting', ['inspect-os'])
            operationOutFile.write(output)
            operationOutFile.write("\r\n")
            # output of list-filesystems is of the form:
            #   /dev/sda1: ext4
            #   /dev/sdb1: ext4
            #   ...

            for line in output.splitlines():
                device = line
                logging.info('Found device at path: %s', device)

                operationOutFile.write("Inspecting ")
                operationOutFile.write(device)

                operationOutFile.write("\r\nType: ")
                inspectOutput, inspectError = self.callGF(
                    'Get-Type', ['--', '-inspect-get-type', device], True)
                operationOutFile.write(inspectOutput)

                operationOutFile.write("Distribution: ")
                inspectOutput, inspectError = self.callGF(
                    'Get-Distro', ['--', '-inspect-get-distro', device], True)
                operationOutFile.write(inspectOutput)

                operationOutFile.write("Product Name: ")
                inspectOutput, inspectError = self.callGF(
                    'Get-ProductName', ['--', '-inspect-get-product-name', device], True)
                operationOutFile.write(inspectOutput)

                operationOutFile.write("Mount Points: \r\n")
                inspectOutput, inspectError = self.callGF(
                    'Get-Mountpoints', ['--', '-inspect-get-mountpoints', device], True)
                operationOutFile.write(inspectOutput)
                operationOutFile.write("\r\n")

                try:
                    self.callGF('Unmounting root volume',
                                ['--', '-umount', '/'], True)
                except subprocess.CalledProcessError:
                    pass

                failed = False
                try:
                    completed, output = self.validateGF('Trying to mounting %s' % (device),
                                                        ['--', '-mount-ro', device, '/'])
                    if not completed:
                        failed = True
                    else:
                        operationOutFile.write("Mounted ")
                        operationOutFile.write(device)
                        operationOutFile.write("\r\n")
                except subprocess.CalledProcessError as e:
                    failed = True

                if failed:
                    operationOutFile.write("Failed to mount ")
                    operationOutFile.write(device)
                    operationOutFile.write("\r\n")
                    # Couldn't mount this device, so just continue to next
                    # device
                    logging.info('Could not mount device %s', device)
                    continue

                operationOutFile.write("Listing /var/log:\r\n")
                # Look for existence of /var/log
                failed = False
                reader = None
                try:
                    completed, output = self.validateGF(
                        'Looking for existence of /var/log',
                        ['--', '-ll', '/var/log'])
                    if not completed:
                        failed = True
                    else:
                        operationOutFile.write(output)
                        operationOutFile.write("\r\n")

                except subprocess.CalledProcessError as e:
                    failed = True

                if failed:
                    logging.info('/var/log does not exist on %s', device)
                    operationOutFile.write("n/a\r\n")
                    continue

                self.callGF('Copying waagent logs',
                            ['--', '-glob', 'copy-out', '/var/log/waagent*', varlogDir], True)
                self.callGF('Copying syslog files',
                            ['--', '-glob', 'copy-out', '/var/log/syslog*', varlogDir], True)
                self.callGF('Copying rsyslog files',
                            ['--', '-glob', 'copy-out', '/var/log/rsyslog*', varlogDir], True)
                self.callGF('Copying messages',
                            ['--', '-glob', 'copy-out', '/var/log/messages*', varlogDir], True)
                self.callGF('Copying kern logs',
                            ['--', '-glob', 'copy-out', '/var/log/kern*', varlogDir], True)
                self.callGF('Copying dmesg logs',
                            ['--', '-glob', 'copy-out', '/var/log/dmesg*', varlogDir], True)
                self.callGF('Copying dpkg logs',
                            ['--', '-glob', 'copy-out', '/var/log/dpkg*', varlogDir], True)
                self.callGF('Copying yum logs',
                            ['--', '-glob', 'copy-out', '/var/log/yum*', varlogDir], True)
                self.callGF('Copying cloud-init logs',
                            ['--', '-glob', 'copy-out', '/var/log/cloud-init*', varlogDir], True)
                self.callGF('Copying boot logs',
                            ['--', '-glob', 'copy-out', '/var/log/boot*', varlogDir], True)
                self.callGF('Copying auth logs',
                            ['--', '-glob', 'copy-out', '/var/log/auth*', varlogDir], True)
                self.callGF('Copying secure logs',
                            ['--', '-glob', 'copy-out', '/var/log/secure*', varlogDir], True)
                self.callGF('Copying fstab',
                            ['--', '-glob', 'copy-out', '/etc/fstab', etcDir], True)
                self.callGF('Copying sshd_conf',
                            ['--', '-glob', 'copy-out', '/etc/ssh/sshd_config', etcDir], True)

            self.callGF('Exiting guestfish', ['--', '-exit'])

            proc = subprocess.Popen(
                ["ls", "-R", requestDir], stdout=subprocess.PIPE)
            output = proc.stdout.read().decode('UTF-8')
            operationOutFile.write("Packaged files:\r\n")
            operationOutFile.write(output)

        logging.info('Making archive')
        archiveName = shutil.make_archive(requestDir, 'zip', requestDir)
        shutil.rmtree(requestDir)
        return archiveName


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


class GuestFishHttpHandler(http.server.BaseHTTPRequestHandler):
    # Handles url's of the form:
    #   http://localhost/storage_acct_name/container_name/blobname?saskey

    def do_GET(self):
        global totalCount
        global successCount
        outputFileName = None
        start_time = datetime.now()
        try:
            urlObj = urllib.parse.urlparse(self.path)
            urlSplit = urlObj.path.split('/')
            if not len(urlSplit) >= 5:
                return

            operationId = urlSplit[1]
            mode = urlSplit[2]
            storageAcctName = urlSplit[3]
            container_blob_name = urlSplit[4] + '/' + urlSplit[5]
            storageUrl = urllib.parse.urlunparse(
                ('https', storageAcctName + '.blob.core.windows.net', container_blob_name, '', urlObj.query, None))

            logging.info('#### Successful Requests Serviced: ' +
                         str(successCount) + '/' + str(totalCount))
            totalCount = totalCount + 1
            logging.info('Request initiated from IP ' + self.client_address[0])
            logging.info('Processing operation id# ' + operationId)
            logging.info('URL: ' + self.path)
            self.send_response_only(100)
            self.end_headers()

            keepAliveWorkerThread = KeepAliveThread(
                self, threading.current_thread().ident)
            keepAliveWorkerThread.start()
            gfWrapper = GuestFishWrapper(self)
            outputFileName = gfWrapper.execute(
                storageUrl, OUTPUTDIRNAME, operationId)
            logging.info('Guest zipped up ' + outputFileName)
            keepAliveWorkerThread.complete()
            keepAliveWorkerThread.join()

            # Now go write this file in the response body
            self.wfile.write(bytes('HTTP/1.1 200 OK\r\n', 'utf-8'))
            self.wfile.write(
                bytes('Content-Type: application/zip\r\n', 'utf-8'))

            statinfo = os.stat(outputFileName)
            self.wfile.write(bytes('Content-Length: {0}\r\n'.format(
                str(statinfo.st_size)), 'utf-8'))
            self.wfile.write(bytes(
                'Content-Disposition: Attachment; filename={0}\r\n'.format(
                    os.path.basename(outputFileName)), 'utf-8'))
            self.wfile.write(bytes('\r\n', 'utf-8'))
            self.wfile.flush()
            logging.info('HTTP Headers done.')

            outputFileSize = os.path.getsize(outputFileName)
            readSize = 0
            with open(outputFileName, 'rb') as outputFileObj:
                buf = None
                logging.info('Opened file for read')
                while (True):
                    buf = outputFileObj.read(64 * 1024)
                    if (not buf):
                        break
                    readSize = readSize + len(buf)
                    printProgress(
                        readSize, outputFileSize, prefix='Progress:', suffix='Complete', barLength=50)
                    self.wfile.write(buf)
            logging.info('Finished request processing')
            successCount = successCount + 1
        except (IndexError, FileNotFoundError) as ex:
            logging.exception('Caught IndexError or FileNotFound error')
            keepAliveWorkerThread.complete()
            keepAliveWorkerThread.join()
            self.send_response(404, 'Not Found')
            self.end_headers()
        except Exception as ex:
            logging.exception('Caught exception' + str(ex))
            keepAliveWorkerThread.complete()
            keepAliveWorkerThread.join()
            self.send_response(500)
            self.end_headers()
        finally:
            self.wfile.flush()
            if outputFileName:
                os.remove(outputFileName)
                elapsed = datetime.now() - start_time
                logging.info('#### Completed request in ' +
                             str(elapsed.total_seconds()) + "s.")


if __name__ == '__main__':
    if (len(sys.argv) > 1):
        gf = GuestFishWrapper()
        outputFileName = gf.execute(sys.argv[1], OUTPUTDIRNAME)
        print("Created " + outputFileName)
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
